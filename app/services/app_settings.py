from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import AppSetting


def get_app_setting(db: Session, key: str) -> str | None:
    setting = db.get(AppSetting, key)
    return setting.value if setting else None


def set_app_setting(db: Session, key: str, value: str) -> AppSetting:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{key} is required.")
    setting = db.get(AppSetting, key)
    if setting is None:
        setting = AppSetting(key=key, value=normalized)
        db.add(setting)
    else:
        setting.value = normalized
    db.commit()
    db.refresh(setting)
    return setting
