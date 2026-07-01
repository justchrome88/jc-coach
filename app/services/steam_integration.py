from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ImportJob, SteamAccount, User

STEAM_OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
STEAM_OPENID_CLAIM_PREFIX = "https://steamcommunity.com/openid/id/"


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


def link_steam_account(db: Session, steam_id: str, persona_name: str | None = None) -> SteamAccount:
    account = db.scalar(select(SteamAccount).where(SteamAccount.steam_id == steam_id))
    if account:
        if persona_name:
            account.persona_name = persona_name
        db.commit()
        db.refresh(account)
        return account
    user = User(display_name=persona_name or f"Steam {steam_id[-4:]}")
    db.add(user)
    db.flush()
    account = SteamAccount(user_id=user.id, steam_id=steam_id, persona_name=persona_name, sync_enabled=0)
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
