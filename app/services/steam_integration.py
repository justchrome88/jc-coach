from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ImportJob, Match, SteamAccount, User
from app.services.app_settings import get_app_setting
from app.services.import_jobs import (
    IMPORT_JOB_ACTIVE_STATUSES,
    IMPORT_JOB_COMPLETED,
    IMPORT_JOB_FAILED,
    IMPORT_JOB_IN_PROGRESS,
    IMPORT_JOB_QUEUED,
    IMPORT_JOB_SKIPPED_DUPLICATE,
    complete_import_job,
    create_import_request,
    fail_import_job,
    start_import_job,
)

STEAM_OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
STEAM_OPENID_CLAIM_PREFIX = "https://steamcommunity.com/openid/id/"
STEAM_MATCH_HISTORY_ENDPOINT = "https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1"
STEAM_SYNC_COOLDOWN_SECONDS = 300
STEAM_INITIAL_CURSOR_SENTINEL = "0"
STEAM_SYNC_SUCCESS_NEW_MATCH_IMPORTED = "SUCCESS_NEW_MATCH_IMPORTED"
STEAM_SYNC_SUCCESS_NO_NEW_MATCHES = "SUCCESS_NO_NEW_MATCHES"
STEAM_SYNC_DUPLICATE_ALREADY_IMPORTED = "DUPLICATE_ALREADY_IMPORTED"
STEAM_SYNC_STEAM_TEMPORARY_ERROR = "STEAM_TEMPORARY_ERROR"
STEAM_IMPORT_SUCCESS = "success"
STEAM_IMPORT_NO_NEW = "no_new"
STEAM_IMPORT_NEED_CODE = "need_code"
STEAM_IMPORT_STEAM_NOT_CONNECTED = "steam_not_connected"
STEAM_IMPORT_RATE_LIMITED = "rate_limited"
STEAM_IMPORT_DOWNLOAD_FAILED = "download_failed"
STEAM_IMPORT_PARSER_FAILED = "parser_failed"
STEAM_IMPORT_PARTIAL_SUCCESS = "partial_success"
STEAM_IMPORT_DUPLICATE_SKIPPED = "duplicate_skipped"
STEAM_IMPORT_EXACT_MATCH_DATE_AVAILABLE = "exact_match_date_available"
STEAM_IMPORT_EXACT_MATCH_DATE_UNAVAILABLE = "exact_match_date_unavailable"
STEAM_IMPORT_APPROXIMATE_MATCH_DATE = "approximate_match_date"
STEAM_IMPORT_DISK_BUDGET_EXCEEDED = "disk_budget_exceeded"
STEAM_IMPORT_BATCH_CAP_REACHED = "batch_cap_reached"
STEAM_IMPORT_DEMO_TOO_LARGE = "demo_too_large"
STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED = "storage_preflight_failed"
STEAM_IMPORT_INTERRUPTED = "interrupted"
STEAM_IMPORT_RUNNING = "running"
STEAM_IMPORT_MAX_CHECKPOINT_EVENTS = 25
STEAM_EXACT_MATCH_DATE_SOURCES = {"steam_gc_match_time"}
SHARE_CODE_DICTIONARY = "ABCDEFGHJKLMNOPQRSTUVWXYZabcdefhijkmnopqrstuvwxyz23456789"
SHARE_CODE_PATTERN = re.compile(rf"^(CSGO)?(-?[{SHARE_CODE_DICTIONARY}]{{5}}){{5}}$")
_BITMASK64 = 2**64 - 1


def steam_login_url() -> str:
    settings = get_settings()
    base_url = settings.public_base_url.rstrip("/")
    return_to = f"{base_url}{settings.steam_return_path}"
    realm = settings.steam_realm or base_url
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return f"{STEAM_OPENID_ENDPOINT}?{urlencode(params)}"


def extract_steam_id(openid_claimed_id: str | None) -> str | None:
    if not openid_claimed_id or not openid_claimed_id.startswith(STEAM_OPENID_CLAIM_PREFIX):
        return None
    steam_id = openid_claimed_id.removeprefix(STEAM_OPENID_CLAIM_PREFIX).strip("/")
    return steam_id if steam_id.isdigit() else None


def link_steam_account(
    db: Session,
    steam_id: str,
    persona_name: str | None = None,
    user_id: int | None = None,
) -> SteamAccount:
    account = db.scalar(select(SteamAccount).where(SteamAccount.steam_id == steam_id))
    if account:
        if persona_name:
            account.persona_name = persona_name
        if user_id:
            account.user_id = user_id
        db.commit()
        db.refresh(account)
        return account
    if user_id is None:
        user = User(display_name=persona_name or f"Steam {steam_id[-4:]}")
        db.add(user)
        db.flush()
        user_id = user.id
    account = SteamAccount(user_id=user_id, steam_id=steam_id, persona_name=persona_name, sync_enabled=0)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def create_steam_import_job(
    db: Session,
    steam_account_id: int | None,
    job_type: str,
    payload: dict[str, Any] | None = None,
    *,
    skip_duplicate: bool = True,
) -> ImportJob:
    user_id: int | None = None
    if steam_account_id is not None:
        account = db.get(SteamAccount, steam_account_id)
        user_id = account.user_id if account else None
    return create_import_request(
        db,
        provider="steam",
        job_type=job_type,
        initial_status=IMPORT_JOB_QUEUED,
        user_id=user_id,
        steam_account_id=steam_account_id,
        payload=payload or {},
        skip_duplicate=skip_duplicate,
    )


def list_steam_accounts(db: Session) -> list[SteamAccount]:
    return list(db.scalars(select(SteamAccount).order_by(SteamAccount.linked_at.desc(), SteamAccount.id.desc())).all())


def list_import_jobs(db: Session, limit: int = 20) -> list[ImportJob]:
    stmt = select(ImportJob).order_by(ImportJob.created_at.desc(), ImportJob.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def list_visible_steam_import_jobs(db: Session, limit: int = 20) -> list[ImportJob]:
    stmt = (
        select(ImportJob)
        .where(ImportJob.provider == "steam")
        .where(ImportJob.job_type.in_(("match_history_sync", "steam_import_all")))
        .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def current_steam_import_all_job(db: Session) -> ImportJob | None:
    return db.scalar(
        select(ImportJob)
        .where(ImportJob.provider == "steam")
        .where(ImportJob.job_type == "steam_import_all")
        .where(ImportJob.status.in_(tuple(IMPORT_JOB_ACTIVE_STATUSES)))
        .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
    )


def queue_steam_import_all(db: Session) -> ImportJob:
    mark_stale_steam_import_all_jobs_interrupted(db)
    running = current_steam_import_all_job(db)
    if running:
        return running
    return create_steam_import_job(
        db,
        None,
        "steam_import_all",
        {"reason": "manual_pull_all", "created_from": "settings_imports"},
    )


def mark_stale_steam_import_all_jobs_interrupted(
    db: Session,
    *,
    now: datetime | None = None,
    timeout_seconds: int | None = None,
    reason: str = "Stale steam_import_all job exceeded the running-job timeout.",
) -> list[ImportJob]:
    settings = get_settings()
    timeout = max(1, int(timeout_seconds or settings.steam_import_stale_running_job_seconds))
    marked: list[ImportJob] = []
    running_jobs = db.scalars(
        select(ImportJob)
        .where(ImportJob.provider == "steam")
        .where(ImportJob.job_type == "steam_import_all")
        .where(ImportJob.status.in_((IMPORT_JOB_IN_PROGRESS, "running")))
        .order_by(ImportJob.created_at.asc(), ImportJob.id.asc())
    ).all()
    for job in running_jobs:
        if is_stale_steam_import_all_job(job, now=now, timeout_seconds=timeout):
            mark_steam_import_all_job_interrupted(db, job, reason=reason)
            marked.append(job)
    return marked


def is_stale_steam_import_all_job(
    job: ImportJob,
    *,
    now: datetime | None = None,
    timeout_seconds: int | None = None,
) -> bool:
    if (
        job.provider != "steam"
        or job.job_type != "steam_import_all"
        or job.status not in {IMPORT_JOB_IN_PROGRESS, "running"}
    ):
        return False
    settings = get_settings()
    timeout = max(1, int(timeout_seconds or settings.steam_import_stale_running_job_seconds))
    reference = job.started_at or job.created_at
    if reference is None:
        return True
    current = now or _now()
    return reference <= current - timedelta(seconds=timeout)


def mark_steam_import_all_job_interrupted(
    db: Session,
    job: ImportJob,
    *,
    reason: str = "steam_import_all job was interrupted.",
    now: datetime | None = None,
) -> ImportJob:
    if job.provider != "steam" or job.job_type != "steam_import_all":
        raise ValueError("Only steam_import_all jobs can be marked interrupted.")
    previous = _json_loads(job.result_json)
    progress = previous.get("progress") if isinstance(previous.get("progress"), dict) else {}
    interrupted_at = (now or _now()).isoformat()
    progress = _bounded_progress(
        {
            **progress,
            "phase": STEAM_IMPORT_INTERRUPTED,
            "updated_at": interrupted_at,
        },
        {
            "phase": STEAM_IMPORT_INTERRUPTED,
            "at": interrupted_at,
            "reason": reason,
        },
    )
    result = {
        "overall_outcome": STEAM_IMPORT_INTERRUPTED,
        "statuses": [STEAM_IMPORT_INTERRUPTED],
        "status_summary": {STEAM_IMPORT_INTERRUPTED: 1},
        "clean_success": False,
        "error_message": reason,
        "interrupted_at": interrupted_at,
        "previous_overall_outcome": previous.get("overall_outcome"),
        "progress": progress,
    }
    return fail_import_job(db, job, reason, result=result)


def steam_import_overview(db: Session) -> dict[str, Any]:
    matches = db.scalars(select(Match).where(Match.source == "steam_history")).all()
    status_counts: dict[str, int] = {}
    latest_error: str | None = None
    for match in matches:
        raw = _json_loads(match.raw_json)
        status = str(raw.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == "demo_download_error" and not latest_error:
            latest_error = str(raw.get("error") or "")
    accounts = list_steam_accounts(db)
    account_states = [_steam_account_import_state(db, account) for account in accounts]
    current_job = current_steam_import_all_job(db)
    return {
        "accounts_count": len(accounts),
        "steam_history_matches": len(matches),
        "pending_demo_download": status_counts.get("demo_download_pending", 0),
        "demo_download_errors": status_counts.get("demo_download_error", 0),
        "demo_imported": status_counts.get("demo_imported", 0),
        "latest_error": latest_error,
        "has_ready_account": any(account.match_auth_code and account.last_share_code for account in accounts),
        "account_states": account_states,
        "current_job": current_job,
    }


def clear_steam_demo_download_errors(db: Session) -> dict[str, int]:
    matches = db.scalars(select(Match).where(Match.source == "steam_history")).all()
    cleared = 0
    for match in matches:
        raw = _json_loads(match.raw_json)
        if raw.get("status") != "demo_download_error":
            continue
        raw.pop("error", None)
        raw.pop("failed_at", None)
        raw["status"] = "demo_download_pending"
        raw["download_method"] = "steam_service_bot_pending"
        raw["next_step"] = "download_demo_with_steam_service_bot"
        match.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
        cleared += 1
    db.commit()
    return {"cleared": cleared}


def update_match_auth_code(
    db: Session,
    steam_account_id: int,
    match_auth_code: str,
    latest_share_code: str | None = None,
) -> SteamAccount:
    account = db.get(SteamAccount, steam_account_id)
    if account is None:
        raise ValueError("Steam account was not found.")
    code = match_auth_code.strip()
    if not code:
        raise ValueError("Game Authentication Code is required.")
    if code.upper().startswith("CSGO-"):
        raise ValueError(
            "This looks like a match share code. Paste the Game Authentication Code from Steam Support instead."
        )
    account.match_auth_code = code
    if latest_share_code is not None:
        share_code = latest_share_code.strip()
        if not share_code:
            raise ValueError("Latest match share code is required.")
        if not share_code.upper().startswith("CSGO-"):
            raise ValueError("Latest match share code should start with CSGO-.")
        account.last_share_code = share_code
        _store_steam_share_code_match(db, account, share_code)
    account.sync_enabled = 1
    db.commit()
    db.refresh(account)
    create_steam_import_job(
        db,
        account.id,
        "match_history_sync",
        {"steam_id": account.steam_id, "has_match_auth_code": True, "reason": "auth_code_saved"},
    )
    return account


def queue_match_history_sync(db: Session, steam_account_id: int) -> ImportJob:
    account = db.get(SteamAccount, steam_account_id)
    if account is None:
        raise ValueError("Steam account was not found.")
    if not account.match_auth_code:
        raise ValueError("Game Authentication Code is required before sync.")
    account.sync_enabled = 1
    db.commit()
    return create_steam_import_job(
        db,
        account.id,
        "match_history_sync",
        {"steam_id": account.steam_id, "has_match_auth_code": True, "reason": "manual_queue"},
        skip_duplicate=False,
    )


def sync_match_history_job(db: Session, job_id: int) -> dict[str, Any]:
    job = db.get(ImportJob, job_id)
    if job is None:
        raise ValueError("Import job was not found.")
    if job.provider != "steam" or job.job_type != "match_history_sync":
        raise ValueError("Only steam match_history_sync jobs can be processed here.")
    if job.status == IMPORT_JOB_IN_PROGRESS:
        return _job_result(job)
    if job.status in {IMPORT_JOB_COMPLETED, IMPORT_JOB_FAILED, IMPORT_JOB_SKIPPED_DUPLICATE, "succeeded"}:
        return _job_result(job)
    account = db.get(SteamAccount, job.steam_account_id) if job.steam_account_id else None
    if account is None:
        return _fail_job(db, job, "Steam account was not found.")
    if not account.match_auth_code:
        return _fail_job(db, job, "Game Authentication Code is missing.")

    settings = get_settings()
    steam_web_api_key = settings.steam_web_api_key or get_app_setting(db, "steam_web_api_key")
    if not steam_web_api_key:
        return _fail_job(
            db,
            job,
            "STEAM_WEB_API_KEY is missing. Add it to .env to call GetNextMatchSharingCode.",
        )

    start_import_job(db, job)

    try:
        payload = _json_loads(job.requested_payload_json)
        cursor = steam_cursor_source(account, payload.get("known_share_code"))
        known_code = cursor["known_code"]
        max_codes = max(1, min(int(settings.steam_sync_max_codes), 100))
        collected = _collect_match_share_codes(
            steam_web_api_key=steam_web_api_key,
            steam_id=account.steam_id,
            steam_id_key=account.match_auth_code,
            known_code=known_code,
            max_codes=max_codes,
        )
        inserted = 0
        duplicates = 0
        for share_code in collected:
            was_inserted = _store_steam_share_code_match(db, account, share_code)
            inserted += 1 if was_inserted else 0
            duplicates += 0 if was_inserted else 1
        cursor_advanced = advance_steam_cursor_after_success(account, collected)
        account.last_sync_at = datetime.now(UTC).replace(tzinfo=None)
        account.sync_enabled = 1
        result = {
            "sync_outcome": classify_steam_sync_outcome(collected, inserted, duplicates),
            "known_code": known_code,
            "cursor_source": cursor["source"],
            "knowncode_zero_is_initial_sentinel": cursor["initial_sentinel"],
            "collected": len(collected),
            "collected_share_codes": collected,
            "inserted": inserted,
            "duplicates": duplicates,
            "cursor_advanced": cursor_advanced,
            "last_share_code": account.last_share_code,
            "note": (
                "Steam share codes were saved. The account cursor advances only after the Steam API call "
                "and local share-code persistence complete successfully."
            ),
        }
        complete_import_job(db, job, result=result)
        return _job_result(job)
    except Exception as exc:
        return _fail_job(db, job, str(exc), sync_outcome=STEAM_SYNC_STEAM_TEMPORARY_ERROR)

def process_queued_steam_jobs(db: Session, limit: int = 5) -> list[dict[str, Any]]:
    jobs = db.scalars(
        select(ImportJob)
        .where(ImportJob.provider == "steam")
        .where(ImportJob.job_type == "match_history_sync")
        .where(ImportJob.status == IMPORT_JOB_QUEUED)
        .order_by(ImportJob.created_at.asc(), ImportJob.id.asc())
        .limit(limit)
    ).all()
    return [sync_match_history_job(db, job.id) for job in jobs]


def run_steam_import_all_job(db: Session, job_id: int) -> dict[str, Any]:
    job = db.get(ImportJob, job_id)
    if job is None:
        raise ValueError("Import job was not found.")
    if job.provider != "steam" or job.job_type != "steam_import_all":
        raise ValueError("Only steam_import_all jobs can be processed here.")
    if job.status in {IMPORT_JOB_IN_PROGRESS, "running"}:
        return {"id": job.id, "status": job.status, "result": None, "error": None}
    if job.status in {IMPORT_JOB_COMPLETED, "succeeded"}:
        return {"id": job.id, "status": job.status, "result": _json_loads(job.result_json), "error": None}
    if job.status in {IMPORT_JOB_FAILED, IMPORT_JOB_SKIPPED_DUPLICATE}:
        return {
            "id": job.id,
            "status": job.status,
            "result": _json_loads(job.result_json),
            "error": job.error_message,
        }

    try:
        settings = get_settings()
        from app.services.steam_storage_guard import SteamImportStorageBudget, SteamStorageBudgetExceeded

        storage_budget = SteamImportStorageBudget()
        try:
            storage_preflight = storage_budget.preflight()
        except SteamStorageBudgetExceeded as exc:
            result = {
                "overall_outcome": STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED,
                "statuses": [STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED, exc.status],
                "status_summary": {STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED: 1, exc.status: 1},
                "clean_success": False,
                "error_message": str(exc),
                "storage_budget": exc.budget,
                "job_status_limitation": (
                    "ImportJob.status uses requested/queued/in_progress/completed/failed/skipped_duplicate; "
                    "storage safety blocks "
                    "are represented in result_json.statuses and persisted as failed."
                ),
            }
            start_import_job(db, job)
            fail_import_job(db, job, str(exc), result=result)
            return {"id": job.id, "status": job.status, "result": result, "error": job.error_message}

        start_import_job(db, job)
        checkpoint_steam_import_all_job(
            db,
            job,
            "started",
            storage_budget=storage_budget,
            extra={"storage_preflight": _compact_storage_budget(storage_preflight)},
        )

        accounts = list_steam_accounts(db)
        sync_results = []
        account_states = []
        fresh_share_codes: list[str] = []
        latest_played_at = _latest_exact_imported_match_played_at(db)
        for account in accounts:
            checkpoint_steam_import_all_job(
                db,
                job,
                "account_checked",
                storage_budget=storage_budget,
                event={"steam_account_id": account.id},
            )
            if not account.match_auth_code or not account.last_share_code:
                account_states.append(
                    {
                        "steam_account_id": account.id,
                        "status": STEAM_IMPORT_NEED_CODE,
                        "error": "Steam account is missing match token or authentication code.",
                        "has_match_auth_code": bool(account.match_auth_code),
                        "has_last_share_code": bool(account.last_share_code),
                    }
                )
                continue
            saved_share_code = account.last_share_code.strip()
            try:
                decode_match_share_code(saved_share_code)
            except ValueError as exc:
                account_states.append(
                    {
                        "steam_account_id": account.id,
                        "status": STEAM_IMPORT_NEED_CODE,
                        "error": str(exc),
                        "has_match_auth_code": bool(account.match_auth_code),
                        "has_last_share_code": bool(account.last_share_code),
                    }
                )
                continue
            account_states.append(
                {
                    "steam_account_id": account.id,
                    "status": "ready",
                    "has_match_auth_code": True,
                    "has_last_share_code": True,
                }
            )
            _store_steam_share_code_match(db, account, saved_share_code)
            fresh_share_codes.append(saved_share_code)
            sync_job = queue_match_history_sync(db, account.id)
            checkpoint_steam_import_all_job(
                db,
                job,
                "share_codes_fetch_started",
                child_job_ids=[sync_job.id],
                current_share_code=saved_share_code,
                storage_budget=storage_budget,
                event={"child_job_id": sync_job.id, "share_code": saved_share_code},
            )
            sync_result = sync_match_history_job(db, sync_job.id)
            sync_results.append(sync_result)
            result_payload = sync_result.get("result") or {}
            fresh_share_codes.extend(result_payload.get("collected_share_codes") or [])
            checkpoint_steam_import_all_job(
                db,
                job,
                "share_codes_fetched",
                child_job_ids=[sync_job.id],
                current_share_code=saved_share_code,
                storage_budget=storage_budget,
                event={
                    "child_job_id": sync_job.id,
                    "share_code": saved_share_code,
                    "status": sync_result.get("status"),
                },
            )
        fresh_share_codes = list(dict.fromkeys(fresh_share_codes))

        demo_status = mark_steam_history_demo_download_status(db, share_codes=fresh_share_codes)
        checkpoint_steam_import_all_job(
            db,
            job,
            "demo_queued",
            counters={"pending": demo_status.get("pending_demo_download", 0)},
            storage_budget=storage_budget,
            event={"status": "demo_download_pending"},
        )
        from app.services.steam_demo_downloader import download_pending_steam_demos

        def progress_callback(phase: str, event: dict[str, Any]) -> None:
            checkpoint_steam_import_all_job(
                db,
                job,
                phase,
                counters=event.get("counters") if isinstance(event.get("counters"), dict) else None,
                current_share_code=event.get("share_code"),
                storage_budget=storage_budget,
                event=event,
            )

        demo_download = download_pending_steam_demos(
            db,
            limit=max(1, int(settings.steam_import_max_demos_per_run)),
            share_codes=fresh_share_codes,
            min_played_at=latest_played_at,
            storage_budget=storage_budget,
            progress_callback=progress_callback,
        )
        if demo_download.get("budget_status"):
            checkpoint_steam_import_all_job(
                db,
                job,
                str(demo_download["budget_status"]),
                counters={
                    "processed": demo_download.get("processed", 0),
                    "imported": demo_download.get("imported", 0),
                    "failed": demo_download.get("failed", 0),
                    "skipped": demo_download.get("skipped", 0),
                    "pending": demo_download.get("pending", 0),
                },
                storage_budget=storage_budget,
                event={"budget_status": demo_download.get("budget_status")},
            )
        if demo_download.get("batch_cap_reached"):
            checkpoint_steam_import_all_job(
                db,
                job,
                "batch_cap_reached",
                counters={
                    "processed": demo_download.get("processed", 0),
                    "imported": demo_download.get("imported", 0),
                    "failed": demo_download.get("failed", 0),
                    "skipped": demo_download.get("skipped", 0),
                    "pending": demo_download.get("pending", 0),
                },
                storage_budget=storage_budget,
                event={
                    "batch_cap_reached": True,
                    "remaining_pending": demo_download.get("remaining_pending"),
                },
            )
        taxonomy = classify_steam_import_all_result(
            accounts_count=len(accounts),
            account_states=account_states,
            sync_results=sync_results,
            demo_download=demo_download,
        )
        checkpoint_payload = _json_loads(job.result_json)
        progress = checkpoint_payload.get("progress") if isinstance(checkpoint_payload.get("progress"), dict) else {}
        result = {
            **taxonomy,
            "accounts": len(accounts),
            "account_states": account_states,
            "sync_jobs": sync_results,
            "demo_status": demo_status,
            "demo_download": demo_download,
            "storage_preflight": storage_preflight,
            "progress": progress,
            "latest_imported_played_at_before_job": latest_played_at.isoformat() if latest_played_at else None,
            "latest_imported_played_at_source_policy": "exact_only:steam_gc_match_time",
            "note": (
                "Synced share codes through Steam Web API, then used Steam GC match_time as the authoritative "
                "date before downloading demos. Candidates older than the latest exact imported Steam match "
                "are skipped."
            ),
        }
        if taxonomy["clean_success"]:
            complete_import_job(db, job, result=result)
        else:
            fail_import_job(db, job, str(taxonomy["error_message"]), result=result)
        return {"id": job.id, "status": job.status, "result": result, "error": job.error_message}
    except Exception as exc:
        return _fail_job(db, job, str(exc))


def run_startup_stale_steam_import_repair(db: Session) -> list[ImportJob]:
    settings = get_settings()
    if not settings.steam_import_repair_stale_on_startup:
        return []
    return mark_stale_steam_import_all_jobs_interrupted(
        db,
        reason="Stale steam_import_all job was interrupted during application startup repair.",
    )


def import_all_available_steam_matches(db: Session) -> dict[str, Any]:
    job = queue_steam_import_all(db)
    return run_steam_import_all_job(db, job.id)


def import_steam_share_code_demo(db: Session, steam_account_id: int, share_code_input: str) -> dict[str, Any]:
    account = db.get(SteamAccount, steam_account_id)
    if account is None:
        raise ValueError("Steam account was not found.")
    parsed = parse_share_code_input(share_code_input)
    share_code = str(parsed["share_code"]).strip()
    decode_match_share_code(share_code)
    job = create_steam_import_job(
        db,
        account.id,
        "share_code_import",
        {
            "steam_id": account.steam_id,
            "share_code": share_code,
            "created_from": "settings_imports_exact_share_code",
            "primary_path": False,
        },
    )
    start_import_job(db, job)
    was_inserted = _store_steam_share_code_match(db, account, share_code)
    account.last_share_code = share_code
    account.last_sync_at = datetime.now(UTC).replace(tzinfo=None)
    account.sync_enabled = 1
    db.commit()

    try:
        demo_status = mark_steam_history_demo_download_status(db, share_codes=[share_code])
        from app.services.steam_demo_downloader import download_pending_steam_demos

        demo_download = download_pending_steam_demos(db, limit=1, share_codes=[share_code])
        taxonomy = classify_steam_import_all_result(
            accounts_count=1,
            account_states=[
                {
                    "steam_account_id": account.id,
                    "status": "ready",
                    "has_match_auth_code": bool(account.match_auth_code),
                    "has_last_share_code": True,
                }
            ],
            sync_results=[],
            demo_download=demo_download,
        )
        result = {
            **taxonomy,
            "share_code": share_code,
            "inserted": was_inserted,
            "demo_status": demo_status,
            "demo_download": demo_download,
            "primary_path": False,
            "note": "Exact share-code import is tracked but remains a non-primary debug/manual path.",
        }
        if taxonomy["clean_success"]:
            complete_import_job(db, job, result=result)
        else:
            fail_import_job(db, job, str(taxonomy["error_message"]), result=result)
        return {**result, "job_id": job.id, "job_status": job.status, "job_error": job.error_message}
    except Exception as exc:
        failed = _fail_job(db, job, str(exc))
        raise ValueError(str(failed["error"])) from exc


def classify_steam_import_all_result(
    *,
    accounts_count: int,
    account_states: list[dict[str, Any]],
    sync_results: list[dict[str, Any]],
    demo_download: dict[str, Any],
) -> dict[str, Any]:
    statuses: list[str] = []
    failure_reasons: list[str] = []
    imported = int(demo_download.get("imported") or 0)
    failed = int(demo_download.get("failed") or 0)
    skipped = int(demo_download.get("skipped") or 0)
    pending = int(demo_download.get("pending") or 0)

    if accounts_count == 0:
        statuses.append(STEAM_IMPORT_STEAM_NOT_CONNECTED)
        failure_reasons.append("No Steam account is connected.")
    if any(state.get("status") == STEAM_IMPORT_NEED_CODE for state in account_states):
        statuses.append(STEAM_IMPORT_NEED_CODE)
        failure_reasons.append("At least one Steam account is missing a Game Authentication Code or share-code cursor.")

    sync_outcomes = [
        (item.get("result") or {}).get("sync_outcome")
        for item in sync_results
        if isinstance(item.get("result"), dict)
    ]
    if any(item.get("status") == "failed" for item in sync_results):
        errors = " ".join(str(item.get("error") or "") for item in sync_results)
        if _looks_rate_limited(errors):
            statuses.append(STEAM_IMPORT_RATE_LIMITED)
        else:
            statuses.append(STEAM_IMPORT_DOWNLOAD_FAILED)
        failure_reasons.append("At least one Steam share-code sync job failed.")
    if sync_outcomes and all(outcome == STEAM_SYNC_SUCCESS_NO_NEW_MATCHES for outcome in sync_outcomes):
        statuses.append(STEAM_IMPORT_NO_NEW)
    if sync_outcomes and all(outcome == STEAM_SYNC_DUPLICATE_ALREADY_IMPORTED for outcome in sync_outcomes):
        statuses.append(STEAM_IMPORT_DUPLICATE_SKIPPED)

    if demo_download.get("configured") is False and pending:
        statuses.append(STEAM_IMPORT_DOWNLOAD_FAILED)
        failure_reasons.append(str(demo_download.get("message") or "Steam demo downloader is not configured."))
    budget_status = demo_download.get("budget_status")
    if budget_status:
        statuses.append(str(budget_status))
        if budget_status in {
            STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
            STEAM_IMPORT_DEMO_TOO_LARGE,
            STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED,
        }:
            failure_reasons.append(f"Steam import storage guard stopped demo processing: {budget_status}.")
    if demo_download.get("batch_cap_reached"):
        statuses.append(STEAM_IMPORT_BATCH_CAP_REACHED)
    if failed:
        failure_status = _classify_demo_failure_status(demo_download)
        statuses.append(failure_status)
        failure_reasons.append(f"{failed} demo download/parser task(s) failed.")
    if imported:
        statuses.append(STEAM_IMPORT_SUCCESS)
    if skipped and not imported and not failed and not pending:
        statuses.append(STEAM_IMPORT_NO_NEW)
    if skipped:
        statuses.append(STEAM_IMPORT_DUPLICATE_SKIPPED)

    date_status = _exact_date_status(demo_download)
    statuses.append(date_status)

    statuses = _dedupe_statuses(statuses)
    has_failure = any(
        status in statuses
        for status in (
            STEAM_IMPORT_NEED_CODE,
            STEAM_IMPORT_STEAM_NOT_CONNECTED,
            STEAM_IMPORT_RATE_LIMITED,
            STEAM_IMPORT_DOWNLOAD_FAILED,
            STEAM_IMPORT_PARSER_FAILED,
            STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
            STEAM_IMPORT_DEMO_TOO_LARGE,
            STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED,
        )
    )
    has_success = any(status in statuses for status in (STEAM_IMPORT_SUCCESS, STEAM_IMPORT_DUPLICATE_SKIPPED))
    if not has_failure and STEAM_IMPORT_NO_NEW in statuses:
        has_success = True
    if has_failure and has_success:
        statuses = _dedupe_statuses([STEAM_IMPORT_PARTIAL_SUCCESS, *statuses])
    if not has_failure and not has_success:
        statuses = _dedupe_statuses([STEAM_IMPORT_NO_NEW, *statuses])
        has_success = True

    failure_order = [
        STEAM_IMPORT_STEAM_NOT_CONNECTED,
        STEAM_IMPORT_NEED_CODE,
        STEAM_IMPORT_RATE_LIMITED,
        STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED,
        STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
        STEAM_IMPORT_DEMO_TOO_LARGE,
        STEAM_IMPORT_PARSER_FAILED,
        STEAM_IMPORT_DOWNLOAD_FAILED,
    ]
    overall = STEAM_IMPORT_PARTIAL_SUCCESS if STEAM_IMPORT_PARTIAL_SUCCESS in statuses else statuses[0]
    if has_failure and STEAM_IMPORT_PARTIAL_SUCCESS not in statuses:
        overall = next((status for status in failure_order if status in statuses), overall)
    clean_success = not has_failure and overall in {
        STEAM_IMPORT_SUCCESS,
        STEAM_IMPORT_NO_NEW,
        STEAM_IMPORT_DUPLICATE_SKIPPED,
    }
    if clean_success and STEAM_IMPORT_SUCCESS in statuses:
        overall = STEAM_IMPORT_SUCCESS
    elif clean_success and STEAM_IMPORT_DUPLICATE_SKIPPED in statuses:
        overall = STEAM_IMPORT_DUPLICATE_SKIPPED
    elif clean_success:
        overall = STEAM_IMPORT_NO_NEW

    error_message = None
    if not clean_success:
        error_message = "; ".join(_dedupe_statuses(failure_reasons)) or f"Steam import outcome: {overall}"
    return {
        "overall_outcome": overall,
        "statuses": statuses,
        "status_summary": {status: statuses.count(status) for status in statuses},
        "clean_success": clean_success,
        "error_message": error_message,
        "job_status_limitation": (
            "ImportJob.status uses requested/queued/in_progress/completed/failed/skipped_duplicate; "
            "partial_success is represented "
            "in result_json.overall_outcome/statuses and persisted as failed to avoid clean-success overclaim."
        ),
    }


def _classify_demo_failure_status(demo_download: dict[str, Any]) -> str:
    errors = " ".join(
        " ".join(str(value) for value in (item.get("budget_status"), item.get("error")) if value)
        for item in demo_download.get("results", [])
        if isinstance(item, dict)
    )
    if STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED in errors:
        return STEAM_IMPORT_STORAGE_PREFLIGHT_FAILED
    if STEAM_IMPORT_DISK_BUDGET_EXCEEDED in errors:
        return STEAM_IMPORT_DISK_BUDGET_EXCEEDED
    if STEAM_IMPORT_DEMO_TOO_LARGE in errors:
        return STEAM_IMPORT_DEMO_TOO_LARGE
    if _looks_rate_limited(errors):
        return STEAM_IMPORT_RATE_LIMITED
    if "parser failed" in errors.lower() or "demoparse" in errors.lower():
        return STEAM_IMPORT_PARSER_FAILED
    return STEAM_IMPORT_DOWNLOAD_FAILED


def _exact_date_status(demo_download: dict[str, Any]) -> str:
    results = [item for item in demo_download.get("results", []) if isinstance(item, dict)]
    if any(
        item.get("match_date_status") == STEAM_IMPORT_EXACT_MATCH_DATE_AVAILABLE
        or (item.get("played_at_source") == "steam_gc_match_time" and item.get("played_at"))
        for item in results
    ):
        return STEAM_IMPORT_EXACT_MATCH_DATE_AVAILABLE
    if any(item.get("match_date_status") == STEAM_IMPORT_EXACT_MATCH_DATE_UNAVAILABLE for item in results):
        return STEAM_IMPORT_EXACT_MATCH_DATE_UNAVAILABLE
    if any(
        item.get("match_date_status") == STEAM_IMPORT_APPROXIMATE_MATCH_DATE or item.get("played_at_source")
        for item in results
    ):
        return STEAM_IMPORT_APPROXIMATE_MATCH_DATE
    return STEAM_IMPORT_EXACT_MATCH_DATE_UNAVAILABLE


def _looks_rate_limited(message: str) -> bool:
    normalized = message.lower()
    return "429" in normalized or "rate limit" in normalized or "too many requests" in normalized


def _dedupe_statuses(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def mark_steam_history_demo_download_status(db: Session, share_codes: list[str] | None = None) -> dict[str, Any]:
    stmt = select(Match).where(Match.source == "steam_history").order_by(Match.id.desc())
    if share_codes is not None:
        normalized_codes = [code.strip() for code in share_codes if code and code.strip()]
        if not normalized_codes:
            return {
                "steam_history_matches": 0,
                "decoded": 0,
                "pending_demo_download": 0,
                "already_has_demo": 0,
                "errors": 0,
            }
        stmt = stmt.where(Match.external_match_id.in_(normalized_codes))
    matches = db.scalars(stmt).all()
    decoded = 0
    pending = 0
    errors = 0
    already_has_demo = 0
    for match in matches:
        raw = _json_loads(match.raw_json)
        share_code = str(raw.get("share_code") or match.external_match_id or "").strip()
        if not share_code:
            errors += 1
            raw.update({"status": "demo_download_error", "error": "Steam share code is missing."})
        else:
            try:
                decoded_info = decode_match_share_code(share_code)
                decoded += 1
                raw.update({"decoded": decoded_info})
                if match.demo_file:
                    already_has_demo += 1
                    raw.update({"status": "demo_imported", "next_step": None})
                else:
                    pending += 1
                    raw.update(
                        {
                            "status": "demo_download_pending",
                            "download_method": "steam_service_bot_pending",
                            "next_step": "download_demo_with_steam_service_bot",
                        }
                    )
            except ValueError as exc:
                errors += 1
                raw.update({"status": "demo_download_error", "error": str(exc)})
        match.raw_json = json.dumps(raw, ensure_ascii=False, default=str)
    db.commit()
    return {
        "steam_history_matches": len(matches),
        "decoded": decoded,
        "pending_demo_download": pending,
        "already_has_demo": already_has_demo,
        "errors": errors,
    }


def mark_job_failed(db: Session, job: ImportJob, message: str) -> ImportJob:
    return fail_import_job(db, job, message)


def validate_openid_callback(query_params: dict[str, str]) -> tuple[str | None, str | None]:
    mode = query_params.get("openid.mode")
    if mode == "cancel":
        return None, "Steam login was cancelled."
    steam_id = extract_steam_id(query_params.get("openid.claimed_id"))
    if not steam_id:
        return None, "SteamID was not found in OpenID callback."
    if not _verify_openid_assertion(query_params):
        return None, "Steam OpenID verification failed."
    return steam_id, None


def _verify_openid_assertion(query_params: dict[str, str]) -> bool:
    params = dict(query_params)
    params["openid.mode"] = "check_authentication"
    request = Request(
        f"{STEAM_OPENID_ENDPOINT}?{urlencode(params)}",
        headers={"User-Agent": "jc-coach/0.1"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
    except Exception:
        return False
    values = {}
    for line in body.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values.get("is_valid") == "true"


def parse_share_code_input(value: str) -> dict[str, Any]:
    text = value.strip()
    if not text:
        raise ValueError("Share code is required.")
    parsed = urlparse(text)
    if parsed.query:
        query = parse_qs(parsed.query)
        known_values = query.get("code") or query.get("sharecode") or query.get("match")
        if known_values:
            text = known_values[0]
    return {"share_code": text}


def decode_match_share_code(code: str) -> dict[str, int]:
    if not SHARE_CODE_PATTERN.match(code):
        raise ValueError("Invalid Steam match share code.")
    payload = re.sub(r"CSGO\-|\-", "", code)[::-1]
    number = 0
    for char in payload:
        number = number * len(SHARE_CODE_DICTIONARY) + SHARE_CODE_DICTIONARY.index(char)
    number = _swap_share_code_endianness(number)
    return {
        "matchid": number & _BITMASK64,
        "outcomeid": (number >> 64) & _BITMASK64,
        "token": (number >> 128) & 0xFFFF,
    }


def _swap_share_code_endianness(number: int) -> int:
    result = 0
    for offset in range(0, 144, 8):
        result = (result << 8) + ((number >> offset) & 0xFF)
    return result


def _collect_match_share_codes(
    steam_web_api_key: str,
    steam_id: str,
    steam_id_key: str,
    known_code: str,
    max_codes: int,
) -> list[str]:
    codes: list[str] = []
    current = known_code
    seen = {known_code}
    for _ in range(max_codes):
        next_code = _get_next_match_sharing_code(
            steam_web_api_key=steam_web_api_key,
            steam_id=steam_id,
            steam_id_key=steam_id_key,
            known_code=current,
        )
        if not next_code or next_code in seen:
            break
        codes.append(next_code)
        seen.add(next_code)
        current = next_code
    return codes


def steam_cursor_source(account: SteamAccount, requested_known_code: Any = None) -> dict[str, Any]:
    requested = str(requested_known_code or "").strip()
    if requested:
        return {"known_code": requested, "source": "job_requested_payload", "initial_sentinel": False}
    saved = str(account.last_share_code or "").strip()
    if saved:
        return {"known_code": saved, "source": "steam_account.last_share_code", "initial_sentinel": False}
    return {
        "known_code": STEAM_INITIAL_CURSOR_SENTINEL,
        "source": "initial_sentinel_no_saved_cursor",
        "initial_sentinel": True,
    }


def advance_steam_cursor_after_success(account: SteamAccount, collected_share_codes: list[str]) -> bool:
    normalized = [code.strip() for code in collected_share_codes if code and code.strip()]
    if not normalized:
        return False
    latest_collected = normalized[-1]
    if account.last_share_code == latest_collected:
        return False
    account.last_share_code = latest_collected
    return True


def classify_steam_sync_outcome(collected_share_codes: list[str], inserted: int, duplicates: int) -> str:
    if not collected_share_codes:
        return STEAM_SYNC_SUCCESS_NO_NEW_MATCHES
    if duplicates == len(collected_share_codes) and inserted == 0:
        return STEAM_SYNC_DUPLICATE_ALREADY_IMPORTED
    return STEAM_SYNC_SUCCESS_NEW_MATCH_IMPORTED


def _get_next_match_sharing_code(
    steam_web_api_key: str,
    steam_id: str,
    steam_id_key: str,
    known_code: str,
) -> str | None:
    params = {
        "key": steam_web_api_key,
        "steamid": steam_id,
        "steamidkey": steam_id_key,
        "knowncode": known_code,
    }
    request = Request(f"{STEAM_MATCH_HISTORY_ENDPOINT}?{urlencode(params)}", headers={"User-Agent": "jc-coach/0.1"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return None
    next_code = result.get("nextcode")
    if not isinstance(next_code, str):
        return None
    normalized = next_code.strip()
    if not normalized or normalized.upper() in {"N/A", "NA", "NONE"}:
        return None
    return normalized


def _store_steam_share_code_match(db: Session, account: SteamAccount, share_code: str) -> bool:
    match = Match(
        source="steam_history",
        external_match_id=share_code,
        mode="Valve Matchmaking",
        raw_json=json.dumps(
            {
                "provider": "steam",
                "steam_account_id": account.id,
                "steam_id": account.steam_id,
                "share_code": share_code,
                "status": "share_code_collected",
                "next_step": "download_demo_and_parse",
            },
            ensure_ascii=False,
        ),
    )
    db.add(match)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


def _latest_imported_match_played_at(db: Session) -> datetime | None:
    return db.scalar(
        select(Match.played_at)
        .where(Match.source != "steam_history")
        .where(Match.played_at.is_not(None))
        .order_by(Match.played_at.desc(), Match.id.desc())
        .limit(1)
    )


def _latest_exact_imported_match_played_at(db: Session) -> datetime | None:
    matches = db.scalars(
        select(Match)
        .where(Match.source != "steam_history")
        .where(Match.played_at.is_not(None))
        .order_by(Match.played_at.desc(), Match.id.desc())
    ).all()
    for match in matches:
        if match.played_at and match_date_truth(match).get("is_exact"):
            return match.played_at
    return None


def match_date_truth(match: Match) -> dict[str, Any]:
    raw = _json_loads(match.raw_json)
    match_raw = raw.get("match") if isinstance(raw.get("match"), dict) else {}
    steam_metadata = raw.get("steam_metadata") if isinstance(raw.get("steam_metadata"), dict) else {}
    source = (
        raw.get("played_at_source")
        or raw.get("match_date_source")
        or match_raw.get("played_at_source")
        or steam_metadata.get("played_at_source")
        or "unknown"
    )
    source = str(source)
    if source in STEAM_EXACT_MATCH_DATE_SOURCES and match.played_at:
        status = STEAM_IMPORT_EXACT_MATCH_DATE_AVAILABLE
        is_exact = True
    elif source == "unknown" or match.played_at is None:
        status = STEAM_IMPORT_EXACT_MATCH_DATE_UNAVAILABLE
        is_exact = False
    else:
        status = STEAM_IMPORT_APPROXIMATE_MATCH_DATE
        is_exact = False
    return {
        "status": status,
        "source": source,
        "is_exact": is_exact,
        "played_at": match.played_at.isoformat() if match.played_at else None,
    }


def _steam_account_import_state(db: Session, account: SteamAccount) -> dict[str, Any]:
    share_code = (account.last_share_code or "").strip()
    match = None
    raw: dict[str, Any] = {}
    if share_code:
        match = db.scalar(
            select(Match)
            .where(Match.source == "steam_history")
            .where(Match.external_match_id == share_code)
            .order_by(Match.id.desc())
            .limit(1)
        )
        if match:
            raw = _json_loads(match.raw_json)
    steam_metadata = raw.get("steam_metadata") if isinstance(raw.get("steam_metadata"), dict) else {}
    played_at = raw.get("played_at") or steam_metadata.get("played_at")
    played_at_source = raw.get("played_at_source") or steam_metadata.get("played_at_source")
    latest_imported = _latest_exact_imported_match_played_at(db)
    anchor_is_older = False
    if played_at and latest_imported:
        try:
            parsed = datetime.fromisoformat(str(played_at).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(UTC).replace(tzinfo=None)
            anchor_is_older = parsed <= latest_imported
        except ValueError:
            anchor_is_older = False
    return {
        "steam_account_id": account.id,
        "steam_id": account.steam_id,
        "has_match_auth_code": bool(account.match_auth_code),
        "last_share_code": share_code or None,
        "last_share_code_status": raw.get("status") if raw else None,
        "last_share_code_played_at": played_at,
        "last_share_code_played_at_source": played_at_source,
        "last_share_code_ignored_reason": raw.get("ignored_reason") if raw else None,
        "latest_imported_played_at": latest_imported.isoformat() if latest_imported else None,
        "latest_imported_played_at_source_policy": "exact_only:steam_gc_match_time",
        "anchor_is_older_than_latest_imported": anchor_is_older,
    }


def checkpoint_steam_import_all_job(
    db: Session,
    job: ImportJob,
    phase: str,
    *,
    counters: dict[str, Any] | None = None,
    child_job_ids: list[int] | None = None,
    current_share_code: str | None = None,
    storage_budget: Any | None = None,
    event: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = _json_loads(job.result_json)
    progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else {}
    previous_counters = progress.get("counters") if isinstance(progress.get("counters"), dict) else {}
    merged_counters = {
        "processed": int(previous_counters.get("processed") or 0),
        "imported": int(previous_counters.get("imported") or 0),
        "failed": int(previous_counters.get("failed") or 0),
        "skipped": int(previous_counters.get("skipped") or 0),
        "pending": int(previous_counters.get("pending") or 0),
    }
    for key, value in (counters or {}).items():
        if key in merged_counters:
            merged_counters[key] = int(value or 0)
    child_ids = list(progress.get("child_job_ids") or [])
    for child_id in child_job_ids or []:
        if child_id not in child_ids:
            child_ids.append(child_id)
    at = _now().isoformat()
    checkpoint_event = {
        "phase": phase,
        "at": at,
    }
    if current_share_code:
        checkpoint_event["share_code"] = current_share_code
    if event:
        checkpoint_event.update(_compact_checkpoint_event(event))
    progress = {
        **progress,
        "phase": phase,
        "updated_at": at,
        "counters": merged_counters,
        "child_job_ids": child_ids,
        "current_share_code": current_share_code or progress.get("current_share_code"),
    }
    if storage_budget is not None:
        snapshot = storage_budget.snapshot() if hasattr(storage_budget, "snapshot") else storage_budget
        progress["storage_budget"] = _compact_storage_budget(snapshot)
    if extra:
        progress.update(extra)
    payload["overall_outcome"] = payload.get("overall_outcome") or STEAM_IMPORT_RUNNING
    payload["statuses"] = payload.get("statuses") or [STEAM_IMPORT_RUNNING]
    payload["progress"] = _bounded_progress(progress, checkpoint_event)
    job.result_json = json.dumps(payload, ensure_ascii=False, default=str)
    job.updated_at = _now()
    db.commit()
    db.refresh(job)


def _bounded_progress(progress: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    recent_events = list(progress.get("recent_events") or [])
    recent_events.append(event)
    progress["recent_events"] = recent_events[-STEAM_IMPORT_MAX_CHECKPOINT_EVENTS:]
    return progress


def _compact_checkpoint_event(event: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "match_id",
        "share_code",
        "child_job_id",
        "status",
        "error",
        "budget_status",
        "downloaded_bytes",
        "raw_demo_size_bytes",
        "stored_path",
        "raw_demo_path",
        "remaining_pending",
        "batch_cap_reached",
    }
    return {key: value for key, value in event.items() if key in allowed and value is not None}


def _compact_storage_budget(snapshot: dict[str, Any]) -> dict[str, Any]:
    usage = snapshot.get("usage") if isinstance(snapshot.get("usage"), dict) else {}
    filesystems = snapshot.get("filesystems") if isinstance(snapshot.get("filesystems"), dict) else {}
    upload = filesystems.get("upload") if isinstance(filesystems.get("upload"), dict) else {}
    temp = filesystems.get("temp") if isinstance(filesystems.get("temp"), dict) else {}
    settings = snapshot.get("settings") if isinstance(snapshot.get("settings"), dict) else {}
    return {
        "settings": {
            "max_demos_per_run": settings.get("max_demos_per_run"),
            "max_bytes_per_job": settings.get("max_bytes_per_job"),
            "max_single_demo_bytes": settings.get("max_single_demo_bytes"),
            "min_free_bytes": settings.get("min_free_bytes"),
            "preserve_free_bytes": settings.get("preserve_free_bytes"),
            "unknown_demo_reserve_bytes": settings.get("unknown_demo_reserve_bytes"),
        },
        "usage": {
            "downloaded_bytes": usage.get("downloaded_bytes"),
            "decompressed_bytes": usage.get("decompressed_bytes"),
            "stored_bytes": usage.get("stored_bytes"),
            "consumed_bytes": usage.get("consumed_bytes"),
            "remaining_job_bytes": usage.get("remaining_job_bytes"),
        },
        "filesystems": {
            "upload_free_bytes": upload.get("free_bytes"),
            "upload_total_bytes": upload.get("total_bytes"),
            "temp_free_bytes": temp.get("free_bytes"),
            "same_filesystem": filesystems.get("same_filesystem"),
        },
        "warnings": snapshot.get("warnings") or [],
    }


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _fail_job(db: Session, job: ImportJob, message: str, sync_outcome: str | None = None) -> dict[str, Any]:
    result = {"sync_outcome": sync_outcome} if sync_outcome else None
    fail_import_job(db, job, message, result=result)
    return _job_result(job)


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
