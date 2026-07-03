from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ImportJob, Match, SteamAccount, User
from app.services.app_settings import get_app_setting

STEAM_OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
STEAM_OPENID_CLAIM_PREFIX = "https://steamcommunity.com/openid/id/"
STEAM_MATCH_HISTORY_ENDPOINT = "https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1"
STEAM_SYNC_COOLDOWN_SECONDS = 300
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
) -> ImportJob:
    job = ImportJob(
        provider="steam",
        job_type=job_type,
        status="queued",
        steam_account_id=steam_account_id,
        requested_payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


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
        .where(ImportJob.status.in_(("queued", "running")))
        .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
    )


def queue_steam_import_all(db: Session) -> ImportJob:
    running = current_steam_import_all_job(db)
    if running:
        return running
    return create_steam_import_job(
        db,
        None,
        "steam_import_all",
        {"reason": "manual_pull_all", "created_from": "settings_imports"},
    )


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
    )


def sync_match_history_job(db: Session, job_id: int) -> dict[str, Any]:
    job = db.get(ImportJob, job_id)
    if job is None:
        raise ValueError("Import job was not found.")
    if job.provider != "steam" or job.job_type != "match_history_sync":
        raise ValueError("Only steam match_history_sync jobs can be processed here.")
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

    job.status = "running"
    job.started_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()

    try:
        payload = _json_loads(job.requested_payload_json)
        known_code = str(payload.get("known_share_code") or account.last_share_code or "0")
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
        account.last_sync_at = datetime.now(UTC).replace(tzinfo=None)
        account.sync_enabled = 1
        job.status = "succeeded"
        job.finished_at = datetime.now(UTC).replace(tzinfo=None)
        job.result_json = json.dumps(
            {
                "known_code": known_code,
                "collected": len(collected),
                "collected_share_codes": collected,
                "inserted": inserted,
                "duplicates": duplicates,
                "last_share_code": account.last_share_code,
                "note": (
                    "Steam share codes were saved. The account's explicit latest share code was not advanced "
                    "from GetNextMatchSharingCode results."
                ),
            },
            ensure_ascii=False,
        )
        db.commit()
        db.refresh(job)
        return _job_result(job)
    except Exception as exc:
        return _fail_job(db, job, str(exc))


def process_queued_steam_jobs(db: Session, limit: int = 5) -> list[dict[str, Any]]:
    jobs = db.scalars(
        select(ImportJob)
        .where(ImportJob.provider == "steam")
        .where(ImportJob.job_type == "match_history_sync")
        .where(ImportJob.status == "queued")
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
    if job.status == "running":
        return {"id": job.id, "status": job.status, "result": None, "error": None}
    if job.status == "succeeded":
        return {"id": job.id, "status": job.status, "result": _json_loads(job.result_json), "error": None}

    job.status = "running"
    job.started_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()

    try:
        settings = get_settings()
        accounts = list_steam_accounts(db)
        sync_results = []
        fresh_share_codes: list[str] = []
        latest_played_at = _latest_imported_match_played_at(db)
        for account in accounts:
            if not account.match_auth_code or not account.last_share_code:
                sync_results.append(
                    {
                        "steam_account_id": account.id,
                        "status": "skipped",
                        "error": "Steam account is missing match token or authentication code.",
                    }
                )
                continue
            saved_share_code = account.last_share_code.strip()
            try:
                decode_match_share_code(saved_share_code)
            except ValueError as exc:
                sync_results.append(
                    {
                        "steam_account_id": account.id,
                        "status": "skipped",
                        "error": str(exc),
                    }
                )
                continue
            _store_steam_share_code_match(db, account, saved_share_code)
            fresh_share_codes.append(saved_share_code)
            sync_job = queue_match_history_sync(db, account.id)
            sync_result = sync_match_history_job(db, sync_job.id)
            sync_results.append(sync_result)
            result_payload = sync_result.get("result") or {}
            fresh_share_codes.extend(result_payload.get("collected_share_codes") or [])
        fresh_share_codes = list(dict.fromkeys(fresh_share_codes))

        demo_status = mark_steam_history_demo_download_status(db, share_codes=fresh_share_codes)
        from app.services.steam_demo_downloader import download_pending_steam_demos

        demo_download = download_pending_steam_demos(
            db,
            limit=max(1, min(int(settings.steam_sync_max_codes), 50)),
            share_codes=fresh_share_codes,
            min_played_at=latest_played_at,
        )
        result = {
            "accounts": len(accounts),
            "sync_jobs": sync_results,
            "demo_status": demo_status,
            "demo_download": demo_download,
            "latest_imported_played_at_before_job": latest_played_at.isoformat() if latest_played_at else None,
            "note": (
                "Synced share codes through Steam Web API, then used Steam GC match_time as the authoritative "
                "date before downloading demos. Candidates older than the latest imported match are skipped."
            ),
        }
        job.status = "succeeded"
        job.finished_at = datetime.now(UTC).replace(tzinfo=None)
        job.result_json = json.dumps(result, ensure_ascii=False, default=str)
        db.commit()
        db.refresh(job)
        return {"id": job.id, "status": job.status, "result": result, "error": None}
    except Exception as exc:
        return _fail_job(db, job, str(exc))


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
    was_inserted = _store_steam_share_code_match(db, account, share_code)
    account.last_share_code = share_code
    account.last_sync_at = datetime.now(UTC).replace(tzinfo=None)
    account.sync_enabled = 1
    db.commit()

    demo_status = mark_steam_history_demo_download_status(db, share_codes=[share_code])
    from app.services.steam_demo_downloader import download_pending_steam_demos

    demo_download = download_pending_steam_demos(db, limit=1, share_codes=[share_code])
    return {
        "share_code": share_code,
        "inserted": was_inserted,
        "demo_status": demo_status,
        "demo_download": demo_download,
    }


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
    job.status = "failed"
    job.error_message = message
    job.finished_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(job)
    return job


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
    latest_imported = _latest_imported_match_played_at(db)
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
        "anchor_is_older_than_latest_imported": anchor_is_older,
    }


def _fail_job(db: Session, job: ImportJob, message: str) -> dict[str, Any]:
    job.status = "failed"
    job.error_message = message
    job.finished_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(job)
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
