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
    add_mission_criteria,
    create_analysis_run,
    create_coach_hypothesis,
    get_analysis_run,
    get_coach_hypothesis,
    get_coach_mission,
    list_analysis_runs,
    list_coach_hypotheses,
    list_coach_missions,
    list_mission_criteria,
    list_mission_progress_evaluations,
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
                "ready": True,
                "reason_codes": ["metric_backed"],
                "target_metric_candidates": ["opening_death_rate", "survival_rate"],
            },
        },
    )

    assert get_coach_hypothesis(db, user_id=owner.id, hypothesis_id=hypothesis.id) == hypothesis
    assert get_coach_hypothesis(db, user_id=other_owner.id, hypothesis_id=hypothesis.id) is None
    assert list_coach_hypotheses(db, user_id=owner.id, analysis_run_id=run.id) == [hypothesis]
    assert hypothesis.problem == "Opening deaths are too frequent."
    assert json.loads(hypothesis.evidence_json)[0]["metric_name"] == "opening_death_rate"
    assert json.loads(hypothesis.caveats_json) == ["Small sample."]
    assert json.loads(hypothesis.target_metric_candidates_json) == ["opening_death_rate", "survival_rate"]

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
    assert mission.focus == "Delay first contact and trade from second position."

    criteria = add_mission_criteria(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        metric_name="opening_death_rate",
        role="success",
        direction="decrease",
        baseline_value=0.31,
        target_value=0.22,
        min_sample_matches=5,
        min_sample_rounds=80,
        confidence_required=0.6,
        rule={"operator": "<=", "value": 0.22},
    )

    assert list_mission_criteria(db, user_id=owner.id, mission_id=mission.id) == [criteria]
    assert criteria.owner_steam_id == "76561198000000001"
    assert json.loads(criteria.rule_json) == {"operator": "<=", "value": 0.22}

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
        insight_card={
            "problem": "Low survival.",
            "evidence": [{"metric_name": "survival_rate", "value": 0.42}],
            "confidence": 0.7,
            "caveats": [],
            "recommended_focus": "Stay alive in opening fights.",
        },
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
        insight_card={"problem": "Low trading.", "recommended_focus": "Trade from second position."},
    )
    mission = activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Improve trades")

    with pytest.raises(ValueError):
        record_mission_progress_evaluation(
            db,
            user_id=owner.id,
            mission_id=mission.id,
            status="unknown",
        )


def _user(db, display_name: str) -> User:
    user = User(display_name=display_name)
    db.add(user)
    db.flush()
    return user
