from __future__ import annotations

import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs

from fastapi import Request

CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER = "x-csrf-token"

logger = logging.getLogger("app.security")


def csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_FORM_FIELD)
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_FORM_FIELD] = token
    return token


async def request_csrf_token(request: Request) -> str | None:
    header_token = request.headers.get(CSRF_HEADER)
    if header_token:
        return header_token
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        body = (await request.body()).decode("utf-8", errors="replace")
        values = parse_qs(body)
        token_values = values.get(CSRF_FORM_FIELD)
        return token_values[0] if token_values else None
    if "multipart/form-data" in content_type:
        body = await request.body()
        marker = f'name="{CSRF_FORM_FIELD}"'.encode()
        index = body.find(marker)
        if index == -1:
            return None
        value_start = body.find(b"\r\n\r\n", index)
        if value_start == -1:
            return None
        value_start += 4
        value_end = body.find(b"\r\n", value_start)
        if value_end == -1:
            return None
        return body[value_start:value_end].decode("utf-8", errors="replace")
    return None


async def has_valid_csrf(request: Request) -> bool:
    expected = request.session.get(CSRF_FORM_FIELD)
    provided = await request_csrf_token(request)
    return isinstance(expected, str) and isinstance(provided, str) and hmac.compare_digest(expected, provided)


def has_valid_api_token(request: Request, configured_token: str | None) -> bool:
    if not configured_token:
        return False
    header = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix):
        return False
    provided = header.removeprefix(prefix).strip()
    return bool(provided) and hmac.compare_digest(provided, configured_token)


@dataclass
class InMemoryRateLimiter:
    window_seconds: int = 60
    _hits: dict[str, list[float]] = field(default_factory=dict)

    def allow(self, key: str, limit: int, now: float | None = None) -> bool:
        timestamp = time.monotonic() if now is None else now
        cutoff = timestamp - self.window_seconds
        hits = [item for item in self._hits.get(key, []) if item >= cutoff]
        if len(hits) >= limit:
            self._hits[key] = hits
            return False
        hits.append(timestamp)
        self._hits[key] = hits
        return True

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = InMemoryRateLimiter()


def rate_limit_bucket(path: str, method: str) -> tuple[str, int] | None:
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    if path == "/login":
        return ("login", 5)
    if path == "/upload" or path == "/upload/server-demo" or path.startswith("/api/import/"):
        return ("import_upload", 20)
    if path.startswith("/api/coach/ai") or path.startswith("/coach/ai"):
        return ("ai", 10)
    if path.startswith("/api/steam/") or path.startswith("/settings/imports"):
        return ("steam_import", 20)
    if path.startswith("/api/reports") or path == "/report/generate":
        return ("reports", 20)
    if path.startswith("/api/recommendations") or path.startswith("/coach/recommendations"):
        return ("recommendations", 30)
    if path.startswith("/api/storage") or path.startswith("/settings/storage"):
        return ("storage", 20)
    return None


def rate_limit_key(request: Request, bucket: str) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_host = forwarded_for.split(",", 1)[0].strip() if forwarded_for else None
    if not client_host and request.client:
        client_host = request.client.host
    user_id = request.session.get("user_id")
    actor = f"user:{user_id}" if user_id else f"ip:{client_host or 'unknown'}"
    return f"{bucket}:{actor}"


def log_security_event(action: str, request: Request, **fields: Any) -> None:
    user_id = request.session.get("user_id")
    logger.info(
        "security_event action=%s method=%s path=%s user_id=%s fields=%s",
        action,
        request.method,
        request.url.path,
        user_id,
        fields,
    )
