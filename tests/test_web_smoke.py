from fastapi.testclient import TestClient

from app.db.session import Base
from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_renders():
    with TestClient(app) as client:
        Base.metadata.create_all(bind=client.app.state._state.get("engine")) if False else None
        response = client.get("/")

    assert response.status_code == 200
    assert "Общая статистика" in response.text


def test_coach_page_renders():
    with TestClient(app) as client:
        response = client.get("/coach")

    assert response.status_code == 200
    assert "Тренер" in response.text


def test_matches_page_supports_filters_and_sorting():
    with TestClient(app) as client:
        response = client.get("/matches?sort=adr&direction=desc&per_page=25")

    assert response.status_code == 200
    assert "Матчи" in response.text
    assert "Найдено" in response.text


def test_missing_match_detail_redirects_to_matches():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/matches/999999999")

    assert response.status_code == 303
    assert response.headers["location"] == "/matches"
