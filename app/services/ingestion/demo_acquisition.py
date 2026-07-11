"""Steam demo-reference acquisition boundary."""

from __future__ import annotations

import json
import socket
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BASE_DIR, get_settings
from app.db.models import ImportJob, Match
from app.services.ingestion.demo_downloader import (
    _download_demo_file,
    _fetch_demo_urls,
    steam_demo_downloader_configured,
)
from app.services.ingestion.jobs import (
    IMPORT_JOB_COMPLETED,
    IMPORT_JOB_FAILED,
    IMPORT_JOB_IN_PROGRESS,
    IMPORT_JOB_SKIPPED_DUPLICATE,
    complete_import_job,
    fail_import_job,
    start_import_job,
)

DEMO_REFERENCE_FOUND = "demo_reference_found"
DEMO_DOWNLOAD_QUEUED_OR_READY = "demo_download_queued_or_ready"
DEMO_ALREADY_AVAILABLE = "already_available"
DEMO_AUTH_MISSING = "auth_missing"
DEMO_STEAM_UNAVAILABLE = "steam_unavailable"
DEMO_NOT_FOUND = "not_found"
DEMO_RATE_LIMITED_OR_TIMEOUT = "rate_limited_or_timeout"
DEMO_FAILED_WITH_ACTIONABLE_ERROR = "failed_with_actionable_error"

DEMO_ACQUISITION_SUCCESS_OUTCOMES = frozenset(
    {
        DEMO_REFERENCE_FOUND,
        DEMO_DOWNLOAD_QUEUED_OR_READY,
        DEMO_ALREADY_AVAILABLE,
    }
)

DemoUrlFetcher = Callable[[list[str]], dict[str, Any]]
DemoDownloader = Callable[[str, str], Any]


def validate_steam_demo_acquisition_config() -> dict[str, Any]:
    settings = get_settings()
    helper = BASE_DIR / "tools" / "steam-gc" / "fetch-demo-urls.js"
    has_refresh_token = bool(settings.steam_bot_refresh_token)
    has_username_password = bool(settings.steam_bot_username and settings.steam_bot_password)
    configured = steam_demo_downloader_configured()
    missing: list[str] = []
    if not configured:
        missing.append("STEAM_BOT_REFRESH_TOKEN or STEAM_BOT_USERNAME+STEAM_BOT_PASSWORD")
    if not helper.exists():
        missing.append("tools/steam-gc/fetch-demo-urls.js")
    return {
        "configured": configured and helper.exists(),
        "auth_configured": configured,
        "helper_installed": helper.exists(),
        "credential_mode": (
            "refresh_token"
            if has_refresh_token
            else "username_password"
            if has_username_password
            else "missing"
        ),
        "missing": missing,
        "timeout_seconds": max(5, int(settings.steam_bot_timeout_seconds)),
    }


def acquire_steam_demo_reference(
    db: Session,
    *,
    share_code: str,
    fetcher: DemoUrlFetcher | None = None,
    download: bool = False,
    downloader: DemoDownloader | None = None,
) -> dict[str, Any]:
    normalized_share_code = share_code.strip()
    started_at = _now_iso()
    match = _steam_history_match(db, normalized_share_code)
    if match is not None and match.demo_file:
        return _result(
            DEMO_ALREADY_AVAILABLE,
            share_code=normalized_share_code,
            started_at=started_at,
            match=match,
            action="Use the existing stored demo; no Steam acquisition is needed.",
        )

    config = validate_steam_demo_acquisition_config()
    if not config["auth_configured"]:
        return _result(
            DEMO_AUTH_MISSING,
            share_code=normalized_share_code,
            started_at=started_at,
            match=match,
            config=config,
            action="Configure Steam bot credentials before acquiring demo URLs.",
        )
    if not config["helper_installed"]:
        return _result(
            DEMO_FAILED_WITH_ACTIONABLE_ERROR,
            share_code=normalized_share_code,
            started_at=started_at,
            match=match,
            config=config,
            error_message="Steam GC helper is not installed.",
            action="Restore tools/steam-gc/fetch-demo-urls.js before acquiring demo URLs.",
        )
    if match is None:
        return _result(
            DEMO_NOT_FOUND,
            share_code=normalized_share_code,
            started_at=started_at,
            config=config,
            action="Create or sync the Steam history row for this share code before acquiring its demo.",
        )

    fetch_demo_urls = fetcher or _fetch_demo_urls
    try:
        payload = fetch_demo_urls([normalized_share_code])
    except Exception as exc:
        return _exception_result(
            exc,
            share_code=normalized_share_code,
            started_at=started_at,
            match=match,
            config=config,
        )

    item = _result_item_for_share_code(payload, normalized_share_code)
    if not item:
        return _result(
            DEMO_NOT_FOUND,
            share_code=normalized_share_code,
            started_at=started_at,
            match=match,
            config=config,
            helper_payload_status=_helper_payload_status(payload),
            action="Retry after the share code is confirmed in Steam history; the helper returned no matching row.",
        )
    if not item.get("ok"):
        return _result(
            _classify_error_message(str(item.get("error") or item.get("code") or "Steam helper returned failure.")),
            share_code=normalized_share_code,
            started_at=started_at,
            match=match,
            config=config,
            helper_payload_status=_helper_payload_status(payload),
            error_message=str(item.get("error") or item.get("code") or "Steam helper returned failure."),
            action=_action_for_error(str(item.get("error") or item.get("code") or "")),
        )

    demo_url = str(item.get("demo_url") or "").strip()
    if not demo_url:
        return _result(
            DEMO_REFERENCE_FOUND,
            share_code=normalized_share_code,
            started_at=started_at,
            match=match,
            config=config,
            helper_payload_status=_helper_payload_status(payload),
            action="Steam returned metadata but no demo URL; retry later or inspect Steam helper output.",
        )
    parsed = urlparse(demo_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return _result(
            DEMO_FAILED_WITH_ACTIONABLE_ERROR,
            share_code=normalized_share_code,
            started_at=started_at,
            match=match,
            config=config,
            error_message="Steam helper returned an invalid demo URL.",
            action="Inspect Steam helper output; the demo URL must be an HTTP(S) URL.",
        )

    source_path = None
    if download:
        try:
            download_demo_file = downloader or _download_demo_file
            source_path = str(download_demo_file(demo_url, normalized_share_code))
        except Exception as exc:
            return _exception_result(
                exc,
                share_code=normalized_share_code,
                started_at=started_at,
                match=match,
                config=config,
            )

    result = _result(
        DEMO_DOWNLOAD_QUEUED_OR_READY,
        share_code=normalized_share_code,
        started_at=started_at,
        match=match,
        config=config,
        helper_payload_status=_helper_payload_status(payload),
        demo_reference={
            "kind": "download_url",
            "host": parsed.netloc,
            "has_url": True,
            "match_id": item.get("match_id"),
            "match_time_available": item.get("match_time") is not None,
            "downloaded": bool(source_path),
        },
        source_path=source_path,
        action="Demo download source is available for the existing downloader/import path.",
    )
    _mark_match_acquisition_result(db, match, result)
    return result


def run_steam_demo_acquisition_job(
    db: Session,
    job_id: int,
    *,
    fetcher: DemoUrlFetcher | None = None,
) -> dict[str, Any]:
    job = db.get(ImportJob, job_id)
    if job is None:
        raise ValueError("Import job was not found.")
    if job.provider != "steam" or job.job_type != "demo_acquisition":
        raise ValueError("Only steam demo_acquisition jobs can be processed here.")
    if job.status == IMPORT_JOB_IN_PROGRESS:
        return _job_result(job)
    if job.status in {IMPORT_JOB_COMPLETED, IMPORT_JOB_FAILED, IMPORT_JOB_SKIPPED_DUPLICATE, "succeeded"}:
        return _job_result(job)

    payload = _json_loads(job.requested_payload_json)
    share_code = str(payload.get("share_code") or payload.get("match_share_code") or "").strip()
    if not share_code:
        result = _result(
            DEMO_FAILED_WITH_ACTIONABLE_ERROR,
            share_code="",
            started_at=_now_iso(),
            error_message="share_code is required for demo acquisition.",
            action="Create the demo acquisition job with payload.share_code.",
        )
        fail_import_job(db, job, str(result["error"]["message"]), result=result)
        return _job_result(job)

    start_import_job(db, job)
    result = acquire_steam_demo_reference(db, share_code=share_code, fetcher=fetcher)
    if result["overall_outcome"] in DEMO_ACQUISITION_SUCCESS_OUTCOMES:
        complete_import_job(db, job, result=result)
    else:
        message = str((result.get("error") or {}).get("message") or result["overall_outcome"])
        fail_import_job(db, job, message, result=result)
    return _job_result(job)


def _exception_result(
    exc: Exception,
    *,
    share_code: str,
    started_at: str,
    match: Match | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    message = str(exc) or type(exc).__name__
    outcome = _classify_exception(exc, message)
    return _result(
        outcome,
        share_code=share_code,
        started_at=started_at,
        match=match,
        config=config,
        error_message=message,
        error_type=type(exc).__name__,
        action=_action_for_error(message),
    )


def _classify_exception(exc: Exception, message: str) -> str:
    if isinstance(exc, (TimeoutError, socket.timeout, subprocess.TimeoutExpired)):
        return DEMO_RATE_LIMITED_OR_TIMEOUT
    if isinstance(exc, HTTPError):
        if exc.code == 429:
            return DEMO_RATE_LIMITED_OR_TIMEOUT
        if exc.code in {404, 410}:
            return DEMO_NOT_FOUND
        if exc.code in {500, 502, 503, 504}:
            return DEMO_STEAM_UNAVAILABLE
    if isinstance(exc, URLError) and _looks_timeout_or_rate_limit(message):
        return DEMO_RATE_LIMITED_OR_TIMEOUT
    return _classify_error_message(message)


def _classify_error_message(message: str) -> str:
    normalized = message.lower()
    if _looks_timeout_or_rate_limit(normalized):
        return DEMO_RATE_LIMITED_OR_TIMEOUT
    if "not found" in normalized or "expired" in normalized or "http 404" in normalized or "http 410" in normalized:
        return DEMO_NOT_FOUND
    if "steam unavailable" in normalized or "temporarily unavailable" in normalized or "http 502" in normalized:
        return DEMO_STEAM_UNAVAILABLE
    return DEMO_FAILED_WITH_ACTIONABLE_ERROR


def _looks_timeout_or_rate_limit(message: str) -> bool:
    normalized = message.lower()
    return "timeout" in normalized or "timed out" in normalized or "rate limit" in normalized or "429" in normalized


def _action_for_error(message: str) -> str:
    outcome = _classify_error_message(message)
    if outcome == DEMO_RATE_LIMITED_OR_TIMEOUT:
        return "Retry later with the one-demo cap preserved; Steam or the helper timed out or rate-limited the request."
    if outcome == DEMO_STEAM_UNAVAILABLE:
        return "Retry later; Steam or Valve replay services were unavailable."
    if outcome == DEMO_NOT_FOUND:
        return "Confirm the share code is valid and that the replay has not expired."
    return "Inspect the Steam helper error and configuration; no secret value is required in logs."


def _result(
    outcome: str,
    *,
    share_code: str,
    started_at: str,
    match: Match | None = None,
    config: dict[str, Any] | None = None,
    helper_payload_status: dict[str, Any] | None = None,
    demo_reference: dict[str, Any] | None = None,
    source_path: str | None = None,
    error_message: str | None = None,
    error_type: str | None = None,
    action: str,
) -> dict[str, Any]:
    result = {
        "overall_outcome": outcome,
        "acquisition_outcome": outcome,
        "share_code": share_code or None,
        "match_id": match.id if match is not None else None,
        "clean_success": outcome in DEMO_ACQUISITION_SUCCESS_OUTCOMES,
        "started_at": started_at,
        "finished_at": _now_iso(),
        "next_action": action,
        "config": _public_config_status(config) if config is not None else None,
        "helper_payload_status": helper_payload_status,
        "demo_reference": demo_reference,
        "source_path": source_path,
        "error": None,
    }
    if error_message:
        result["error"] = {"message": error_message, "type": error_type}
    return result


def _public_config_status(config: dict[str, Any] | None) -> dict[str, Any] | None:
    if config is None:
        return None
    return {
        "configured": config.get("configured"),
        "auth_configured": config.get("auth_configured"),
        "helper_installed": config.get("helper_installed"),
        "credential_mode": config.get("credential_mode"),
        "missing": config.get("missing") or [],
        "timeout_seconds": config.get("timeout_seconds"),
    }


def _helper_payload_status(payload: dict[str, Any]) -> dict[str, Any]:
    results = payload.get("results") if isinstance(payload, dict) else None
    return {
        "ok": bool(payload.get("ok")) if isinstance(payload, dict) else False,
        "results_count": len(results) if isinstance(results, list) else 0,
    }


def _result_item_for_share_code(payload: dict[str, Any], share_code: str) -> dict[str, Any] | None:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return None
    for item in results:
        if isinstance(item, dict) and item.get("share_code") == share_code:
            return item
    return None


def _mark_match_acquisition_result(db: Session, match: Match, result: dict[str, Any]) -> None:
    raw = _json_loads(match.raw_json)
    raw.update(
        {
            "status": "demo_reference_found",
            "demo_acquisition": {
                "outcome": result["acquisition_outcome"],
                "finished_at": result["finished_at"],
                "demo_reference": result.get("demo_reference"),
            },
            "next_step": "download_demo_with_steam_service_bot",
        }
    )
    match.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
    db.commit()


def _steam_history_match(db: Session, share_code: str) -> Match | None:
    if not share_code:
        return None
    return db.scalar(
        select(Match)
        .where(Match.source == "steam_history")
        .where(Match.external_match_id == share_code)
        .order_by(Match.id.desc())
    )


def _job_result(job: ImportJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "status": job.status,
        "job_type": job.job_type,
        "result": _json_loads(job.result_json),
        "error": job.error_message,
    }


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _now_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()
