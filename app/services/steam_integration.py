from __future__ import annotations

import json
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


def update_match_auth_code(db: Session, steam_account_id: int, match_auth_code: str) -> SteamAccount:
    account = db.get(SteamAccount, steam_account_id)
    if account is None:
        raise ValueError("Steam account was not found.")
    code = match_auth_code.strip()
    if not code:
        raise ValueError("Game Authentication Code is required.")
    account.match_auth_code = code
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
        if collected:
            account.last_share_code = collected[-1]
        account.last_sync_at = datetime.now(UTC).replace(tzinfo=None)
        account.sync_enabled = 1
        job.status = "succeeded"
        job.finished_at = datetime.now(UTC).replace(tzinfo=None)
        job.result_json = json.dumps(
            {
                "known_code": known_code,
                "collected": len(collected),
                "inserted": inserted,
                "duplicates": duplicates,
                "last_share_code": account.last_share_code,
                "note": "Steam share codes were saved. Demo download/parsing is the next worker layer.",
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
    return steam_id, None


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
