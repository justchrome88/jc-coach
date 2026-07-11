import re

from fastapi.testclient import TestClient

from app.db.models import CoachRecommendation, MatchRecommendationEvaluation
from app.db.session import SessionLocal
from app.main import app, create_app
from app.services.ingestion.structured_import import import_rows
from app.services.metrics.recommendations import (
    ensure_default_recommendation,
    evaluate_new_matches,
    get_active_recommendation_progress,
    get_all_evaluations_by_match_id,
    get_all_recommendation_progress,
    get_evaluations_by_match_id,
    list_recommendation_history,
    recommendation_category_summary,
)


def _csrf_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def _register_owner(client: TestClient) -> None:
    page = client.get("/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": _csrf_from(page),
            "display_name": "Owner",
            "email": "owner@example.test",
            "password": "strong-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def _seed_app_recommendations(with_evaluation: bool = True) -> int:
    with SessionLocal() as session:
        import_rows(session, [_row(index) for index in range(15)], source="baseline")
        recommendation = ensure_default_recommendation(session)
        assert recommendation is not None
        if with_evaluation:
            import_rows(session, [_row(20, entry_deaths=2, early_deaths=2, kast=76, adr=82)], source="new")
            evaluate_new_matches(session)
        return recommendation.id


def _app_counts() -> tuple[int, int]:
    with SessionLocal() as session:
        return session.query(CoachRecommendation).count(), session.query(MatchRecommendationEvaluation).count()


def test_read_helpers_do_not_commit_or_create_rows(db, monkeypatch):
    import_rows(db, [_row(index) for index in range(15)], source="baseline")
    before = (
        db.query(CoachRecommendation).count(),
        db.query(MatchRecommendationEvaluation).count(),
    )

    def fail_commit():
        raise AssertionError("read helper must not commit")

    monkeypatch.setattr(db, "commit", fail_commit)

    assert get_active_recommendation_progress(db) is not None
    assert get_all_recommendation_progress(db)
    assert get_evaluations_by_match_id(db) == {}
    assert get_all_evaluations_by_match_id(db) == {}
    assert list_recommendation_history(db)
    assert recommendation_category_summary(db)

    after = (
        db.query(CoachRecommendation).count(),
        db.query(MatchRecommendationEvaluation).count(),
    )
    assert after == before


def test_get_recommendations_api_does_not_create_recommendations_or_evaluations(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "owner-token")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        before = _app_counts()
        with TestClient(create_app()) as client:
            response = client.get("/api/recommendations", headers={"Authorization": "Bearer owner-token"})
        after = _app_counts()
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json() == []
    assert after == before == (0, 0)


def test_get_recommendations_api_does_not_change_existing_counts(monkeypatch):
    recommendation_id = _seed_app_recommendations()
    before = _app_counts()
    monkeypatch.setenv("API_TOKEN", "owner-token")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            response = client.get("/api/recommendations", headers={"Authorization": "Bearer owner-token"})
        after = _app_counts()
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert recommendation_id in ids
    assert after == before


def test_coach_page_read_does_not_change_recommendation_counts():
    _seed_app_recommendations()
    before = _app_counts()

    with TestClient(app) as client:
        _register_owner(client)
        response = client.get("/coach")

    assert response.status_code == 200
    assert _app_counts() == before


def test_post_status_still_mutates_intentionally(monkeypatch):
    recommendation_id = _seed_app_recommendations(with_evaluation=False)
    monkeypatch.setenv("API_TOKEN", "owner-token")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            response = client.post(
                f"/api/recommendations/{recommendation_id}/status",
                params={"status": "completed"},
                headers={"Authorization": "Bearer owner-token"},
            )
        with SessionLocal() as session:
            status = session.get(CoachRecommendation, recommendation_id).status
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert status == "completed"


def _row(
    index: int,
    entry_deaths: int = 4,
    early_deaths: int = 4,
    kast: float = 70,
    adr: float = 80,
) -> dict:
    return {
        "played_at": f"2026-06-{index + 1:02d}",
        "map_name": "Mirage",
        "result": "win" if index % 2 == 0 else "loss",
        "rounds_for": 13,
        "rounds_against": 10,
        "kills": 20,
        "deaths": 16,
        "assists": 4,
        "adr": adr,
        "kast": kast,
        "rating": 1.05,
        "entry_kills": 2,
        "entry_deaths": entry_deaths,
        "early_deaths": early_deaths,
        "utility_damage": 70,
        "flash_assists": 1,
    }
