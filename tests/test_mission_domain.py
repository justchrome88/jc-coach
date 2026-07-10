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
from app.services.coach_insights import coach_insights_with_mission_readiness_from_snapshots
from app.services.mission_domain import (
    MISSION_PAYLOAD_SCHEMA_VERSION,
    activate_coach_mission,
    activate_draft_coach_mission,
    add_mission_criteria,
    cancel_coach_mission,
    create_analysis_run,
    create_coach_hypothesis,
    create_draft_coach_mission,
    evaluate_mission_progress,
    get_analysis_run,
    get_coach_hypothesis,
    get_coach_mission,
    list_active_coach_missions,
    list_analysis_runs,
    list_coach_hypotheses,
    list_coach_missions,
    list_mission_criteria,
    list_mission_progress_evaluations,
    mission_payload_from_insight_card,
    pause_coach_mission,
    record_mission_progress_evaluation,
    serialize_coach_mission,
    serialize_mission_payload,
    serialize_mission_progress_evaluation,
    update_coach_mission_status,
    validate_mission_payload,
)


def test_mission_domain_tables_are_registered():
    assert AnalysisRun.__tablename__ == "analysis_runs"
    assert CoachHypothesis.__tablename__ == "coach_hypotheses"
    assert CoachMission.__tablename__ == "coach_missions"
    assert MissionCriteria.__tablename__ == "mission_criteria"
    assert MissionProgressEvaluation.__tablename__ == "mission_progress_evaluations"


def test_mission_payload_schema_accepts_required_measurable_fields():
    payload = {
        "title": "Reduce opening deaths",
        "goal": "Move opening_death_rate from 0.310 toward 0.260 using supported owner metric snapshots.",
        "rules": [
            "Delay first contact.",
            "Count progress only when opening_death_rate is present in owner-scoped metric snapshots.",
        ],
        "duration": {"unit": "matches", "min_matches": 3, "max_matches": 5},
        "success_metric": {
            "metric_name": "opening_death_rate",
            "direction": "lower_is_better",
            "baseline_value": 0.31,
            "target_value": 0.26,
        },
        "failure_condition": {
            "metric_name": "opening_death_rate",
            "direction": "stay_below",
            "threshold_value": 0.31,
            "reason": "Do not regress from the activation baseline.",
        },
        "linked_insight": {"source_insight_card_id": "card-opening-1"},
    }

    assert validate_mission_payload(payload) == ()

    serialized = serialize_mission_payload(payload)
    assert serialized["schema_version"] == MISSION_PAYLOAD_SCHEMA_VERSION
    assert serialized["success_metric"]["target_value"] == 0.26
    assert serialized["linked_insight"]["source_insight_card_id"] == "card-opening-1"


def test_mission_payload_schema_rejects_vague_unmeasurable_payload():
    payload = {
        "title": "Play better",
        "goal": "Improve generally.",
        "rules": [],
        "duration": {"unit": "matches"},
        "success_metric": {"metric_name": "opening_death_rate", "direction": "lower_is_better"},
        "failure_condition": {"metric_name": "opening_death_rate", "direction": "stay_below"},
    }

    issues = validate_mission_payload(payload)
    codes = {issue.code for issue in issues}

    assert "missing_mission_rules" in codes
    assert "invalid_mission_duration_window" in codes
    assert "missing_mission_success_target" in codes
    assert "missing_mission_failure_threshold" in codes
    assert serialize_mission_payload(payload) == {}


def test_survival_opening_insight_generates_actionable_opening_mission(db):
    owner = _user(db, "owner")
    card = coach_insights_with_mission_readiness_from_snapshots(
        [
            _e02_survival_snapshot(
                metrics={
                    "rounds": 12,
                    "opening_deaths": 4,
                    "opening_death_rate": 0.333,
                    "survived_rounds": 6,
                    "survival_rate": 0.5,
                },
                confidence={
                    "opening_death_rate": {
                        "level": "medium",
                        "usable_for_insights": True,
                        "usable_for_missions": True,
                        "hard_recommendation_eligible": True,
                    },
                    "survival_rate": {
                        "level": "high",
                        "usable_for_insights": True,
                        "usable_for_missions": True,
                        "hard_recommendation_eligible": True,
                    },
                },
            )
        ]
    )[0]

    payload = mission_payload_from_insight_card(card)

    assert payload is not None
    assert validate_mission_payload(payload) == ()
    assert payload["title"] == "Reduce opening deaths"
    assert payload["goal"] == (
        "Reduce opening_death_rate from 0.333 to 0.283 over upcoming owner matches "
        "using supported metric snapshots."
    )
    assert payload["duration"]["min_sample_rounds"] == 12
    assert payload["success_metric"] == {
        "metric_name": "opening_death_rate",
        "direction": "lower_is_better",
        "baseline_value": 0.333,
        "target_value": 0.283,
        "min_sample_matches": None,
        "min_sample_rounds": 12,
        "confidence_required": 0.6,
    }
    assert payload["failure_condition"] == {
        "metric_name": "opening_death_rate",
        "direction": "stay_below",
        "threshold_value": 0.333,
        "reason": (
            "Mission fails if opening_death_rate rises above the activation baseline or cannot be evaluated "
            "with supported metrics."
        ),
    }
    assert payload["rules"][:3] == [
        "For each upcoming match, avoid voluntary first contact in the opening phase unless trade support is set.",
        "Success is measured only by lowering opening_death_rate in owner-scoped metric snapshots.",
        (
            "Failure is triggered if opening_death_rate is above the activation baseline or cannot be "
            "evaluated with supported metrics."
        ),
    ]

    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000001")
    hypothesis = create_coach_hypothesis(db, user_id=owner.id, analysis_run_id=run.id, insight_card=card)
    mission = activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title=payload["title"])
    criteria = list_mission_criteria(db, user_id=owner.id, mission_id=mission.id)

    assert [(row.metric_name, row.role, row.direction, row.min_sample_rounds) for row in criteria] == [
        ("opening_death_rate", "primary", "lower_is_better", 12),
        ("survival_rate", "secondary", "higher_is_better", 12),
        ("opening_death_rate", "guardrail", "stay_below", None),
    ]
    assert json.loads(criteria[0].rule_json)["source"] == "survival_opening_mission_template"


def test_survival_opening_insight_generates_survival_mission_payload():
    card = coach_insights_with_mission_readiness_from_snapshots(
        [
            _e02_survival_snapshot(
                metrics={
                    "rounds": 10,
                    "opening_deaths": 1,
                    "opening_death_rate": 0.1,
                    "survived_rounds": 5,
                    "survival_rate": 0.5,
                },
                confidence={
                    "survival_rate": {
                        "level": "high",
                        "usable_for_insights": True,
                        "usable_for_missions": True,
                        "hard_recommendation_eligible": True,
                    },
                },
            )
        ]
    )[0]

    payload = mission_payload_from_insight_card(card)

    assert payload is not None
    assert validate_mission_payload(payload) == ()
    assert payload["title"] == "Improve round survival"
    assert payload["goal"] == (
        "Raise survival_rate from 0.500 to 0.550 over upcoming owner matches using supported metric snapshots."
    )
    assert payload["success_metric"]["metric_name"] == "survival_rate"
    assert payload["success_metric"]["direction"] == "higher_is_better"
    assert payload["success_metric"]["target_value"] == 0.55
    assert payload["failure_condition"] == {
        "metric_name": "survival_rate",
        "direction": "stay_above",
        "threshold_value": 0.5,
        "reason": (
            "Mission fails if survival_rate drops below the activation baseline or cannot be evaluated "
            "with supported metrics."
        ),
    }
    assert payload["rules"][:3] == [
        "For each upcoming match, prioritize staying alive through early fights before taking isolated space.",
        "Success is measured only by raising survival_rate in owner-scoped metric snapshots.",
        (
            "Failure is triggered if survival_rate drops below the activation baseline or cannot be "
            "evaluated with supported metrics."
        ),
    ]


def test_bad_fight_trade_insight_generates_trade_discipline_mission(db):
    owner = _user(db, "owner")
    card = coach_insights_with_mission_readiness_from_snapshots(
        [
            _e02_survival_snapshot(
                metrics={
                    "rounds": 10,
                    "opening_deaths": 3,
                    "opening_death_rate": 0.3,
                    "untraded_deaths": 3,
                    "traded_deaths": 1,
                    "trade_status_known_deaths": 4,
                    "untraded_death_rate": 0.75,
                    "traded_death_rate": 0.25,
                },
                confidence={
                    "opening_death_rate": {
                        "level": "high",
                        "usable_for_insights": True,
                        "usable_for_missions": True,
                        "hard_recommendation_eligible": True,
                    },
                    "untraded_death_rate": {
                        "level": "high",
                        "usable_for_insights": True,
                        "usable_for_missions": True,
                        "hard_recommendation_eligible": True,
                    },
                },
            )
        ]
    )[0]

    payload = mission_payload_from_insight_card(card)

    assert payload is not None
    assert validate_mission_payload(payload) == ()
    assert payload["title"] == "Reduce untraded deaths"
    assert payload["goal"] == (
        "Reduce untraded_death_rate from 0.750 to 0.700 over upcoming owner matches "
        "using supported trade-status metric snapshots."
    )
    assert payload["duration"]["min_sample_rounds"] == 10
    assert payload["success_metric"] == {
        "metric_name": "untraded_death_rate",
        "direction": "lower_is_better",
        "baseline_value": 0.75,
        "target_value": 0.7,
        "min_sample_matches": None,
        "min_sample_rounds": 10,
        "confidence_required": 0.9,
    }
    assert payload["failure_condition"] == {
        "metric_name": "untraded_death_rate",
        "direction": "stay_below",
        "threshold_value": 0.75,
        "reason": (
            "Mission fails if untraded_death_rate rises above the activation baseline or cannot be evaluated "
            "with supported trade-status metrics."
        ),
    }
    assert payload["rules"][:3] == [
        "For each upcoming match, avoid taking isolated fights unless a teammate can trade the death.",
        "Success is measured only by lowering untraded_death_rate in owner-scoped metric snapshots.",
        (
            "Failure is triggered if untraded_death_rate is above the activation baseline or cannot be "
            "evaluated with supported trade-status metrics."
        ),
    ]

    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000001")
    hypothesis = create_coach_hypothesis(db, user_id=owner.id, analysis_run_id=run.id, insight_card=card)
    mission = activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title=payload["title"])
    criteria = list_mission_criteria(db, user_id=owner.id, mission_id=mission.id)

    assert [(row.metric_name, row.role, row.direction, row.min_sample_rounds) for row in criteria] == [
        ("untraded_death_rate", "primary", "lower_is_better", 10),
        ("opening_death_rate", "secondary", "lower_is_better", 10),
        ("untraded_death_rate", "guardrail", "stay_below", None),
    ]
    assert json.loads(criteria[0].rule_json)["source"] == "bad_fight_trade_mission_template"


def test_trade_discipline_mission_progress_uses_trade_and_opening_metrics(db):
    owner = _user(db, "owner")
    card = coach_insights_with_mission_readiness_from_snapshots(
        [
            _e02_survival_snapshot(
                metrics={
                    "rounds": 10,
                    "opening_deaths": 3,
                    "opening_death_rate": 0.3,
                    "untraded_deaths": 3,
                    "traded_deaths": 1,
                    "trade_status_known_deaths": 4,
                    "untraded_death_rate": 0.75,
                    "traded_death_rate": 0.25,
                },
                confidence={
                    "opening_death_rate": {
                        "level": "high",
                        "usable_for_insights": True,
                        "usable_for_missions": True,
                        "hard_recommendation_eligible": True,
                    },
                    "untraded_death_rate": {
                        "level": "high",
                        "usable_for_insights": True,
                        "usable_for_missions": True,
                        "hard_recommendation_eligible": True,
                    },
                },
            )
        ]
    )[0]
    mission = _active_mission_from_card(db, owner=owner, card=card, title="Reduce untraded deaths")

    evaluation = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            {
                "id": owner.id * 1000 + 10,
                "user_id": owner.id,
                "owner_steam_id": mission.owner_steam_id,
                "metrics": {
                    "untraded_death_rate": 0.65,
                    "opening_death_rate": 0.22,
                },
                "confidence": "high",
                "sample_matches": 3,
                "sample_rounds": 30,
            }
        ],
    )

    result = json.loads(evaluation.result_json)
    assert evaluation.status == "improving"
    assert result["target_met"] is True
    assert result["component_metrics"]["untraded_death_rate"]["target_reached"] is True
    assert result["component_metrics"]["opening_death_rate"]["target_reached"] is True
    assert result["snapshot_comparison"]["success_metric"] == {
        "metric_name": "untraded_death_rate",
        "direction": "lower_is_better",
        "target_value": 0.7,
        "source": "mission_payload.success_metric",
    }


def test_ambiguous_trade_evidence_does_not_generate_mission_payload():
    card = coach_insights_with_mission_readiness_from_snapshots(
        [
            _e02_survival_snapshot(
                metrics={
                    "rounds": 10,
                    "ambiguous_traded_deaths": 2,
                    "trade_status_known_deaths": 0,
                },
                confidence={
                    "traded_death_rate": {
                        "level": "low",
                        "usable_for_insights": False,
                        "usable_for_missions": False,
                        "hard_recommendation_eligible": False,
                    },
                    "untraded_death_rate": {
                        "level": "low",
                        "usable_for_insights": False,
                        "usable_for_missions": False,
                        "hard_recommendation_eligible": False,
                    },
                },
            )
        ]
    )[0]

    assert card["problem"] == "Trade behavior cannot be judged confidently from this match snapshot."
    assert card["confidence"] == "low"
    assert card["evidence"][0]["metric_id"] == "ambiguous_traded_deaths"
    assert card["mission_readiness"]["can_become_mission"] is False
    assert "low_or_unavailable_confidence" in card["mission_readiness"]["blocking_reason_codes"]
    assert mission_payload_from_insight_card(card) is None


def test_weak_survival_opening_insight_does_not_produce_active_mission(db):
    owner = _user(db, "owner")
    weak_card = {
        "problem": "Opening deaths are present but weakly supported.",
        "evidence": [{"metric_id": "opening_death_rate", "value": 0.31, "metric_confidence": "low"}],
        "confidence": "low",
        "caveats": ["Opening death evidence is too weak for a mission."],
        "recommended_focus": "Collect stronger opening-death evidence first.",
        "mission_readiness": {
            "can_become_mission": False,
            "target_metric_candidate": "opening_death_rate",
            "baseline_value": 0.31,
            "confidence_eligibility": {
                "level": "low",
                "usable_for_missions": False,
                "hard_recommendation_eligible": False,
            },
            "missing_requirements": ["mission_eligible_confidence"],
            "blocking_reason_codes": ["low_or_unavailable_confidence"],
        },
    }
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000001")
    hypothesis = create_coach_hypothesis(db, user_id=owner.id, analysis_run_id=run.id, insight_card=weak_card)

    assert mission_payload_from_insight_card(weak_card) is None

    draft = create_draft_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Weak opening")
    assert draft.status == "draft"
    with pytest.raises(ValueError, match="low_or_unavailable_confidence"):
        activate_draft_coach_mission(db, user_id=owner.id, mission_id=draft.id)


def test_inconsistent_weak_survival_readiness_does_not_generate_mission_payload(db):
    owner = _user(db, "owner")
    weak_card = {
        "problem": "Opening deaths are present but not mission-ready.",
        "evidence": [{"metric_id": "opening_death_rate", "value": 0.31, "metric_confidence": "low"}],
        "confidence": "low",
        "caveats": ["Opening death evidence is too weak for a mission."],
        "recommended_focus": "Collect stronger opening-death evidence first.",
        "mission_readiness": {
            "can_become_mission": True,
            "target_metric_candidate": "opening_death_rate",
            "baseline_value": 0.31,
            "confidence_eligibility": {
                "level": "low",
                "usable_for_missions": False,
                "hard_recommendation_eligible": False,
            },
            "missing_requirements": ["mission_eligible_confidence"],
            "blocking_reason_codes": ["low_or_unavailable_confidence"],
        },
    }
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000001")
    hypothesis = create_coach_hypothesis(db, user_id=owner.id, analysis_run_id=run.id, insight_card=weak_card)

    assert mission_payload_from_insight_card(weak_card) is None
    assert serialize_coach_mission(
        create_draft_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Weak opening")
    )["mission_payload"] == {}
    with pytest.raises(ValueError, match="low_or_unavailable_confidence"):
        activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Weak opening")


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
    mission_source_payload = json.loads(mission.source_payload_json)
    mission_payload = mission_source_payload["mission_payload"]
    assert mission_source_payload["baseline_source"] == "coach_hypothesis_mission_readiness"
    assert validate_mission_payload(mission_payload) == ()
    assert mission_payload["title"] == "Reduce opening deaths"
    assert mission_payload["success_metric"] == {
        "metric_name": "opening_death_rate",
        "direction": "lower_is_better",
        "baseline_value": 0.31,
        "target_value": 0.26,
        "min_sample_matches": None,
        "min_sample_rounds": None,
        "confidence_required": 0.6,
    }
    assert mission_payload["failure_condition"]["threshold_value"] == 0.31
    assert mission_payload["linked_insight"] == {
        "source_hypothesis_id": hypothesis.id,
        "source_insight_card_id": "card-survival-1",
        "analysis_run_id": run.id,
        "source": "coach_hypothesis",
    }
    serialized_mission = serialize_coach_mission(mission)
    assert serialized_mission["mission_payload"] == mission_payload

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


@pytest.mark.parametrize(
    ("future_value", "expected_status"),
    [
        (0.24, "improving"),
        (0.31, "unchanged"),
        (0.38, "regressing"),
    ],
)
def test_evaluate_opening_mission_progress_outcomes(db, future_value, expected_status):
    owner = _user(db, "owner")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Survive openings",
    )

    evaluation = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_window_start=datetime(2026, 7, 9),
        evaluation_window_end=datetime(2026, 7, 16),
        evaluation_metric_snapshots=[
            _snapshot(
                owner,
                owner_steam_id=mission.owner_steam_id,
                metrics={"opening_death_rate": future_value},
                sample_matches=3,
                sample_rounds=72,
            )
        ],
    )

    result = json.loads(evaluation.result_json)
    assert evaluation.status == expected_status
    assert result["evaluation_window_json"]["sample_matches"] == 3
    assert result["components"][0]["metric_name"] == "opening_death_rate"
    assert result["components"][0]["outcome"] == expected_status
    assert evaluation.owner_steam_id == mission.owner_steam_id


def test_evaluate_mission_progress_links_before_after_snapshots_and_explains_focus(db):
    owner = _user(db, "owner")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Survive openings",
    )

    evaluation = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        baseline_metric_snapshots=[
            _snapshot(
                owner,
                owner_steam_id=mission.owner_steam_id,
                metrics={"opening_death_rate": 0.31},
                sample_matches=3,
                sample_rounds=70,
            )
        ],
        evaluation_metric_snapshots=[
            _snapshot(
                owner,
                owner_steam_id=mission.owner_steam_id,
                metrics={"opening_death_rate": 0.24},
                sample_matches=3,
                sample_rounds=72,
            )
        ],
    )

    result = json.loads(evaluation.result_json)
    summary = serialize_mission_progress_evaluation(evaluation)
    comparison = result["snapshot_comparison"]
    assert evaluation.status == "improving"
    assert comparison["success_metric"] == {
        "metric_name": "opening_death_rate",
        "direction": "lower_is_better",
        "target_value": 0.26,
        "source": "mission_payload.success_metric",
    }
    assert comparison["before"]["metric_snapshot_ids"] == [owner.id * 1000 + 70]
    assert comparison["after"]["metric_snapshot_ids"] == [owner.id * 1000 + 72]
    assert comparison["before"]["value"] == 0.31
    assert comparison["after"]["value"] == 0.24
    assert comparison["delta"] == pytest.approx(-0.07)
    assert result["components"][0]["baseline_source"] == "metric_snapshots"
    assert "Improving on the assigned focus" in result["progress_explanation"]
    assert summary["snapshot_comparison"] == comparison
    assert summary["progress_explanation"] == result["progress_explanation"]


def test_evaluate_mission_progress_distinguishes_missing_data(db):
    owner = _user(db, "owner")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Survive openings",
    )

    evaluation = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _snapshot(
                owner,
                owner_steam_id=mission.owner_steam_id,
                metrics={"survival_rate": 0.55},
                sample_matches=3,
                sample_rounds=72,
            )
        ],
    )

    result = json.loads(evaluation.result_json)
    assert evaluation.status == "insufficient_data"
    assert result["components"][0]["outcome"] == "insufficient_data"
    assert "missing_metric" in result["components"][0]["reason_codes"]
    assert json.loads(evaluation.caveats_json) == ["opening_death_rate:missing_metric"]


def test_evaluate_mission_progress_requires_success_metric_in_before_snapshot(db):
    owner = _user(db, "owner")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Survive openings",
    )

    evaluation = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        baseline_metric_snapshots=[
            _snapshot(
                owner,
                owner_steam_id=mission.owner_steam_id,
                metrics={"survival_rate": 0.55},
                sample_matches=3,
                sample_rounds=70,
            )
        ],
        evaluation_metric_snapshots=[
            _snapshot(
                owner,
                owner_steam_id=mission.owner_steam_id,
                metrics={"opening_death_rate": 0.24},
                sample_matches=3,
                sample_rounds=72,
            )
        ],
    )

    result = json.loads(evaluation.result_json)
    assert evaluation.status == "insufficient_data"
    assert result["components"][0]["reason_codes"] == ["missing_baseline_metric"]
    assert result["snapshot_comparison"]["before"]["metric_snapshot_ids"] == [owner.id * 1000 + 70]
    assert result["snapshot_comparison"]["after"]["metric_snapshot_ids"] == [owner.id * 1000 + 72]
    assert result["snapshot_comparison"]["before"]["value"] is None
    assert json.loads(evaluation.caveats_json) == ["opening_death_rate:missing_baseline_metric"]
    assert "Insufficient data to judge the assigned focus" in result["progress_explanation"]


def test_evaluate_mission_progress_distinguishes_not_following(db):
    owner = _user(db, "owner")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_utility_card_with_follow_rule(),
        title="Utility discipline",
    )

    evaluation = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _snapshot(
                owner,
                owner_steam_id=mission.owner_steam_id,
                metrics={
                    "utility_damage": 98,
                    "utility_uses_per_match": 1,
                },
                sample_matches=4,
                sample_rounds=96,
            )
        ],
    )

    result = json.loads(evaluation.result_json)
    assert evaluation.status == "not_following"
    assert result["components"][0]["outcome"] == "not_following"
    assert "not_following" in result["components"][0]["reason_codes"]
    assert json.loads(evaluation.caveats_json) == ["utility_damage:not_following"]


def test_evaluate_mission_progress_guardrail_blocks_harmful_success(db):
    owner = _user(db, "owner")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_survival_with_adr_guardrail_card(),
        title="Survive with damage",
    )

    evaluation = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _snapshot(
                owner,
                owner_steam_id=mission.owner_steam_id,
                metrics={
                    "survival_rate": 0.58,
                    "adr": 58,
                },
                sample_matches=4,
                sample_rounds=96,
            )
        ],
    )

    result = json.loads(evaluation.result_json)
    assert evaluation.status == "regressing"
    assert result["target_met"] is False
    assert result["component_metrics"]["survival_rate"]["outcome"] == "improving"
    assert result["component_metrics"]["adr"]["outcome"] == "regressing"


def test_evaluate_mission_progress_rejects_cross_owner_snapshot(db):
    owner = _user(db, "owner")
    other_owner = _user(db, "other")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Survive openings",
    )

    with pytest.raises(PermissionError):
        evaluate_mission_progress(
            db,
            user_id=owner.id,
            mission_id=mission.id,
            evaluation_metric_snapshots=[
                _snapshot(
                    other_owner,
                    owner_steam_id="76561198000000999",
                    metrics={"opening_death_rate": 0.24},
                    sample_matches=3,
                    sample_rounds=72,
                )
            ],
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


def test_no_data_insight_card_does_not_produce_mission_payload_or_active_mission(db):
    owner = _user(db, "owner")
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000004")
    no_data_card = {
        "problem": "No validated coach insight is available yet.",
        "evidence": [],
        "confidence": "low",
        "caveats": ["No supported evidence was available for this card."],
        "recommended_focus": "Use the current accepted recommendation until more evidence exists.",
        "mission_readiness": {
            "can_become_mission": False,
            "target_metric_candidate": None,
            "baseline_value": None,
            "confidence_eligibility": {
                "level": "low",
                "usable_for_missions": False,
                "hard_recommendation_eligible": False,
            },
            "missing_requirements": ["target_metric", "baseline_value", "mission_eligible_confidence"],
            "blocking_reason_codes": ["missing_target_metric", "missing_baseline_value"],
        },
    }
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card=no_data_card,
    )

    assert mission_payload_from_insight_card(no_data_card) is None

    with pytest.raises(ValueError, match="missing_target_metric,missing_baseline_value"):
        activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="No-data mission")
    assert list_coach_missions(db, user_id=owner.id) == []


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


def _ready_utility_card_with_follow_rule() -> dict:
    return {
        "problem": "Utility damage needs repeatable usage.",
        "evidence": [{"metric_id": "utility_damage", "value": 94, "metric_confidence": "medium"}],
        "confidence": "medium",
        "caveats": [],
        "recommended_focus": "Use planned utility before taking space.",
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
                    "rule": {
                        "follow_rule": {
                            "metric_name": "utility_uses_per_match",
                            "operator": ">=",
                            "value": 3,
                        }
                    },
                }
            ],
        },
    }


def _ready_survival_with_adr_guardrail_card() -> dict:
    return {
        "problem": "Survival is low without enough damage impact.",
        "evidence": [{"metric_id": "survival_rate", "value": 0.47, "metric_confidence": "medium"}],
        "confidence": "medium",
        "caveats": [],
        "recommended_focus": "Survive opening fights without disappearing from damage trades.",
        "mission_readiness": {
            "can_become_mission": True,
            "target_metric_candidate": "survival_rate",
            "baseline_value": 0.47,
            "confidence_eligibility": {
                "level": "medium",
                "usable_for_missions": True,
                "hard_recommendation_eligible": True,
            },
            "missing_requirements": [],
            "blocking_reason_codes": [],
            "criteria": [
                {
                    "metric_name": "survival_rate",
                    "role": "primary",
                    "direction": "higher_is_better",
                    "baseline_value": 0.47,
                    "target_value": 0.52,
                    "min_sample_matches": 3,
                },
                {
                    "metric_name": "adr",
                    "role": "guardrail",
                    "direction": "not_drop_more_than",
                    "baseline_value": 78,
                    "target_value": 68,
                    "min_sample_matches": 3,
                    "rule": {"max_drop": 10},
                },
            ],
        },
    }


def _active_mission_from_card(db, *, owner: User, card: dict, title: str) -> CoachMission:
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000001")
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card=card,
    )
    return activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title=title)


def _snapshot(
    owner: User,
    *,
    owner_steam_id: str | None,
    metrics: dict,
    sample_matches: int,
    sample_rounds: int,
) -> dict:
    return {
        "id": owner.id * 1000 + sample_rounds,
        "user_id": owner.id,
        "owner_steam_id": owner_steam_id,
        "metrics": metrics,
        "confidence": "medium",
        "sample_matches": sample_matches,
        "sample_rounds": sample_rounds,
    }


def _e02_survival_snapshot(
    *,
    metrics: dict,
    confidence: dict,
    match_id: int = 42,
) -> dict:
    return {
        "id": 100 + match_id,
        "match_id": match_id,
        "player_key": "steam:76561198000000001",
        "source": "core_combat_metrics",
        "source_event_set_id": "fixture:e02",
        "metrics": metrics,
        "confidence_baseline": {"source": "core-combat-metrics-v1", "metrics": confidence},
        "caveats": [],
        "metadata": {"schema_version": "core-combat-metrics-v1"},
    }
