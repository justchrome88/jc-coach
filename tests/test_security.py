import re

from fastapi.testclient import TestClient

from app.config import Settings, _assert_strong_session_secret, get_settings
from app.main import app, create_app


def _csrf_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def test_production_like_env_rejects_default_session_secret():
    settings = Settings(app_env="production", session_secret_key="change-me-before-public-release")

    try:
        _assert_strong_session_secret(settings)
    except RuntimeError as exc:
        assert "SESSION_SECRET_KEY" in str(exc)
    else:
        raise AssertionError("weak production session secret should fail")


def test_local_env_allows_default_session_secret():
    settings = Settings(app_env="local", session_secret_key="change-me-before-public-release")

    _assert_strong_session_secret(settings)


def test_login_rate_limit_blocks_repeated_attempts():
    with TestClient(app) as client:
        page = client.get("/login")
        csrf = _csrf_from(page)
        statuses = [
            client.post(
                "/login",
                data={"csrf_token": csrf, "email": "missing@example.test", "password": "wrong-password"},
            ).status_code
            for _ in range(6)
        ]

    assert statuses[:5] == [400, 400, 400, 400, 400]
    assert statuses[5] == 429


def test_bearer_api_token_allows_protected_api_without_csrf(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-api-token")
    get_settings.cache_clear()

    try:
        with TestClient(create_app()) as client:
            response = client.post(
                "/api/reports/generate",
                headers={"Authorization": "Bearer test-api-token"},
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_invalid_bearer_api_token_is_rejected(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-api-token")
    get_settings.cache_clear()

    try:
        with TestClient(create_app()) as client:
            response = client.get(
                "/api/matches",
                headers={"Authorization": "Bearer wrong-token"},
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 401
