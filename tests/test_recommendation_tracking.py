from sqlalchemy import select

from app.db.models import CoachRecommendation, MatchRecommendationEvaluation
from app.services.importer import import_rows
from app.services.recommendation_tracking import (
    ensure_default_recommendation,
    evaluate_new_matches,
    extend_recommendation_target,
    get_active_recommendation_progress,
    get_all_recommendation_progress,
    list_recommendation_history,
    recommendation_category_summary,
    restart_recommendation_category,
    update_recommendation_status,
)


def test_creates_default_recommendation_with_baseline(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=75) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")

    recommendation = db.scalar(select(CoachRecommendation))
    survival = ensure_default_recommendation(db)

    assert recommendation is not None
    assert survival is not None
    assert survival.title == "Снизить первые смерти"
    assert survival.baseline_period_matches == 15
    assert survival.target_period_matches == 10
    assert db.query(CoachRecommendation).count() == 4


def test_evaluates_new_matches_green_yellow_red(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    ensure_default_recommendation(db)

    import_rows(
        db,
        [
            _row(20, entry_deaths=2, early_deaths=2, kast=76, adr=82),
            _row(21, entry_deaths=2, early_deaths=2, kast=74, adr=60),
            _row(22, entry_deaths=6, early_deaths=6, kast=62, adr=58),
        ],
        source="new",
    )
    evaluate_new_matches(db)

    survival = ensure_default_recommendation(db)
    statuses = [
        evaluation.status
        for evaluation in db.scalars(
            select(MatchRecommendationEvaluation)
            .where(MatchRecommendationEvaluation.recommendation_id == survival.id)
            .order_by(MatchRecommendationEvaluation.id)
        )
    ]

    assert statuses == ["green", "yellow", "red"]


def test_progress_summary_counts_statuses(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    import_rows(db, [_row(20, entry_deaths=2, early_deaths=2, kast=76, adr=82)], source="new")
    ensure_default_recommendation(db)
    evaluate_new_matches(db)

    progress = get_active_recommendation_progress(db)

    assert progress["completed_matches"] == 1
    assert progress["counts"]["green"] == 1
    assert progress["last_status"] == "green"


def test_all_recommendation_progress_has_categories(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    import_rows(db, [_row(20, entry_deaths=2, early_deaths=2, kast=76, adr=82)], source="new")
    ensure_default_recommendation(db)
    evaluate_new_matches(db)

    progress_items = get_all_recommendation_progress(db)
    categories = {item["recommendation"].category for item in progress_items}

    assert categories == {"aim", "grenades", "map", "survival"}
    assert all("progress_score" in item for item in progress_items)


def test_update_recommendation_status(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    recommendation = ensure_default_recommendation(db)

    updated = update_recommendation_status(db, recommendation.id, "completed")

    assert updated.status == "completed"
    assert updated.ended_at is not None


def test_extend_recommendation_target(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    recommendation = ensure_default_recommendation(db)

    updated = extend_recommendation_target(db, recommendation.id, additional_matches=5)

    assert updated.target_period_matches == 15


def test_restart_recommendation_category_archives_current_and_creates_new(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    original = ensure_default_recommendation(db)

    restarted = restart_recommendation_category(db, "survival")
    history = list_recommendation_history(db)

    assert restarted.id != original.id
    assert restarted.status == "active"
    assert any(item.id == original.id and item.status == "archived" for item in history)


def test_recommendation_category_summary(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    ensure_default_recommendation(db)
    evaluate_new_matches(db)

    summary = recommendation_category_summary(db)

    assert {item["category"] for item in summary} == {"aim", "grenades", "map", "survival"}
    assert all(item["history_count"] >= 1 for item in summary)


def _row(index: int, entry_deaths: int, early_deaths: int, kast: float, adr: float) -> dict:
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
