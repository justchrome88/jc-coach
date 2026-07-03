from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User

PBKDF2_ITERATIONS = 260_000
OWNER_POLICY = "first_active_credentialed_user_is_owner"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('ascii')}${base64.b64encode(digest).decode('ascii')}"
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(digest_b64)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def register_user(db: Session, email: str, password: str, display_name: str | None = None) -> User:
    if owner_user(db) is not None:
        raise ValueError("Регистрация закрыта: этот инстанс уже привязан к owner user.")
    normalized_email = normalize_email(email)
    if "@" not in normalized_email or "." not in normalized_email:
        raise ValueError("Введите корректный email.")
    if len(password) < 8:
        raise ValueError("Пароль должен быть не короче 8 символов.")
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise ValueError("Пользователь с таким email уже есть.")
    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        display_name=(display_name or normalized_email.split("@", 1)[0]).strip()[:120],
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    if not is_owner_user(db, user):
        return None
    user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(user)
    return user


def login_user(request: Request, user: User) -> None:
    request.session["user_id"] = user.id


def logout_user(request: Request) -> None:
    request.session.clear()


def current_user_from_session(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, user_id)
    if not user or not user.is_active:
        return None
    if not is_owner_user(db, user):
        return None
    return user


def owner_user(db: Session) -> User | None:
    return db.scalar(
        select(User)
        .where(User.is_active == 1)
        .where(User.email.is_not(None))
        .where(User.password_hash.is_not(None))
        .order_by(User.id.asc())
        .limit(1)
    )


def is_owner_user(db: Session, user: User) -> bool:
    owner = owner_user(db)
    return bool(owner and user.id == owner.id)
