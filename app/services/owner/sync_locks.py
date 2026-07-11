"""Owner-sync lock persistence and recovery."""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    AppSetting,
)
from app.services.owner.sync_support import (
    _iso,
    _json_mapping,
    _optional_int,
    _optional_text,
    _parse_datetime,
    _utcnow,
)
from app.services.owner.sync_types import (
    OWNER_COACH_SYNC_LOCK_TTL,
    OWNER_COACH_SYNC_OPERATION,
    _OwnerSyncLock,
)


def _acquire_owner_sync_lock(db: Session, *, owner_user_id: int) -> _OwnerSyncLock | None:
    now = _utcnow()
    key = _lock_key(owner_user_id)
    lock = _new_lock(key=key, now=now)
    db.add(AppSetting(key=key, value=lock.value))
    try:
        db.commit()
        return lock
    except IntegrityError:
        db.rollback()

    existing = db.get(AppSetting, key)
    if existing is None:
        return None
    existing_lock = _lock_from_value(key, existing.value)
    if existing_lock is not None and existing_lock.expires_at > now:
        return None
    stale_value = existing.value
    recovered = _new_lock(key=key, now=now, recovered_stale=True)
    changed = db.execute(
        update(AppSetting)
        .where(AppSetting.key == key)
        .where(AppSetting.value == stale_value)
        .values(value=recovered.value)
    )
    db.commit()
    return recovered if changed.rowcount == 1 else None

def _refresh_owner_sync_lock(db: Session, lock: _OwnerSyncLock) -> bool:
    now = _utcnow()
    refreshed = _new_lock(key=lock.key, now=now, token=lock.token, recovered_stale=lock.recovered_stale)
    changed = db.execute(
        update(AppSetting)
        .where(AppSetting.key == lock.key)
        .where(AppSetting.value == lock.value)
        .values(value=refreshed.value)
    )
    db.commit()
    if changed.rowcount != 1:
        return False
    lock.value = refreshed.value
    lock.expires_at = refreshed.expires_at
    return True

def _release_owner_sync_lock(db: Session, lock: _OwnerSyncLock) -> bool:
    changed = db.execute(delete(AppSetting).where(AppSetting.key == lock.key).where(AppSetting.value == lock.value))
    db.commit()
    return changed.rowcount == 1

def _read_active_lock(db: Session, *, owner_user_id: int) -> _OwnerSyncLock | None:
    setting = db.get(AppSetting, _lock_key(owner_user_id))
    if setting is None:
        return None
    lock = _lock_from_value(setting.key, setting.value)
    if lock is None or lock.expires_at <= _utcnow():
        return None
    return lock

def _new_lock(
    *,
    key: str,
    now: datetime,
    token: str | None = None,
    recovered_stale: bool = False,
) -> _OwnerSyncLock:
    token = token or secrets.token_urlsafe(18)
    expires_at = now + OWNER_COACH_SYNC_LOCK_TTL
    value = json.dumps(
        {
            "operation": OWNER_COACH_SYNC_OPERATION,
            "token": token,
            "acquired_at": _iso(now),
            "expires_at": _iso(expires_at),
        },
        sort_keys=True,
    )
    return _OwnerSyncLock(
        key=key,
        token=token,
        value=value,
        acquired_at=now,
        expires_at=expires_at,
        recovered_stale=recovered_stale,
    )

def _lock_from_value(key: str, value: str) -> _OwnerSyncLock | None:
    payload = _json_mapping(value)
    token = _optional_text(payload.get("token"))
    acquired_at = _parse_datetime(payload.get("acquired_at"))
    expires_at = _parse_datetime(payload.get("expires_at"))
    if not token or acquired_at is None or expires_at is None:
        return None
    return _OwnerSyncLock(
        key=key,
        token=token,
        value=value,
        acquired_at=acquired_at,
        expires_at=expires_at,
    )

def _public_lock(lock: _OwnerSyncLock, *, status: str) -> dict[str, Any]:
    return {
        "status": status,
        "operation": OWNER_COACH_SYNC_OPERATION,
        "owner_user_id": _optional_int(lock.key.rsplit(":", 1)[-1]),
        "acquired_at": _iso(lock.acquired_at),
        "expires_at": _iso(lock.expires_at),
        "recovered_stale": lock.recovered_stale,
        "released": False,
    }

def _lock_key(owner_user_id: int) -> str:
    return f"lock:{OWNER_COACH_SYNC_OPERATION}:{owner_user_id}"

__all__ = (
)
