import re
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.db.models import User
from app.db.session import Base, SessionLocal
from app.main import app


def _csrf_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _register_test_user(client: TestClient) -> None:
    page = client.get("/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": _csrf_from(page),
            "display_name": "Test User",
            "email": f"test-{uuid4().hex}@example.test",
            "password": "test-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


def _app_user_count() -> int:
    with SessionLocal() as session:
        return session.query(User).count()


def test_register_route_rejects_test_smoke_email_outside_test_env(monkeypatch):
    monkeypatch.setattr(
        "app.services.auth.get_settings",
        lambda: Settings(app_env="local", database_url="sqlite:///:memory:"),
    )

    with TestClient(app) as client:
        page = client.get("/register")
        response = client.post(
            "/register",
            data={
                "csrf_token": _csrf_from(page),
                "display_name": "Smoke",
                "email": "smoke-runtime@example.test",
                "password": "test-password",
            },
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert "Refusing to register test/smoke email outside APP_ENV=test" in response.text
    assert _app_user_count() == 0


def test_landing_renders_for_anonymous_user():
    with TestClient(app) as client:
        Base.metadata.create_all(bind=client.app.state._state.get("engine")) if False else None
        response = client.get("/")

    assert response.status_code == 200
    assert "AI-тренер" in response.text
    assert "Войти" in response.text


def test_dashboard_renders_after_registration():
    with TestClient(app) as client:
        _register_test_user(client)
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Общая статистика" in response.text


def test_protected_page_redirects_anonymous_user_to_login():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/dashboard")

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_api_requires_authentication_for_anonymous_user():
    with TestClient(app) as client:
        response = client.get("/api/matches")

    assert response.status_code == 401


def test_api_allows_authenticated_session_user():
    with TestClient(app) as client:
        _register_test_user(client)
        response = client.get("/api/matches")

    assert response.status_code == 200


def test_dangerous_api_job_anonymous_blocked():
    with TestClient(app) as client:
        response = client.post("/api/steam/import/all")

    assert response.status_code == 401


def test_session_api_post_requires_csrf():
    with TestClient(app) as client:
        _register_test_user(client)
        response = client.post("/api/reports/generate")

    assert response.status_code == 403


def test_csrf_missing_rejected_for_web_post():
    with TestClient(app) as client:
        response = client.post(
            "/login",
            data={"email": "missing@example.test", "password": "wrong-password"},
        )

    assert response.status_code == 403


def test_stats_page_renders_with_filters():
    with TestClient(app) as client:
        _register_test_user(client)
        response = client.get("/stats?range_type=last&matches_count=15")

    assert response.status_code == 200
    assert "Общая статистика" in response.text
    assert "Количество игр" in response.text


def test_language_switch_sets_locale_cookie():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/language/en", headers={"referer": "/stats"})

    assert response.status_code == 303
    assert response.headers["location"] == "/stats"
    assert "locale=en" in response.headers["set-cookie"]


def test_coach_page_renders():
    with TestClient(app) as client:
        _register_test_user(client)
        response = client.get("/coach")

    assert response.status_code == 200
    assert "Тренер" in response.text


def test_matches_page_supports_filters_and_sorting():
    with TestClient(app) as client:
        _register_test_user(client)
        response = client.get("/matches?sort=adr&direction=desc&per_page=25")

    assert response.status_code == 200
    assert "Матчи" in response.text
    assert "Найдено" in response.text


def test_storage_settings_page_renders():
    with TestClient(app) as client:
        _register_test_user(client)
        response = client.get("/settings/storage")

    assert response.status_code == 200
    assert "Хранилище demo" in response.text
    assert "Целевая схема" in response.text


def test_missing_match_detail_redirects_to_matches():
    with TestClient(app, follow_redirects=False) as client:
        _register_test_user(client)
        response = client.get("/matches/999999999")

    assert response.status_code == 303
    assert response.headers["location"] == "/matches"
