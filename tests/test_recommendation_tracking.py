import json
from datetime import datetime

from sqlalchemy import select

from app.db.models import CoachRecommendation, Match, MatchRecommendationEvaluation
from app.services.importer import import_rows
from app.services.metric_confidence import is_exact_date_match, metric_context
from app.services.recommendation_tracking import (
    ensure_default_recommendation,
    evaluate_new_matches,
    evaluate_recommendations_for_match,
    extend_recommendation_target,
    get_active_recommendation_progress,
    get_all_recommendation_progress,
    list_recommendation_history,
    recommendation_category_summary,
    recommendation_health,
    recommendation_needs_refresh,
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
    baseline = json.loads(survival.baseline_metrics_json)
    assert baseline["confidence"]["date_window"]["exact_date_matches"] == 15
    assert baseline["confidence"]["metrics"]["early_deaths"]["level"] == "low_confidence"
    assert db.query(CoachRecommendation).count() == 4


def test_legacy_recommendation_detected_when_baseline_has_no_confidence(db):
    import_rows(db, [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=75) for index in range(15)])
    recommendation = ensure_default_recommendation(db)
    assert recommendation is not None
    recommendation.baseline_metrics_json = json.dumps({"matches_count": 15, "entry_deaths_per_match": 4})
    db.commit()

    health = recommendation_health(db, recommendation)

    assert health["needs_refresh"] is True
    assert "baseline_missing_confidence" in health["reasons"]


def test_legacy_recommendation_detected_when_baseline_ids_are_steam_history(db):
    for index in range(15):
        db.add(
            Match(
                source="steam_history",
                external_match_id=f"history-{index}",
                raw_json=json.dumps(
                    {
                        "match_date_status": "exact_match_date_available",
                        "match_date_source": "steam_gc_match_time",
                    }
                ),
            )
        )
    db.commit()
    history_ids = [match.id for match in db.scalars(select(Match).order_by(Match.id)).all()]
    recommendation = CoachRecommendation(
        title="legacy",
        description="legacy",
        category="survival",
        status="active",
        priority="high",
        target_period_matches=10,
        baseline_period_matches=15,
        start_after_match_id=max(history_ids),
        baseline_metrics_json=json.dumps({"matches_count": 15, "entry_deaths_per_match": None}),
        target_metrics_json=json.dumps({"entry_deaths_per_match": "need data"}),
        success_rules_json=json.dumps(["early deaths ниже baseline"]),
        failure_rules_json=json.dumps(["early deaths выше baseline"]),
        baseline_match_ids_json=json.dumps(history_ids),
        created_by="system",
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)

    health = recommendation_health(db, recommendation)

    assert recommendation_needs_refresh(db, recommendation) is True
    assert "baseline_contains_non_playable_matches" in health["reasons"]
    assert "rules_use_weak_metrics_as_hard_evidence" in health["reasons"]
    assert health["baseline_non_playable_ids"] == history_ids


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
    evidence = json.loads(
        db.scalar(
            select(MatchRecommendationEvaluation.evidence_json)
            .where(MatchRecommendationEvaluation.recommendation_id == survival.id)
            .order_by(MatchRecommendationEvaluation.id)
        )
    )
    assert "metric_confidence" in evidence


def test_evaluate_new_matches_skips_legacy_active_recommendation(db):
    import_rows(db, [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)])
    recommendation = ensure_default_recommendation(db)
    assert recommendation is not None
    recommendation.baseline_metrics_json = json.dumps({"matches_count": 15, "entry_deaths_per_match": 4})
    db.commit()

    import_rows(db, [_row(20, entry_deaths=2, early_deaths=2, kast=76, adr=82)], source="new")
    before = db.query(MatchRecommendationEvaluation).count()
    evaluations = evaluate_new_matches(db)

    assert evaluations == []
    assert db.query(MatchRecommendationEvaluation).count() == before


def test_evaluate_recommendations_for_match_evaluates_eligible_match_after_anchor(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    recommendation = ensure_default_recommendation(db)
    assert recommendation is not None

    match = _add_match(db, 20, source="new", entry_deaths=2, early_deaths=2, kast=76, adr=82)

    evaluations = evaluate_recommendations_for_match(db, match.id)

    survival_evaluation = next(item for item in evaluations if item.recommendation_id == recommendation.id)
    evidence = json.loads(survival_evaluation.evidence_json)
    assert survival_evaluation.match_id == match.id
    assert survival_evaluation.status == "green"
    assert "metric_confidence" in evidence


def test_evaluate_recommendations_for_match_respects_start_after_and_baseline_filters(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    recommendation = ensure_default_recommendation(db)
    assert recommendation is not None
    baseline_id = json.loads(recommendation.baseline_match_ids_json)[-1]

    baseline_evaluations = evaluate_recommendations_for_match(db, baseline_id)

    assert baseline_evaluations == []


def test_evaluate_recommendations_for_match_skips_legacy_recommendation(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    recommendation = ensure_default_recommendation(db)
    assert recommendation is not None
    recommendation.baseline_metrics_json = json.dumps({"matches_count": 15, "entry_deaths_per_match": 4})
    db.commit()

    match = _add_match(db, 20, source="new", entry_deaths=2, early_deaths=2, kast=76, adr=82)
    before = db.query(MatchRecommendationEvaluation).count()

    evaluations = evaluate_recommendations_for_match(db, match.id)

    assert all(evaluation.recommendation_id != recommendation.id for evaluation in evaluations)
    assert (
        db.query(MatchRecommendationEvaluation)
        .filter(
            MatchRecommendationEvaluation.recommendation_id == recommendation.id,
            MatchRecommendationEvaluation.match_id == match.id,
        )
        .count()
        == 0
    )
    assert db.query(MatchRecommendationEvaluation).count() >= before


def test_evaluate_recommendations_for_match_does_not_duplicate_evaluation(db):
    baseline_rows = [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)]
    import_rows(db, baseline_rows, source="baseline")
    recommendation = ensure_default_recommendation(db)
    assert recommendation is not None

    match = _add_match(db, 20, source="new", entry_deaths=2, early_deaths=2, kast=76, adr=82)

    first = evaluate_recommendations_for_match(db, match.id)
    second = evaluate_recommendations_for_match(db, match.id)

    assert any(item.recommendation_id == recommendation.id for item in first)
    assert second == []
    assert (
        db.query(MatchRecommendationEvaluation)
        .filter(
            MatchRecommendationEvaluation.recommendation_id == recommendation.id,
            MatchRecommendationEvaluation.match_id == match.id,
        )
        .count()
        == 1
    )


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


def test_legacy_progress_is_not_accepted_hard_progress(db):
    import_rows(db, [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)])
    import_rows(db, [_row(20, entry_deaths=2, early_deaths=2, kast=76, adr=82)], source="new")
    recommendation = ensure_default_recommendation(db)
    assert recommendation is not None
    recommendation.baseline_metrics_json = json.dumps({"matches_count": 15, "entry_deaths_per_match": 4})
    db.commit()

    progress = get_active_recommendation_progress(db)

    assert progress["health"]["needs_refresh"] is True
    assert progress["health"]["accepted_for_hard_progress"] is False
    assert progress["progress_score"] == 0
    assert "Legacy recommendation" in progress["summary"]


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


def test_restart_recommendation_category_creates_confidence_aware_playable_baseline(db):
    import_rows(db, [_row(index, entry_deaths=4, early_deaths=4, kast=70, adr=80) for index in range(15)])
    original = ensure_default_recommendation(db)
    assert original is not None
    original.baseline_metrics_json = json.dumps({"matches_count": 15, "entry_deaths_per_match": 4})
    db.commit()

    restarted = restart_recommendation_category(db, "survival")
    baseline = json.loads(restarted.baseline_metrics_json)
    baseline_ids = json.loads(restarted.baseline_match_ids_json)
    baseline_matches = db.scalars(select(Match).where(Match.id.in_(baseline_ids)).order_by(Match.id)).all()
    context = metric_context(baseline_matches)

    assert restarted.status == "active"
    assert recommendation_health(db, restarted)["accepted_for_hard_progress"] is True
    assert baseline["confidence"]["date_window"]["exact_date_matches"] == 15
    assert "metrics" in baseline["confidence"]
    assert all(match.source != "steam_history" for match in baseline_matches)
    assert all(is_exact_date_match(match, context=context) for match in baseline_matches)


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


def _add_match(
    db,
    index: int,
    *,
    source: str = "demo",
    entry_deaths: int,
    early_deaths: int,
    kast: float,
    adr: float,
) -> Match:
    played_at = datetime.fromisoformat(f"2026-06-{index + 1:02d}T12:00:00")
    match = Match(
        source=source,
        external_match_id=f"{source}-{index}",
        played_at=played_at,
        map_name="Mirage",
        result="win",
        rounds_for=13,
        rounds_against=10,
        kills=20,
        deaths=16,
        assists=4,
        kd=1.25,
        adr=adr,
        kast=kast,
        rating=1.05,
        entry_kills=2,
        entry_deaths=entry_deaths,
        early_deaths=early_deaths,
        utility_damage=70,
        flash_assists=1,
        raw_json=json.dumps(
            {
                "match_date_status": "exact_match_date_available",
                "match_date_source": "steam_gc_match_time",
                "played_at_source": "steam_gc_match_time",
            }
        ),
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match
