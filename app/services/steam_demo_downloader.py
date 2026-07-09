from __future__ import annotations

import bz2
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BASE_DIR, get_settings
from app.db.models import Match, SteamAccount
from app.services.demo_parser import DemoParseError, import_demo_file
from app.services.demo_retention import (
    DEMO_RETENTION_STATUS_CLEANUP_NEEDED,
    retention_metadata,
)
from app.services.recommendation_tracking import (
    evaluate_recommendations_for_match,
    recommendation_evaluation_metadata,
)
from app.services.steam_integration import decode_match_share_code
from app.services.steam_match_metadata import (
    STEAM_GC_PLAYED_AT_SOURCE,
    parse_steam_match_time,
    steam_gc_metadata_from_item,
)
from app.services.steam_storage_guard import (
    STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
    STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED,
    SteamImportStorageBudget,
    SteamStorageBudgetExceeded,
)

DOWNLOAD_CHUNK_BYTES = 1024 * 1024


class SteamDemoDownloadError(RuntimeError):
    pass


def steam_demo_downloader_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.steam_bot_refresh_token
        or (settings.steam_bot_username and settings.steam_bot_password)
    )


def download_pending_steam_demos(
    db: Session,
    limit: int = 10,
    player_identifier: str | None = None,
    share_codes: list[str] | None = None,
    min_played_at: datetime | None = None,
    storage_budget: SteamImportStorageBudget | None = None,
    progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    import_job_id: int | None = None,
) -> dict[str, Any]:
    storage_budget = storage_budget or SteamImportStorageBudget()
    total_pending = _count_pending_steam_history_matches(db, share_codes=share_codes)
    target_limit = max(1, min(limit, storage_budget.settings.max_demos_per_run))
    matches = _pending_steam_history_matches(db, limit=target_limit, share_codes=share_codes)
    remaining_pending = max(0, total_pending - len(matches))
    batch_cap_reached = remaining_pending > 0
    if not matches:
        return {
            "configured": steam_demo_downloader_configured(),
            "processed": 0,
            "imported": 0,
            "failed": 0,
            "pending": total_pending,
            "remaining_pending": total_pending,
            "storage_budget": storage_budget.snapshot(),
            "results": [],
        }
    if not steam_demo_downloader_configured():
        return {
            "configured": False,
            "processed": 0,
            "imported": 0,
            "failed": 0,
            "pending": total_pending,
            "remaining_pending": total_pending,
            "batch_cap_reached": batch_cap_reached,
            "storage_budget": storage_budget.snapshot(),
            "results": [],
            "message": "Steam service bot is not configured.",
        }

    try:
        storage_budget.preflight()
    except SteamStorageBudgetExceeded as exc:
        return {
            "configured": True,
            "processed": 0,
            "imported": 0,
            "failed": 1,
            "pending": total_pending,
            "remaining_pending": total_pending,
            "storage_budget": exc.budget,
            "results": [{"status": "failed", "error": str(exc), "budget_status": exc.status}],
            "budget_status": STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED,
        }

    share_codes = [_share_code_for_match(match) for match in matches]
    metadata = _fetch_demo_urls(share_codes)
    by_share_code = {item.get("share_code"): item for item in metadata.get("results", []) if item.get("share_code")}

    results = []
    imported = failed = skipped = processed = 0
    budget_status = None
    for match in matches:
        share_code = _share_code_for_match(match)
        _emit_progress(
            progress_callback,
            "demo_queued",
            share_code=share_code,
            match_id=match.id,
            counters={
                "processed": processed,
                "imported": imported,
                "failed": failed,
                "skipped": skipped,
                "pending": total_pending - processed,
            },
        )
        item = by_share_code.get(share_code) or {"ok": False, "error": "Steam bot did not return this share code."}
        try:
            storage_budget.reserve_next_demo()
            if not item.get("ok"):
                message = item.get("error") or item.get("code") or "Could not resolve demo URL."
                raise SteamDemoDownloadError(str(message))
            steam_metadata = steam_gc_metadata_from_item(item)
            played_at = parse_steam_match_time(steam_metadata.get("played_at"))
            if min_played_at and (not played_at or played_at <= min_played_at):
                skipped += 1
                _mark_match_download_skipped(
                    db,
                    match,
                    steam_metadata=steam_metadata,
                    reason="steam_gc_match_time_not_newer_than_latest_imported_match",
                )
                results.append(
                    {
                        "match_id": match.id,
                        "share_code": share_code,
                        "status": "skipped",
                        "played_at": steam_metadata.get("played_at"),
                        "played_at_source": steam_metadata.get("played_at_source"),
                        "match_date_status": _match_date_status(steam_metadata),
                        "reason": "not_newer_than_latest_imported_match",
                    }
                )
                processed += 1
                continue
            result = _download_and_import_match(
                db,
                match,
                share_code=share_code,
                steam_gc_item=item,
                player_identifier=player_identifier,
                storage_budget=storage_budget,
                progress_callback=progress_callback,
                import_job_id=import_job_id,
            )
            imported += 1 if result.get("imported") else 0
            results.append(result)
            processed += 1
        except SteamStorageBudgetExceeded as exc:
            _emit_progress(
                progress_callback,
                exc.status,
                share_code=share_code,
                match_id=match.id,
                budget_status=exc.status,
                error=str(exc),
            )
            fail_current = exc.status != STEAM_IMPORT_DISK_BUDGET_EXCEEDED or not results
            if fail_current:
                failed += 1
                retention = retention_metadata(
                    raw_demo_path=None,
                    parser_success=False,
                    status=DEMO_RETENTION_STATUS_CLEANUP_NEEDED,
                )
                _mark_match_download_error(db, match, str(exc), retention=retention)
                results.append(
                    {
                        "match_id": match.id,
                        "share_code": share_code,
                        "status": "failed",
                        "error": str(exc),
                        "budget_status": exc.status,
                        **retention,
                    }
                )
                processed += 1
                remaining_pending += len(matches) - processed
            else:
                remaining_pending += len(matches) - processed
                results.append(
                    {
                        "match_id": match.id,
                        "share_code": share_code,
                        "status": "not_attempted",
                        "budget_status": exc.status,
                        "error": str(exc),
                    }
                )
            budget_status = exc.status
            break
        except Exception as exc:
            failed += 1
            retention = getattr(exc, "retention", {}) or {}
            if not retention:
                retention = retention_metadata(
                    raw_demo_path=None,
                    parser_success=False,
                    status=DEMO_RETENTION_STATUS_CLEANUP_NEEDED,
                )
            _mark_match_download_error(db, match, str(exc), retention=retention)
            results.append(
                {"match_id": match.id, "share_code": share_code, "status": "failed", "error": str(exc), **retention}
            )
            processed += 1

    final_batch_cap_reached = batch_cap_reached or remaining_pending > 0
    if final_batch_cap_reached:
        _emit_progress(
            progress_callback,
            "batch_cap_reached",
            remaining_pending=remaining_pending,
            batch_cap_reached=True,
            counters={
                "processed": processed,
                "imported": imported,
                "failed": failed,
                "skipped": skipped,
                "pending": remaining_pending,
            },
        )
    return {
        "configured": True,
        "processed": processed,
        "imported": imported,
        "failed": failed,
        "skipped": skipped,
        "pending": remaining_pending,
        "remaining_pending": remaining_pending,
        "batch_cap_reached": final_batch_cap_reached,
        "budget_status": budget_status,
        "storage_budget": storage_budget.snapshot(),
        "results": results,
    }


def _pending_steam_history_matches(db: Session, limit: int, share_codes: list[str] | None = None) -> list[Match]:
    target_limit = max(1, min(limit, 50))
    stmt = (
        select(Match)
        .where(Match.source == "steam_history")
        .where(Match.demo_file.is_(None))
        .order_by(Match.id.desc())
        .limit(max(target_limit * 5, 25))
    )
    if share_codes is not None:
        normalized_codes = [code.strip() for code in share_codes if code and code.strip()]
        if not normalized_codes:
            return []
        stmt = stmt.where(Match.external_match_id.in_(normalized_codes))
    rows = db.scalars(stmt).all()
    matches = [
        match
        for match in rows
        if _share_code_for_match(match) and _match_raw(match).get("status") != "demo_download_error"
    ]
    return matches[:target_limit]


def _count_pending_steam_history_matches(db: Session, share_codes: list[str] | None = None) -> int:
    return len(_pending_steam_history_matches(db, limit=50, share_codes=share_codes))


def _download_and_import_match(
    db: Session,
    match: Match,
    share_code: str,
    steam_gc_item: dict[str, Any],
    player_identifier: str | None,
    storage_budget: SteamImportStorageBudget | None = None,
    progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    import_job_id: int | None = None,
) -> dict[str, Any]:
    decoded = decode_match_share_code(share_code)
    demo_url = str(steam_gc_item["demo_url"])
    steam_metadata = steam_gc_metadata_from_item(steam_gc_item)
    date_status = _match_date_status(steam_metadata)
    download_kwargs: dict[str, Any] = {"storage_budget": storage_budget}
    if progress_callback is not None:
        download_kwargs["progress_callback"] = progress_callback
    demo_path = _download_demo_file(demo_url, share_code, **download_kwargs)
    try:
        _emit_progress(progress_callback, "parser_started", share_code=share_code, match_id=match.id)
        import_result = import_demo_file(
            db,
            demo_path,
            original_filename=f"{share_code}.dem",
            player_identifier=player_identifier,
            steam_metadata=steam_metadata,
            acquisition_metadata=_acquisition_metadata(db, match, share_code, import_job_id),
            storage_budget=storage_budget,
            evaluate_recommendations=False,
        )
        _emit_progress(
            progress_callback,
            "demo_stored",
            share_code=share_code,
            match_id=match.id,
            stored_path=import_result.get("stored_path"),
            raw_demo_path=import_result.get("raw_demo_path"),
            raw_demo_size_bytes=import_result.get("raw_demo_size_bytes"),
            storage=import_result.get("storage"),
            parser_handoff=import_result.get("parser_handoff"),
        )
        _emit_progress(
            progress_callback,
            "parser_succeeded",
            share_code=share_code,
            match_id=match.id,
            status="imported",
        )
    except DemoParseError as exc:
        _emit_progress(
            progress_callback,
            "parser_failed",
            share_code=share_code,
            match_id=match.id,
            error=str(exc),
        )
        error = SteamDemoDownloadError(f"Downloaded demo but parser failed: {exc}")
        error.retention = exc.retention
        raise error from exc
    finally:
        shutil.rmtree(demo_path.parent, ignore_errors=True)

    db.refresh(match)
    imported_match = db.get(Match, import_result.get("match_id")) if import_result.get("match_id") else None
    recommendation_metadata = import_result.get("recommendation_evaluation")
    recommendation_evaluations = import_result.get("recommendation_evaluations", [])
    if imported_match is not None:
        _apply_primary_steam_date_truth(imported_match, steam_metadata, date_status)
        db.commit()
        db.refresh(imported_match)
        if date_status == "exact_match_date_available":
            evaluations = evaluate_recommendations_for_match(db, imported_match.id)
            if evaluations:
                recommendation_metadata = recommendation_evaluation_metadata(
                    evaluations,
                    status="created",
                    match_id=imported_match.id,
                )
            else:
                status = "duplicate" if import_result.get("skipped_duplicates") else "skipped"
                recommendation_metadata = recommendation_evaluation_metadata(
                    status=status,
                    match_id=imported_match.id,
                    reason="already_evaluated_or_no_eligible_recommendation",
                )
            recommendation_evaluations = recommendation_metadata["evaluations"]
        else:
            recommendation_metadata = recommendation_evaluation_metadata(
                status="not_eligible",
                match_id=imported_match.id,
                reason=date_status,
            )
            recommendation_evaluations = []
    elif recommendation_metadata is None:
        recommendation_metadata = recommendation_evaluation_metadata(
            status="skipped",
            reason="import_result_missing_demo_match",
        )
        recommendation_evaluations = []
    raw = _match_raw(match)
    raw.update(
        {
            "status": "demo_imported",
            "download_method": "steam_service_bot",
            "decoded": decoded,
            "steam_metadata": steam_metadata,
            "played_at": steam_metadata.get("played_at"),
            "played_at_source": steam_metadata.get("played_at_source"),
            "match_date_status": date_status,
            "match_date_source": steam_metadata.get("played_at_source") or "unavailable",
            "match_date_truth_note": _match_date_truth_note(date_status),
            "demo_retention_policy": import_result.get("demo_retention_policy"),
            "demo_retention_status": import_result.get("demo_retention_status"),
            "raw_demo_path": import_result.get("raw_demo_path"),
            "raw_demo_size_bytes": import_result.get("raw_demo_size_bytes"),
            "parser_success": import_result.get("parser_success"),
            "storage": import_result.get("storage"),
            "parser_handoff": import_result.get("parser_handoff"),
            "recommendation_evaluations": recommendation_evaluations,
            "recommendation_evaluation": recommendation_metadata,
            "demo_url_host": urlparse(demo_url).netloc,
            "imported_demo_match_id": import_result.get("match_id"),
            "imported_at": datetime.now(UTC).isoformat(),
            "next_step": None,
        }
    )
    match.demo_file = import_result.get("stored_path")
    match.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
    db.commit()
    return {
        "match_id": match.id,
        "share_code": share_code,
        "status": "imported",
        "demo_match_id": import_result.get("match_id"),
        "played_at": steam_metadata.get("played_at"),
        "played_at_source": steam_metadata.get("played_at_source"),
        "match_date_status": date_status,
        "match_date_source": steam_metadata.get("played_at_source") or "unavailable",
        "demo_retention_policy": import_result.get("demo_retention_policy"),
        "demo_retention_status": import_result.get("demo_retention_status"),
        "raw_demo_path": import_result.get("raw_demo_path"),
        "raw_demo_size_bytes": import_result.get("raw_demo_size_bytes"),
        "parser_success": import_result.get("parser_success"),
        "storage": import_result.get("storage"),
        "parser_handoff": import_result.get("parser_handoff"),
        "imported": import_result.get("imported", 0),
        "duplicate": import_result.get("skipped_duplicates", 0),
        "recommendation_evaluations": recommendation_evaluations,
        "recommendation_evaluation": recommendation_metadata,
    }


def _fetch_demo_urls(share_codes: list[str]) -> dict[str, Any]:
    helper = BASE_DIR / "tools" / "steam-gc" / "fetch-demo-urls.js"
    if not helper.exists():
        raise SteamDemoDownloadError("Steam service bot helper is not installed.")

    settings = get_settings()
    credential_dir = BASE_DIR / "data" / "steam_bot_credentials"
    credential_dir.mkdir(parents=True, exist_ok=True)
    credential_dir.chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "STEAM_BOT_CREDENTIAL_DIR": str(credential_dir),
            "STEAM_BOT_TIMEOUT_MS": str(max(5, settings.steam_bot_timeout_seconds) * 1000),
        }
    )
    optional_env = {
        "STEAM_BOT_USERNAME": settings.steam_bot_username,
        "STEAM_BOT_PASSWORD": settings.steam_bot_password,
        "STEAM_BOT_SHARED_SECRET": settings.steam_bot_shared_secret,
        "STEAM_BOT_TWO_FACTOR_CODE": settings.steam_bot_two_factor_code,
        "STEAM_BOT_REFRESH_TOKEN": settings.steam_bot_refresh_token,
    }
    for key, value in optional_env.items():
        if value:
            env[key] = value

    result = subprocess.run(
        ["node", str(helper)],
        cwd=str(helper.parent),
        env=env,
        input=json.dumps({"share_codes": share_codes}, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=max(10, settings.steam_bot_timeout_seconds + 10),
        check=False,
    )
    output = (result.stdout or "").strip().splitlines()[-1:] or [""]
    try:
        payload = json.loads(output[0])
    except json.JSONDecodeError as exc:
        message = (result.stderr or result.stdout or "Steam service bot helper did not return JSON.").strip()
        raise SteamDemoDownloadError(message) from exc
    if result.returncode != 0 or not payload.get("ok"):
        raise SteamDemoDownloadError(str(payload.get("error") or payload.get("code") or "Steam service bot failed."))
    return payload


def _download_demo_file(
    url: str,
    share_code: str,
    storage_budget: SteamImportStorageBudget | None = None,
    progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> Path:
    if not url.startswith(("http://", "https://")):
        raise SteamDemoDownloadError("Steam service bot returned an invalid demo URL.")
    suffix = ".dem.bz2" if url.endswith(".bz2") else ".dem"
    safe_share = share_code.replace("/", "_")
    temp_root = Path(get_settings().temp_dir).resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="jc-steam-demo-", dir=temp_root))
    archive_path = temp_dir / f"{safe_share}{suffix}"
    demo_path = temp_dir / f"{safe_share}.dem"
    request = Request(url, headers={"User-Agent": "jc-coach/0.1"})
    try:
        with urlopen(request, timeout=120) as response:
            content_length = _response_content_length(response)
            if storage_budget is not None:
                storage_budget.reserve_next_demo(content_length)
            _emit_progress(progress_callback, "demo_downloading", share_code=share_code)
            downloaded = _stream_response_to_file(response, archive_path, storage_budget=storage_budget)
            _emit_progress(
                progress_callback,
                "demo_downloaded",
                share_code=share_code,
                downloaded_bytes=downloaded,
            )
            modified_timestamp = _response_modified_timestamp(response)
    except HTTPError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if exc.code in {404, 410, 502}:
            raise SteamDemoDownloadError(
                f"Valve replay CDN returned HTTP {exc.code}; the demo is likely expired or temporarily unavailable."
            ) from exc
        raise
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    if archive_path.suffix == ".bz2":
        _emit_progress(progress_callback, "demo_decompressing", share_code=share_code)
        decompressed = _decompress_bz2_stream(archive_path, demo_path, storage_budget=storage_budget)
        if modified_timestamp:
            os.utime(demo_path, (modified_timestamp, modified_timestamp))
        archive_path.unlink(missing_ok=True)
        if storage_budget is not None:
            storage_budget.record_decompressed(decompressed)
        return demo_path
    if modified_timestamp:
        os.utime(archive_path, (modified_timestamp, modified_timestamp))
    return archive_path


def _stream_response_to_file(
    response,
    destination: Path,
    *,
    storage_budget: SteamImportStorageBudget | None,
) -> int:
    total = 0
    with destination.open("wb") as handle:
        while True:
            try:
                chunk = response.read(DOWNLOAD_CHUNK_BYTES)
            except TypeError:
                chunk = response.read()
            if not chunk:
                break
            total += len(chunk)
            if storage_budget is not None:
                storage_budget.ensure_single_demo_size(total)
                storage_budget.ensure_temp_write(len(chunk), phase="download")
            handle.write(chunk)
    if storage_budget is not None:
        storage_budget.record_downloaded(total)
    return total


def _decompress_bz2_stream(
    archive_path: Path,
    demo_path: Path,
    *,
    storage_budget: SteamImportStorageBudget | None,
) -> int:
    decompressor = bz2.BZ2Decompressor()
    total = 0
    with archive_path.open("rb") as source, demo_path.open("wb") as destination:
        for chunk in iter(lambda: source.read(DOWNLOAD_CHUNK_BYTES), b""):
            data = decompressor.decompress(chunk)
            if not data:
                continue
            total += len(data)
            if storage_budget is not None:
                storage_budget.ensure_single_demo_size(total)
                storage_budget.ensure_temp_write(len(data), phase="decompression")
            destination.write(data)
    return total


def _response_content_length(response) -> int | None:
    value = response.headers.get("Content-Length")
    if not value:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _response_modified_timestamp(response) -> float | None:
    last_modified = response.headers.get("Last-Modified")
    if not last_modified:
        return None
    try:
        parsed = parsedate_to_datetime(last_modified)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def _mark_match_download_error(
    db: Session,
    match: Match,
    message: str,
    retention: dict[str, Any] | None = None,
) -> None:
    raw = _match_raw(match)
    raw.update(
        {
            "status": "demo_download_error",
            "error": message,
            "failed_at": datetime.now(UTC).isoformat(),
            **(retention or {}),
        }
    )
    match.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
    db.commit()


def _mark_match_download_skipped(
    db: Session,
    match: Match,
    steam_metadata: dict[str, Any],
    reason: str,
) -> None:
    raw = _match_raw(match)
    raw.update(
        {
            "status": "ignored_old_history",
            "steam_metadata": steam_metadata,
            "played_at": steam_metadata.get("played_at"),
            "played_at_source": steam_metadata.get("played_at_source"),
            "match_date_status": _match_date_status(steam_metadata),
            "match_date_source": steam_metadata.get("played_at_source") or "unavailable",
            "ignored_reason": reason,
            "next_step": None,
        }
    )
    match.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
    db.commit()


def _share_code_for_match(match: Match) -> str:
    raw = _match_raw(match)
    return str(raw.get("share_code") or match.external_match_id or "").strip()


def _match_raw(match: Match) -> dict[str, Any]:
    try:
        raw = json.loads(match.raw_json or "{}")
    except json.JSONDecodeError:
        raw = {}
    return raw if isinstance(raw, dict) else {}


def _acquisition_metadata(db: Session, match: Match, share_code: str, import_job_id: int | None) -> dict[str, Any]:
    raw = _match_raw(match)
    steam_account_id = raw.get("steam_account_id")
    account = db.get(SteamAccount, steam_account_id) if steam_account_id else None
    return {
        "import_job_id": import_job_id,
        "source_match_id": match.id,
        "source_match_external_id": match.external_match_id,
        "share_code": share_code,
        "steam_account_id": account.id if account else steam_account_id,
        "steam_id": account.steam_id if account else raw.get("steam_id"),
        "user_id": account.user_id if account else None,
    }


def _match_date_status(steam_metadata: dict[str, Any]) -> str:
    if steam_metadata.get("played_at") and steam_metadata.get("played_at_source") == STEAM_GC_PLAYED_AT_SOURCE:
        return "exact_match_date_available"
    return "exact_match_date_unavailable"


def _match_date_truth_note(status: str) -> str:
    if status == "exact_match_date_available":
        return "Exact match datetime came from Steam GC match_time."
    return "Steam GC match_time was unavailable; parser/file timestamps are not treated as exact match date."


def _emit_progress(
    callback: Callable[[str, dict[str, Any]], None] | None,
    phase: str,
    **event: Any,
) -> None:
    if callback is None:
        return
    callback(phase, event)


def _apply_primary_steam_date_truth(match: Match, steam_metadata: dict[str, Any], date_status: str) -> None:
    raw = _match_raw(match)
    raw["steam_metadata"] = steam_metadata
    raw["match_date_status"] = date_status
    raw["match_date_source"] = steam_metadata.get("played_at_source") or "unavailable"
    raw["match_date_truth_note"] = _match_date_truth_note(date_status)
    parsed_match = raw.get("match") if isinstance(raw.get("match"), dict) else None
    if parsed_match is not None:
        parsed_match["match_date_status"] = date_status
        parsed_match["match_date_source"] = raw["match_date_source"]
    if date_status != "exact_match_date_available":
        match.played_at = None
        raw["played_at_source_before_steam_date_truth"] = raw.get("played_at_source")
        raw["played_at"] = None
        raw["played_at_source"] = "unavailable"
        if parsed_match is not None:
            parsed_match["played_at"] = None
            parsed_match["played_at_source"] = "unavailable"
    else:
        match.played_at = parse_steam_match_time(steam_metadata.get("played_at"))
        raw["played_at"] = steam_metadata.get("played_at")
        raw["played_at_source"] = STEAM_GC_PLAYED_AT_SOURCE
    match.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
