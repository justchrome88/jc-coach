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
