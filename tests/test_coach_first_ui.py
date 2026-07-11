import json
import re

from fastapi.testclient import TestClient

from app.db.models import CoachRecommendation, MatchRecommendationEvaluation
from app.db.session import SessionLocal
from app.main import app
from app.services.coach.ai import save_ai_coach_result
from app.services.ingestion.structured_import import import_rows
from app.services.metrics.recommendations import ensure_default_recommendation, evaluate_new_matches


def _csrf_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def _register_owner(client: TestClient, email: str = "owner@example.test") -> None:
    page = client.get("/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": _csrf_from(page),
            "display_name": "Owner",
            "email": email,
            "password": "strong-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def _seed_recommendation(with_evaluation: bool = True) -> None:
    with SessionLocal() as session:
        import_rows(session, [_row(index) for index in range(15)], source="baseline")
        recommendation = ensure_default_recommendation(session)
        assert recommendation is not None
        if with_evaluation:
            import_rows(session, [_row(20, entry_deaths=2, early_deaths=1, kast=76, adr=84)], source="new")
            evaluate_new_matches(session)


def _counts() -> tuple[int, int]:
    with SessionLocal() as session:
        return session.query(CoachRecommendation).count(), session.query(MatchRecommendationEvaluation).count()


def test_coach_page_renders_for_authenticated_owner_with_empty_state():
    with TestClient(app) as client:
        _register_owner(client)
        response = client.get("/coach")

    assert response.status_code == 200
    assert "Current tracked recommendation" in response.text
    assert "Нет отслеживаемой рекомендации" in response.text
    assert "AI не запускается при открытии страницы" in response.text


def test_coach_page_displays_current_tracked_recommendation_without_verified_top_problem_claim():
    _seed_recommendation()

    with TestClient(app) as client:
        _register_owner(client)
        response = client.get("/coach")

    assert response.status_code == 200
    assert "Current tracked recommendation" in response.text
    assert "Снизить первые смерти" in response.text
    assert "Это текущая отслеживаемая цель, не verified top problem." in response.text
    assert "verified top problem</h" not in response.text.lower()
    assert "Следующий матч" in response.text
    assert "Last evaluation" in response.text


def test_coach_page_labels_legacy_recommendation_as_needing_refresh():
    _seed_recommendation(with_evaluation=False)
    with SessionLocal() as session:
        recommendation = session.query(CoachRecommendation).filter_by(category="survival").one()
        recommendation.baseline_metrics_json = json.dumps({"matches_count": 15, "entry_deaths_per_match": 4})
        session.commit()

    with TestClient(app) as client:
        _register_owner(client)
        response = client.get("/coach")

    assert response.status_code == 200
    assert "needs_refresh" in response.text
    assert (
        "Legacy recommendation: refresh this category before treating progress as accepted coach evidence."
        in response.text
    )
    assert "Historical/unverified evaluations are shown for audit only." in response.text


def test_coach_page_surfaces_metric_truth_warning_labels_for_weak_metrics():
    _seed_recommendation(with_evaluation=False)

    with TestClient(app) as client:
        _register_owner(client)
        response = client.get("/coach")

    assert response.status_code == 200
    assert "Metric Truth warnings" in response.text
    assert "early_deaths" in response.text
    assert "approximate" in response.text
    assert "trade_kills" in response.text
    assert "suppressed" in response.text
    assert "traded_deaths" in response.text
    assert "unavailable" in response.text


def test_coach_page_surfaces_ai_validation_fallback_status():
    with SessionLocal() as session:
        import_rows(session, [_row(index) for index in range(2)], source="ai")
        save_ai_coach_result(session, "Confident free-form advice about crosshair placement.", source_ref="mock")

    with TestClient(app) as client:
        _register_owner(client)
        response = client.get("/coach")

    assert response.status_code == 200
    assert "Fallback AI report" in response.text
    assert "Исходный AI output отклонён validator" in response.text


def test_get_coach_does_not_mutate_recommendation_or_evaluation_rows():
    _seed_recommendation()
    before = _counts()

    with TestClient(app) as client:
        _register_owner(client)
        response = client.get("/coach")

    assert response.status_code == 200
    assert _counts() == before


def test_get_coach_does_not_run_live_ai_steam_parser_or_import_jobs(monkeypatch):
    _seed_recommendation(with_evaluation=False)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("page render must not run external jobs")

    monkeypatch.setattr("app.web.routes.generate_ai_coach_with_provider", fail_if_called)
    monkeypatch.setattr("app.web.routes.prepare_ai_coach_handoff", fail_if_called)
    monkeypatch.setattr("app.web.routes.run_steam_import_all_job", fail_if_called)
    monkeypatch.setattr("app.web.routes.process_queued_steam_jobs", fail_if_called)
    monkeypatch.setattr("app.web.routes.import_demo_file", fail_if_called)

    with TestClient(app) as client:
        _register_owner(client)
        response = client.get("/coach")

    assert response.status_code == 200


def test_coach_page_displays_valid_ai_validation_status():
    with SessionLocal() as session:
        import_rows(session, [_row(index) for index in range(2)], source="ai-valid")
        save_ai_coach_result(session, json.dumps(_valid_ai_output()), source_ref="mock")

    with TestClient(app) as client:
        _register_owner(client)
        response = client.get("/coach")

    assert response.status_code == 200
    assert "Valid structured AI report" in response.text
    assert "Структура и Metric Truth usage прошли validator." in response.text


def _valid_ai_output() -> dict:
    return {
        "summary": "Survival is the current focus.",
        "diagnoses": [
            {
                "category": "survival",
                "severity": "medium",
                "claim": "Entry deaths are too frequent.",
                "evidence_metric_ids": ["entry_deaths"],
                "confidence": "medium",
                "caveats": ["Opening duel detection depends on parser/source order."],
            }
        ],
        "recommendations": [
            {
                "category": "survival",
                "action": "Play first 20 seconds for trade support.",
                "rationale": "Entry deaths are the reliable hard signal.",
                "target_metric_ids": ["entry_deaths"],
                "confidence": "medium",
                "caveats": ["Track over the next imported matches."],
            }
        ],
        "warnings": ["Do not infer crosshair placement from current data."],
        "evidence": [
            {
                "metric_id": "entry_deaths",
                "value": 3,
                "metric_confidence": "medium",
                "caveats": ["Source/order dependent."],
            }
        ],
        "insight_cards": [
            {
                "problem": "Opening duel survival is the current evidence-backed focus.",
                "evidence": [
                    {
                        "metric_id": "entry_deaths",
                        "value": 3,
                        "metric_confidence": "medium",
                        "description": "Entry deaths are elevated in the current sample.",
                    }
                ],
                "confidence": "medium",
                "caveats": ["Opening duel detection depends on parser/source order."],
                "recommended_focus": "Review first-contact deaths before changing broader coach goals.",
            }
        ],
        "confidence": "medium",
    }


def _row(index: int, entry_deaths: int = 4, early_deaths: int = 4, kast: float = 70, adr: float = 80) -> dict:
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
