import json
from datetime import datetime

import pytest

from app.db.models import (
    AnalysisRun,
    CoachHypothesis,
    CoachMission,
    MissionCriteria,
    MissionProgressEvaluation,
    User,
)
from app.services.mission_domain import (
    activate_coach_mission,
    activate_draft_coach_mission,
    add_mission_criteria,
    cancel_coach_mission,
    create_analysis_run,
    create_coach_hypothesis,
    create_draft_coach_mission,
    get_analysis_run,
    get_coach_hypothesis,
    get_coach_mission,
    list_active_coach_missions,
    list_analysis_runs,
    list_coach_hypotheses,
    list_coach_missions,
    list_mission_criteria,
    list_mission_progress_evaluations,
    pause_coach_mission,
    record_mission_progress_evaluation,
    update_coach_mission_status,
)


def test_mission_domain_tables_are_registered():
    assert AnalysisRun.__tablename__ == "analysis_runs"
    assert CoachHypothesis.__tablename__ == "coach_hypotheses"
    assert CoachMission.__tablename__ == "coach_missions"
    assert MissionCriteria.__tablename__ == "mission_criteria"
    assert MissionProgressEvaluation.__tablename__ == "mission_progress_evaluations"


def test_create_read_list_update_mission_domain_flow(db):
    owner = _user(db, "owner")
    other_owner = _user(db, "other")

    run = create_analysis_run(
        db,
        user_id=owner.id,
        owner_steam_id="76561198000000001",
        window_start=datetime(2026, 7, 1),
        window_end=datetime(2026, 7, 8),
        source="coach_api",
        selected_metric_snapshot_ids=[101, 102],
        analysis_scope={
            "mode": "personal",
            "owner_user_id": owner.id,
            "window": "last_7_days",
            "source": "metric_snapshots",
        },
        source_payload={"report_id": 77},
    )

    assert get_analysis_run(db, user_id=owner.id, analysis_run_id=run.id) == run
    assert get_analysis_run(db, user_id=other_owner.id, analysis_run_id=run.id) is None
    assert list_analysis_runs(db, user_id=owner.id) == [run]
    assert json.loads(run.selected_metric_snapshot_ids_json) == [101, 102]
    assert json.loads(run.analysis_scope_json)["owner_user_id"] == owner.id

    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card={
            "id": "card-survival-1",
            "problem": "Opening deaths are too frequent.",
            "evidence": [{"metric_name": "opening_death_rate", "value": 0.31}],
            "confidence": 0.74,
            "caveats": ["Small sample."],
            "recommended_focus": "Delay first contact and trade from second position.",
            "mission_readiness": {
                "can_become_mission": True,
                "target_metric_candidate": "opening_death_rate",
                "baseline_value": 0.31,
                "confidence_eligibility": {
                    "level": "medium",
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                },
                "missing_requirements": [],
                "blocking_reason_codes": [],
            },
        },
    )

    assert get_coach_hypothesis(db, user_id=owner.id, hypothesis_id=hypothesis.id) == hypothesis
    assert get_coach_hypothesis(db, user_id=other_owner.id, hypothesis_id=hypothesis.id) is None
    assert list_coach_hypotheses(db, user_id=owner.id, analysis_run_id=run.id) == [hypothesis]
    assert hypothesis.problem == "Opening deaths are too frequent."
    assert json.loads(hypothesis.evidence_json)[0]["metric_name"] == "opening_death_rate"
    assert json.loads(hypothesis.caveats_json) == ["Small sample."]
    assert json.loads(hypothesis.target_metric_candidates_json) == []

    mission = activate_coach_mission(
        db,
        user_id=owner.id,
        hypothesis_id=hypothesis.id,
        title="Reduce opening deaths",
        source_payload={"activated_from": "test"},
    )

    assert get_coach_mission(db, user_id=owner.id, mission_id=mission.id) == mission
    assert get_coach_mission(db, user_id=other_owner.id, mission_id=mission.id) is None
    assert list_coach_missions(db, user_id=owner.id, status="active") == [mission]
    assert list_active_coach_missions(db, user_id=owner.id) == [mission]
    assert mission.focus == "Delay first contact and trade from second position."
    assert json.loads(mission.source_payload_json)["baseline_source"] == "coach_hypothesis_mission_readiness"

    criteria_rows = list_mission_criteria(db, user_id=owner.id, mission_id=mission.id)
    assert [(row.metric_name, row.role, row.direction) for row in criteria_rows] == [
        ("opening_death_rate", "primary", "lower_is_better"),
        ("opening_death_rate", "guardrail", "stay_below"),
    ]
    assert criteria_rows[0].baseline_value == 0.31
    assert criteria_rows[0].target_value == 0.26

    manual_criteria = add_mission_criteria(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        metric_name="survival_rate",
        role="secondary",
        direction="higher_is_better",
        baseline_value=0.31,
        target_value=0.36,
        min_sample_matches=5,
        min_sample_rounds=80,
        confidence_required=0.6,
        rule={"operator": ">=", "value": 0.36},
    )

    assert list_mission_criteria(db, user_id=owner.id, mission_id=mission.id)[-1] == manual_criteria
    assert manual_criteria.owner_steam_id == "76561198000000001"
    assert json.loads(manual_criteria.rule_json) == {"operator": ">=", "value": 0.36}

    evaluation = record_mission_progress_evaluation(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        status="improving",
        evaluation_window_start=datetime(2026, 7, 9),
        evaluation_window_end=datetime(2026, 7, 16),
        result={"opening_death_rate": 0.24},
        confidence=0.67,
        caveats=["Still below sample target."],
    )

    assert list_mission_progress_evaluations(db, user_id=owner.id, mission_id=mission.id) == [evaluation]
    assert evaluation.status == "improving"
    assert json.loads(evaluation.result_json) == {"opening_death_rate": 0.24}

    ended_at = datetime(2026, 7, 17)
    updated = update_coach_mission_status(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        status="completed",
        ended_at=ended_at,
    )

    assert updated.status == "completed"
    assert updated.ended_at == ended_at


def test_cross_owner_mutations_are_denied(db):
    owner = _user(db, "owner")
    other_owner = _user(db, "other")
    run = create_analysis_run(db, user_id=owner.id, analysis_scope={"owner_user_id": owner.id})
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card=_ready_opening_death_card(),
    )
    mission = activate_coach_mission(
        db,
        user_id=owner.id,
        hypothesis_id=hypothesis.id,
        title="Survive openings",
    )

    with pytest.raises(PermissionError):
        create_coach_hypothesis(
            db,
            user_id=other_owner.id,
            analysis_run_id=run.id,
            insight_card={"problem": "Cross-owner", "recommended_focus": "Denied"},
        )
    with pytest.raises(PermissionError):
        activate_coach_mission(db, user_id=other_owner.id, hypothesis_id=hypothesis.id, title="Denied")
    with pytest.raises(PermissionError):
        add_mission_criteria(
            db,
            user_id=other_owner.id,
            mission_id=mission.id,
            metric_name="survival_rate",
            role="success",
            direction="increase",
        )
    with pytest.raises(PermissionError):
        record_mission_progress_evaluation(
            db,
            user_id=other_owner.id,
            mission_id=mission.id,
            status="unchanged",
        )
    with pytest.raises(PermissionError):
        update_coach_mission_status(db, user_id=other_owner.id, mission_id=mission.id, status="cancelled")


def test_progress_evaluation_rejects_unknown_status(db):
    owner = _user(db, "owner")
    run = create_analysis_run(db, user_id=owner.id)
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card=_ready_opening_death_card(),
    )
    mission = activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Improve trades")

    with pytest.raises(ValueError):
        record_mission_progress_evaluation(
            db,
            user_id=owner.id,
            mission_id=mission.id,
            status="unknown",
        )


def test_active_mission_requires_ready_metric_confidence_and_persists_explicit_criteria(db):
    owner = _user(db, "owner")
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000002")
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card={
            "problem": "Utility damage can become a measurable mission.",
            "evidence": [{"metric_id": "utility_damage", "value": 94, "metric_confidence": "medium"}],
            "confidence": "medium",
            "caveats": [],
            "recommended_focus": "Review damage-producing grenade rounds.",
            "mission_readiness": {
                "can_become_mission": True,
                "target_metric_candidate": "utility_damage",
                "baseline_value": 94,
                "confidence_eligibility": {
                    "level": "medium",
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                },
                "missing_requirements": [],
                "blocking_reason_codes": [],
                "criteria": [
                    {
                        "metric_name": "utility_damage",
                        "role": "primary",
                        "direction": "higher_is_better",
                        "baseline_value": 94,
                        "target_value": 110,
                        "min_sample_matches": 3,
                    },
                    {
                        "metric_name": "he_damage",
                        "role": "secondary",
                        "direction": "higher_is_better",
                        "baseline_value": 20,
                        "target_value": 25,
                    },
                    {
                        "metric_name": "utility_damage",
                        "role": "guardrail",
                        "direction": "stay_above",
                        "baseline_value": 94,
                        "target_value": 80,
                    },
                ],
            },
        },
    )

    draft = create_draft_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Utility damage")
    assert draft.status == "draft"
    assert {row.role for row in list_mission_criteria(db, user_id=owner.id, mission_id=draft.id)} == {
        "primary",
        "secondary",
        "guardrail",
    }

    activated = activate_draft_coach_mission(db, user_id=owner.id, mission_id=draft.id)
    criteria = list_mission_criteria(db, user_id=owner.id, mission_id=activated.id)

    assert activated.status == "active"
    assert [(row.metric_name, row.role, row.direction, row.baseline_value, row.target_value) for row in criteria] == [
        ("utility_damage", "primary", "higher_is_better", 94, 110),
        ("he_damage", "secondary", "higher_is_better", 20, 25),
        ("utility_damage", "guardrail", "stay_above", 94, 80),
    ]
    assert criteria[0].min_sample_matches == 3


def test_activation_blocks_low_or_mission_ineligible_metrics(db):
    owner = _user(db, "owner")
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000003")
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card={
            "problem": "Low-confidence utility context is not a hard mission.",
            "evidence": [{"metric_id": "utility_damage", "value": 90, "metric_confidence": "low"}],
            "confidence": "low",
            "caveats": ["Utility events are incomplete."],
            "recommended_focus": "Collect stronger utility evidence first.",
            "mission_readiness": {
                "can_become_mission": False,
                "target_metric_candidate": "utility_damage",
                "baseline_value": 90,
                "confidence_eligibility": {
                    "level": "low",
                    "usable_for_missions": False,
                    "hard_recommendation_eligible": False,
                },
                "missing_requirements": ["mission_eligible_confidence"],
                "blocking_reason_codes": ["low_or_unavailable_confidence"],
            },
        },
    )

    draft = create_draft_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Draft only")
    assert draft.status == "draft"

    with pytest.raises(ValueError, match="low_or_unavailable_confidence"):
        activate_draft_coach_mission(db, user_id=owner.id, mission_id=draft.id)
    with pytest.raises(ValueError, match="low_or_unavailable_confidence"):
        activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Denied active")


def test_pause_and_cancel_mission_status_helpers(db):
    owner = _user(db, "owner")
    run = create_analysis_run(db, user_id=owner.id)
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card=_ready_opening_death_card(),
    )
    mission = activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Opening deaths")

    assert pause_coach_mission(db, user_id=owner.id, mission_id=mission.id).status == "paused"
    cancelled = cancel_coach_mission(db, user_id=owner.id, mission_id=mission.id)
    assert cancelled.status == "cancelled"
    assert cancelled.ended_at is not None


def _user(db, display_name: str) -> User:
    user = User(display_name=display_name)
    db.add(user)
    db.flush()
    return user


def _ready_opening_death_card() -> dict:
    return {
        "problem": "Opening deaths are too frequent.",
        "evidence": [{"metric_id": "opening_death_rate", "value": 0.31, "metric_confidence": "medium"}],
        "confidence": "medium",
        "caveats": [],
        "recommended_focus": "Delay first contact.",
        "mission_readiness": {
            "can_become_mission": True,
            "target_metric_candidate": "opening_death_rate",
            "baseline_value": 0.31,
            "confidence_eligibility": {
                "level": "medium",
                "usable_for_missions": True,
                "hard_recommendation_eligible": True,
            },
            "missing_requirements": [],
            "blocking_reason_codes": [],
        },
    }
