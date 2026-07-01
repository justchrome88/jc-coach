from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import Base
from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _register_test_user(client: TestClient) -> None:
    response = client.post(
        "/register",
        data={
            "display_name": "Test User",
            "email": f"test-{uuid4().hex}@example.test",
            "password": "test-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


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


def test_missing_match_detail_redirects_to_matches():
    with TestClient(app, follow_redirects=False) as client:
        _register_test_user(client)
        response = client.get("/matches/999999999")

    assert response.status_code == 303
    assert response.headers["location"] == "/matches"
