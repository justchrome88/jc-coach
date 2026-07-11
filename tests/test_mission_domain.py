import json
from datetime import datetime

import pytest

from app.db.models import (
    AnalysisRun,
    CoachHypothesis,
    CoachMission,
    Match,
    MetricSnapshot,
    MissionCriteria,
    MissionProgressEvaluation,
    User,
)
from app.services.coach.insights import coach_insights_with_mission_readiness_from_snapshots
from app.services.mission_domain import (
    MISSION_PAYLOAD_SCHEMA_VERSION,
    activate_coach_mission,
    activate_draft_coach_mission,
    active_mission_context_for_owner,
    add_mission_criteria,
    cancel_coach_mission,
    complete_coach_mission,
    create_analysis_run,
    create_coach_hypothesis,
    create_draft_coach_mission,
    evaluate_mission_progress,
    expire_coach_mission,
    fail_coach_mission,
    generate_rolling_mission_candidates,
    get_analysis_run,
    get_coach_hypothesis,
    get_coach_mission,
    list_active_coach_missions,
    list_analysis_runs,
    list_coach_hypotheses,
    list_coach_missions,
    list_mission_criteria,
    list_mission_progress_evaluations,
    mission_domain_key,
    mission_payload_from_insight_card,
    pause_coach_mission,
    persist_rolling_mission_candidates,
    record_mission_progress_evaluation,
    resume_coach_mission,
    serialize_active_mission_summary,
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
                    "rounds_played": 12,
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
                    "rounds_played": 10,
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
                    "rounds_played": 10,
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
                    "rounds_played": 10,
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
                    "match_id": 10,
                    "user_id": owner.id,
                    "owner_steam_id": mission.owner_steam_id,
                    "source": "coach_metric_performance",
                    "metrics": {
                        "untraded_death_rate": 0.65,
                        "opening_death_rate": 0.22,
                    },
                    "confidence_baseline": {
                        "metrics": {
                            "untraded_death_rate": {"level": "high"},
                            "opening_death_rate": {"level": "high"},
                        }
                    },
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
                    "rounds_played": 10,
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
    assert mission_source_payload["mission_domain_key"] == "bad_fight_selection"
    assert mission_source_payload["problem_key"] == "bad_fight_selection"
    assert mission_domain_key(mission) == "bad_fight_selection"
    assert mission_source_payload["activation_metadata"]["primary_metric"] == "opening_death_rate"
    assert mission_source_payload["activation_metadata"]["baseline_values"]["opening_death_rate"] == 0.31
    assert mission_source_payload["activation_metadata"]["target_values"]["opening_death_rate"] == 0.26
    assert mission_source_payload["activation_metadata"]["confidence_required"] == 0.6
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
    assert result["evaluation_window_json"]["sample_matches"] == 1
    assert result["components"][0]["metric_name"] == "opening_death_rate"
    assert result["components"][0]["outcome"] == expected_status
    assert evaluation.owner_steam_id == mission.owner_steam_id


@pytest.mark.parametrize(
    ("status", "current_value", "delta", "counted", "feedback_phrase"),
    [
        ("improving", 0.24, -0.07, True, "continue the active mission focus"),
        ("unchanged", 0.31, 0.0, False, "continue the active mission focus"),
        ("regressing", 0.39, 0.08, False, "explain the failed metric"),
        ("insufficient_data", None, None, False, "do not make a hard progress or failure claim"),
        ("not_following", 0.32, 0.01, False, "what rule was not followed"),
    ],
)
def test_active_mission_summary_serializes_progress_states_with_caveats(
    db,
    status,
    current_value,
    delta,
    counted,
    feedback_phrase,
):
    owner = _user(db, f"owner-{status}")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Survive openings",
    )
    reason_codes = [] if status in {"improving", "unchanged", "regressing"} else [status]
    evaluation = record_mission_progress_evaluation(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        status=status,
        result={
            "components": [
                {
                    "metric_name": "opening_death_rate",
                    "role": "primary",
                    "direction": "lower_is_better",
                    "baseline_value": 0.31,
                    "observed_value": current_value,
                    "delta": delta,
                    "target_value": 0.26,
                    "outcome": status,
                    "target_reached": counted,
                    "reason_codes": reason_codes,
                    "sample_matches": 3,
                    "sample_rounds": 72,
                    "confidence": 0.6,
                }
            ],
            "snapshot_comparison": {
                "metric_name": "opening_death_rate",
                "before": {"metric_snapshot_ids": [101], "value": 0.31},
                "after": {"metric_snapshot_ids": [202], "value": current_value},
                "delta": delta,
            },
            "source_metric_snapshot_ids": [202],
            "target_met": counted,
            "progress_explanation": f"{status}: opening_death_rate from 0.31 to {current_value}.",
        },
        confidence=0.6 if status != "insufficient_data" else 0.25,
        caveats=["low_sample_caveat"] if status == "insufficient_data" else [],
    )

    summary = serialize_active_mission_summary(mission, latest_evaluation=evaluation)

    assert summary["title"] == "Survive openings"
    assert summary["progress_status"] == status
    assert summary["metric"] == "opening_death_rate"
    assert summary["baseline_value"] == 0.31
    assert summary["current_value"] == current_value
    assert summary["delta"] == delta
    assert summary["counted"] is counted
    assert summary["confidence"] == (0.25 if status == "insufficient_data" else 0.6)
    assert feedback_phrase in summary["coach_feedback"]
    if status == "insufficient_data":
        assert summary["caveats"] == ["low_sample_caveat"]


def test_active_mission_context_reports_no_evaluation_yet(db):
    owner = _user(db, "owner-no-eval")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Survive openings",
    )

    context = active_mission_context_for_owner(
        db,
        user_id=owner.id,
        owner_steam_id=mission.owner_steam_id,
    )

    summary = context["active_missions"][0]
    assert context["active_mission_count"] == 1
    assert summary["progress_status"] == "no_evaluation_yet"
    assert summary["counted"] is False
    assert summary["confidence"] is None
    assert summary["caveats"] == ["no_evaluation_yet"]
    assert "wait for persisted owner-scoped progress data" in summary["coach_feedback"]


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
    assert result["snapshot_comparison"]["before"]["metric_snapshot_ids"] == []
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
                    "opening_death_rate": 0.28,
                    "opening_duel_attempts": 1,
                },
                sample_matches=1,
                sample_rounds=32,
                match_id=match_id,
            )
            for match_id in (301, 302, 303)
        ],
    )

    result = json.loads(evaluation.result_json)
    assert evaluation.status == "not_following"
    assert result["components"][0]["outcome"] == "not_following"
    assert "not_following" in result["components"][0]["reason_codes"]
    assert json.loads(evaluation.caveats_json) == ["opening_death_rate:not_following"]


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
                sample_matches=1,
                sample_rounds=32,
                match_id=match_id,
            )
            for match_id in (201, 202, 203)
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


def test_mission_progress_counts_unique_metric_matches_and_preserves_snapshot_lineage(db):
    owner = _user(db, "owner-sample-semantics")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Unique match sample",
    )

    single = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=501,
                match_id=41,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24},
            )
        ],
        evaluation_window={"sample_matches": 99},
    )
    single_window = json.loads(single.result_json)["evaluation_window_json"]
    assert single_window["snapshot_count"] == 1
    assert single_window["match_ids"] == [41]
    assert single_window["sample_matches"] == 1

    missing_identity_snapshot = _canonical_snapshot(
        owner,
        mission,
        snapshot_id=502,
        match_id=42,
        source="coach_metric_performance",
        metrics={"opening_death_rate": 0.24},
    )
    missing_identity_snapshot.pop("match_id")
    missing_identity = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[missing_identity_snapshot],
    )
    missing_component = json.loads(missing_identity.result_json)["components"][0]
    assert missing_component["sample_matches"] == 0
    assert "missing_match_identity" in missing_component["reason_codes"]

    f09_regression = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=1119,
                match_id=122,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24, "rounds_played": 20},
            ),
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=1130,
                match_id=122,
                source="coach_metric_utility",
                metrics={"effective_enemy_utility_damage": 61},
            ),
        ],
    )
    result = json.loads(f09_regression.result_json)
    window = result["evaluation_window_json"]
    assert window["snapshot_ids"] == [1119, 1130]
    assert window["snapshot_count"] == 2
    assert window["match_ids"] == [122]
    assert window["sample_matches"] == len(window["match_ids"]) == 1
    assert result["components"][0]["metric_snapshot_ids"] == [1119]
    assert result["snapshot_comparison"]["after"]["source_metric_snapshot_ids"] == [1119]


def test_duplicate_snapshot_sources_cannot_satisfy_match_requirement(db):
    owner = _user(db, "owner-duplicate-sample")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_utility_card_with_follow_rule(),
        title="Three real matches required",
    )
    same_match = [
        _canonical_snapshot(
            owner,
            mission,
            snapshot_id=600 + index,
            match_id=51,
            source=source,
            metrics={"opening_death_rate": 0.24, "opening_duel_attempts": 3},
        )
        for index, source in enumerate(("coach_metric_utility", "coach_metric_performance", "legacy_owner_metrics"))
    ]

    insufficient = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=same_match,
    )
    insufficient_result = json.loads(insufficient.result_json)
    assert insufficient.status == "insufficient_data"
    assert insufficient_result["evaluation_window_json"]["snapshot_count"] == 3
    assert insufficient_result["components"][0]["sample_matches"] == 1
    assert "insufficient_sample_matches" in insufficient_result["components"][0]["reason_codes"]

    distinct_matches = [
        _canonical_snapshot(
            owner,
            mission,
            snapshot_id=700 + match_id,
            match_id=match_id,
            source="coach_metric_performance",
            metrics={"opening_death_rate": 0.24, "opening_duel_attempts": 3},
        )
        for match_id in (61, 62, 63)
    ]
    sufficient = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=distinct_matches,
    )
    sufficient_result = json.loads(sufficient.result_json)
    assert sufficient.status == "improving"
    assert sufficient_result["components"][0]["match_ids"] == [61, 62, 63]
    assert sufficient_result["components"][0]["sample_matches"] == 3


def test_metric_observation_resolution_deduplicates_and_surfaces_conflicts(db):
    owner = _user(db, "owner-source-resolution")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Canonical metric source",
    )

    identical = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=801,
                match_id=71,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24},
            ),
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=802,
                match_id=71,
                source="legacy_owner_metrics",
                metrics={"opening_death_rate": 0.24},
            ),
        ],
    )
    component = json.loads(identical.result_json)["components"][0]
    identical_metric_sample = json.loads(identical.result_json)["evaluation_window_json"]["metric_samples"][
        "opening_death_rate"
    ]
    assert component["observed_value"] == 0.24
    assert component["metric_snapshot_ids"] == [801]
    assert component["deduplicated_metric_snapshot_ids"] == [802]
    assert component["sample_matches"] == 1
    assert "duplicate_metric_source_deduplicated" in component["reason_codes"]
    assert identical_metric_sample["observations"][0]["source_parser_artifact_id"] == 10801
    assert {item["source_event_set_id"] for item in identical_metric_sample["source_lineage"]} == {
        "fixture:71:coach_metric_performance",
        "fixture:71:legacy_owner_metrics",
    }

    resolved_conflict = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=803,
                match_id=72,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24},
            ),
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=804,
                match_id=72,
                source="legacy_owner_metrics",
                metrics={"opening_death_rate": 0.9},
            ),
        ],
    )
    resolved_component = json.loads(resolved_conflict.result_json)["components"][0]
    assert resolved_component["observed_value"] == 0.24
    assert "conflicting_metric_sources" in resolved_component["reason_codes"]

    unresolved = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=805,
                match_id=73,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24},
            ),
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=806,
                match_id=73,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.9},
            ),
        ],
    )
    unresolved_component = json.loads(unresolved.result_json)["components"][0]
    assert unresolved.status == "insufficient_data"
    assert unresolved_component["observed_value"] is None
    assert "conflicting_metric_sources" in unresolved_component["reason_codes"]

    reused = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=807,
                match_id=74,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24},
            )
        ]
        * 3,
    )
    reused_window = json.loads(reused.result_json)["evaluation_window_json"]
    assert reused_window["snapshot_count"] == 1
    assert reused_window["sample_matches"] == 1


def test_round_samples_are_metric_specific_and_missing_rounds_fail_closed(db):
    owner = _user(db, "owner-round-semantics")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Supported round sample",
    )
    criteria = list_mission_criteria(db, user_id=owner.id, mission_id=mission.id)[0]
    criteria.min_sample_rounds = 10
    db.flush()

    evaluation = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=901,
                match_id=81,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24, "rounds_played": 12},
            ),
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=902,
                match_id=81,
                source="coach_metric_utility",
                metrics={"opening_death_rate": 0.24, "rounds_played": 12},
            ),
        ],
    )
    result = json.loads(evaluation.result_json)
    assert result["evaluation_window_json"]["sample_rounds"] == 12
    assert result["components"][0]["sample_rounds"] == 12

    missing_rounds = evaluate_mission_progress(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                owner,
                mission,
                snapshot_id=903,
                match_id=82,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24},
            )
        ],
    )
    missing_component = json.loads(missing_rounds.result_json)["components"][0]
    assert missing_rounds.status == "insufficient_data"
    assert missing_component["sample_rounds"] == 0
    assert "unavailable_round_sample" in missing_component["reason_codes"]
    assert "insufficient_sample_rounds" in missing_component["reason_codes"]


def test_criterion_confidence_uses_only_canonical_metric_observations(db):
    utility_owner = _user(db, "owner-opening-confidence")
    utility_mission = _active_mission_from_card(
        db,
        owner=utility_owner,
        card=_ready_utility_card_with_follow_rule(),
        title="Opening confidence",
    )
    utility_criteria = list_mission_criteria(
        db,
        user_id=utility_owner.id,
        mission_id=utility_mission.id,
    )[0]
    utility_criteria.confidence_required = 0.6
    db.flush()
    utility_snapshots = []
    for match_id in (91, 92, 93):
        utility_snapshots.extend(
            [
                _canonical_snapshot(
                    utility_owner,
                    utility_mission,
                    snapshot_id=1000 + match_id,
                    match_id=match_id,
                    source="coach_metric_performance",
                    metrics={"opening_death_rate": 0.24, "opening_duel_attempts": 3},
                    confidence={"opening_death_rate": "low", "opening_duel_attempts": "low"},
                ),
                _canonical_snapshot(
                    utility_owner,
                    utility_mission,
                    snapshot_id=1100 + match_id,
                    match_id=match_id,
                    source="legacy_owner_metrics",
                    metrics={"opening_death_rate": 0.24},
                    confidence={"opening_death_rate": "high"},
                ),
            ]
        )
    utility_evaluation = evaluate_mission_progress(
        db,
        user_id=utility_owner.id,
        mission_id=utility_mission.id,
        evaluation_metric_snapshots=utility_snapshots,
    )
    utility_component = json.loads(utility_evaluation.result_json)["components"][0]
    assert utility_component["canonical_source"] == "coach_metric_performance"
    assert utility_component["confidence"] == 0.25
    assert "insufficient_confidence" in utility_component["reason_codes"]

    combat_owner = _user(db, "owner-combat-confidence")
    combat_mission = _active_mission_from_card(
        db,
        owner=combat_owner,
        card=_ready_opening_death_card(),
        title="Combat confidence",
    )
    combat_evaluation = evaluate_mission_progress(
        db,
        user_id=combat_owner.id,
        mission_id=combat_mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                combat_owner,
                combat_mission,
                snapshot_id=1201,
                match_id=94,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24},
                confidence={"opening_death_rate": "high"},
            ),
            _canonical_snapshot(
                combat_owner,
                combat_mission,
                snapshot_id=1202,
                match_id=94,
                source="coach_metric_utility",
                metrics={"effective_enemy_utility_damage": 10},
                confidence={"effective_enemy_utility_damage": "low"},
            ),
        ],
    )
    assert combat_evaluation.status == "improving"
    assert combat_evaluation.confidence == 0.9

    missing_confidence = evaluate_mission_progress(
        db,
        user_id=combat_owner.id,
        mission_id=combat_mission.id,
        evaluation_metric_snapshots=[
            _canonical_snapshot(
                combat_owner,
                combat_mission,
                snapshot_id=1203,
                match_id=95,
                source="coach_metric_performance",
                metrics={"opening_death_rate": 0.24},
                confidence={},
            )
        ],
    )
    missing_component = json.loads(missing_confidence.result_json)["components"][0]
    assert missing_confidence.status == "insufficient_data"
    assert missing_confidence.confidence is None
    assert "missing_metric_specific_confidence" in missing_component["reason_codes"]
    assert "missing_confidence" in missing_component["reason_codes"]


def test_active_mission_requires_ready_metric_confidence_and_persists_explicit_criteria(db):
    owner = _user(db, "owner")
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000002")
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card={
            "problem": "Utility damage can become a measurable mission.",
            "evidence": [{"metric_id": "effective_enemy_utility_damage", "value": 94, "metric_confidence": "medium"}],
            "confidence": "medium",
            "caveats": [],
            "recommended_focus": "Review damage-producing grenade rounds.",
            "mission_readiness": {
                "can_become_mission": True,
                "target_metric_candidate": "effective_enemy_utility_damage",
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
                        "metric_name": "effective_enemy_utility_damage",
                        "role": "primary",
                        "direction": "higher_is_better",
                        "baseline_value": 94,
                        "target_value": 110,
                        "min_sample_matches": 3,
                    },
                    {
                        "metric_name": "enemy_he_damage",
                        "role": "secondary",
                        "direction": "higher_is_better",
                        "baseline_value": 20,
                        "target_value": 25,
                    },
                    {
                        "metric_name": "effective_enemy_utility_damage",
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

    with pytest.raises(ValueError, match="Noncanonical coach domain"):
        activate_draft_coach_mission(db, user_id=owner.id, mission_id=draft.id)
    assert draft.status == "draft"


def test_activation_blocks_low_or_mission_ineligible_metrics(db):
    owner = _user(db, "owner")
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id="76561198000000003")
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card={
            "problem": "Low-confidence utility context is not a hard mission.",
            "evidence": [{"metric_id": "effective_enemy_utility_damage", "value": 90, "metric_confidence": "low"}],
            "confidence": "low",
            "caveats": ["Utility events are incomplete."],
            "recommended_focus": "Collect stronger utility evidence first.",
            "mission_readiness": {
                "can_become_mission": False,
                "target_metric_candidate": "effective_enemy_utility_damage",
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


def test_rolling_last_30_window_generates_ranked_owner_mission_candidates(db):
    owner = _user(db, "owner")
    other = _user(db, "other")
    owner_steam_id = "76561198000000001"
    other_steam_id = "76561198000000999"
    for index, metrics in enumerate(
        (
            {
                "rounds_played": 10,
                "survival_rate": 0.5,
                "opening_death_rate": 0.3,
                "untraded_death_rate": 0.8,
                "traded_death_rate": 0.2,
                "trade_status_known_deaths": 5,
            },
            {
                "rounds_played": 12,
                "survival_rate": 0.55,
                "opening_death_rate": 0.35,
                "untraded_death_rate": 0.7,
                "traded_death_rate": 0.3,
                "trade_status_known_deaths": 5,
            },
            {
                "rounds_played": 14,
                "survival_rate": 0.45,
                "opening_death_rate": 0.34,
                "untraded_death_rate": 0.75,
                "traded_death_rate": 0.25,
                "trade_status_known_deaths": 6,
            },
        ),
        start=1,
    ):
        match = _match(db, owner=owner, external_match_id=f"owner-{index}", day=index)
        _rolling_metric_snapshot(db, match=match, owner_steam_id=owner_steam_id, metrics=metrics)
    other_match = _match(db, owner=other, external_match_id="other-1", day=4)
    _rolling_metric_snapshot(
        db,
        match=other_match,
        owner_steam_id=other_steam_id,
        metrics={
            "rounds_played": 16,
            "survival_rate": 0.1,
            "opening_death_rate": 0.8,
            "untraded_death_rate": 1.0,
            "trade_status_known_deaths": 8,
        },
    )

    result = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
        window_type="last_30",
    )

    assert result["window"]["sample_matches"] == 3
    assert set(result["window"]["match_ids"]) != {other_match.id}
    candidates = result["candidates"]
    assert [candidate["primary_metric"] for candidate in candidates] == [
        "untraded_death_rate",
        "opening_death_rate",
    ]
    assert [candidate["rank"] for candidate in candidates] == [1, 2]
    assert candidates[0]["explanation"].startswith("Generated from last_30 owner metric snapshots")
    assert validate_mission_payload(candidates[0]["mission_payload"]) == ()
    assert candidates[0]["mission_payload"]["success_metric"]["metric_name"] == "untraded_death_rate"
    assert candidates[1]["mission_payload"]["success_metric"]["metric_name"] == "opening_death_rate"


def test_rolling_custom_match_set_uses_only_requested_owner_matches(db):
    owner = _user(db, "owner")
    owner_steam_id = "76561198000000001"
    selected_matches = []
    for index in range(1, 5):
        match = _match(db, owner=owner, external_match_id=f"custom-{index}", day=index)
        _rolling_metric_snapshot(
            db,
            match=match,
            owner_steam_id=owner_steam_id,
            metrics={
                "rounds_played": 10,
                "survival_rate": 0.48,
                "opening_death_rate": 0.33,
            },
        )
        if index <= 3:
            selected_matches.append(match)

    result = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
        window_type="custom_match_set",
        match_ids=[match.id for match in selected_matches],
    )

    assert result["window"]["window_type"] == "custom_match_set"
    assert set(result["window"]["match_ids"]) == {match.id for match in selected_matches}
    assert result["candidates"][0]["primary_metric"] == "opening_death_rate"


def test_rolling_window_keeps_utility_value_context_only(db):
    owner = _user(db, "owner")
    owner_steam_id = "76561198000000001"
    matches, _ = _utility_trend_snapshots(
        db,
        owner=owner,
        owner_steam_id=owner_steam_id,
        values=[*[50] * 5, *[45] * 5],
        prefix="utility",
        confidence_level="medium",
    )

    result = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
        window_type="last_30",
    )

    trend = result["diagnostics"]["effective_enemy_utility_damage"]
    assert trend["evidence_available"] is True
    assert trend["deficiency_detected"] is True
    assert trend["mission_ready"] is True
    assert trend["baseline_match_ids"] == [match.id for match in matches[:5]]
    assert trend["recent_match_ids"] == [match.id for match in matches[5:]]
    assert set(trend["baseline_match_ids"]).isdisjoint(trend["recent_match_ids"])
    assert trend["baseline_value"] == 50
    assert trend["recent_value"] == 45
    assert trend["relative_drop"] == 0.1
    assert trend["severity"] == 0.1
    assert trend["classification"] == "context-only"
    assert trend["mission_eligible"] is False
    assert "noncanonical_utility_value_family" in trend["reason_codes"]
    assert result["candidates"] == []

    persisted = persist_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
        window_type="last_30",
    )
    assert persisted["coach_hypothesis_ids"] == []


@pytest.mark.parametrize(
    ("recent_value", "candidate_expected", "reason_code", "expected_severity"),
    [
        (55, False, "utility_trend_not_negative", 0.0),
        (50, False, "utility_trend_not_negative", 0.0),
        (46, False, "utility_drop_below_materiality_gate", 0.08),
        (45.5, False, "utility_drop_below_materiality_gate", 0.09),
        (45, False, None, 0.1),
        (40, False, None, 0.2),
    ],
)
def test_utility_trend_direction_and_materiality_gate(
    db,
    recent_value,
    candidate_expected,
    reason_code,
    expected_severity,
):
    owner = _user(db, f"owner-{recent_value}")
    owner_steam_id = f"7656119800000{int(recent_value * 10):04d}"
    _utility_trend_snapshots(
        db,
        owner=owner,
        owner_steam_id=owner_steam_id,
        values=[*[50] * 5, *[recent_value] * 5],
        prefix=f"direction-{recent_value}",
    )

    result = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
    )

    trend = result["diagnostics"]["effective_enemy_utility_damage"]
    assert trend["severity"] == expected_severity
    assert bool(result["candidates"]) is candidate_expected
    if reason_code is None:
        assert trend["reason_codes"] == ["noncanonical_utility_value_family"]
    else:
        assert reason_code in trend["reason_codes"]


def test_utility_trend_windows_are_chronological_deterministic_and_bounded(db):
    owner_21 = _user(db, "owner-21")
    owner_21_steam_id = "76561198000000021"
    matches_21, _ = _utility_trend_snapshots(
        db,
        owner=owner_21,
        owner_steam_id=owner_21_steam_id,
        values=[999, *[50] * 10, *[45] * 10],
        prefix="window-21",
    )

    result_21 = generate_rolling_mission_candidates(
        db,
        user_id=owner_21.id,
        owner_steam_id=owner_21_steam_id,
    )
    trend_21 = result_21["diagnostics"]["effective_enemy_utility_damage"]
    assert trend_21["ignored_oldest_match_ids"] == [matches_21[0].id]
    assert trend_21["baseline_match_ids"] == [match.id for match in matches_21[1:11]]
    assert trend_21["recent_match_ids"] == [match.id for match in matches_21[11:]]

    owner_31 = _user(db, "owner-31")
    owner_31_steam_id = "76561198000000031"
    matches_31, _ = _utility_trend_snapshots(
        db,
        owner=owner_31,
        owner_steam_id=owner_31_steam_id,
        values=[999, *[50] * 15, *[45] * 15],
        prefix="window-31",
    )

    result_31 = generate_rolling_mission_candidates(
        db,
        user_id=owner_31.id,
        owner_steam_id=owner_31_steam_id,
    )
    trend_31 = result_31["diagnostics"]["effective_enemy_utility_damage"]
    assert trend_31["supported_match_count"] == 30
    assert matches_31[0].id not in trend_31["supported_match_ids"]
    assert trend_31["ignored_oldest_match_ids"] == [matches_31[0].id]
    assert trend_31["baseline_match_ids"] == [match.id for match in matches_31[1:16]]
    assert trend_31["recent_match_ids"] == [match.id for match in matches_31[16:]]


def test_utility_trend_deduplicates_sources_and_excludes_non_owner_snapshots(db):
    owner = _user(db, "utility-owner-dedup")
    other = _user(db, "utility-other-dedup")
    owner_steam_id = "76561198000000101"
    matches, canonical_snapshots = _utility_trend_snapshots(
        db,
        owner=owner,
        owner_steam_id=owner_steam_id,
        values=[*[50] * 5, *[45] * 5],
        prefix="dedup-owner",
    )
    duplicate_snapshot_ids = []
    for match, value in zip(matches, [*[50] * 5, *[45] * 5], strict=True):
        duplicate_snapshot_ids.append(
            _rolling_metric_snapshot(
                db,
                match=match,
                owner_steam_id=owner_steam_id,
                metrics={"effective_enemy_utility_damage": value},
                source="coach_metric_performance",
            ).id
        )
    _utility_trend_snapshots(
        db,
        owner=other,
        owner_steam_id="76561198000000999",
        values=[*[500] * 5, *[1] * 5],
        prefix="dedup-other",
    )

    result = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
    )

    trend = result["diagnostics"]["effective_enemy_utility_damage"]
    assert trend["supported_match_count"] == 10
    assert trend["supported_snapshot_ids"] == [snapshot.id for snapshot in canonical_snapshots]
    assert set(duplicate_snapshot_ids).isdisjoint(trend["supported_snapshot_ids"])
    assert "Duplicate effective utility damage observations" in " ".join(trend["caveats"])


def test_utility_trend_fails_closed_for_insufficient_confidence_conflict_and_invalid_baseline(db):
    insufficient_owner = _user(db, "utility-insufficient")
    insufficient_steam_id = "76561198000000201"
    _utility_trend_snapshots(
        db,
        owner=insufficient_owner,
        owner_steam_id=insufficient_steam_id,
        values=[*[50] * 4, *[45] * 5],
        prefix="insufficient",
    )
    insufficient = persist_rolling_mission_candidates(
        db,
        user_id=insufficient_owner.id,
        owner_steam_id=insufficient_steam_id,
    )
    assert insufficient["candidates"] == []
    assert insufficient["coach_hypothesis_ids"] == []
    assert (
        "insufficient_supported_matches"
        in insufficient["diagnostics"]["effective_enemy_utility_damage"]["reason_codes"]
    )

    low_owner = _user(db, "utility-low-confidence")
    low_steam_id = "76561198000000202"
    _utility_trend_snapshots(
        db,
        owner=low_owner,
        owner_steam_id=low_steam_id,
        values=[*[50] * 5, *[40] * 5],
        prefix="low-confidence",
        confidence_level="low",
        usable_for_missions=False,
    )
    low = generate_rolling_mission_candidates(db, user_id=low_owner.id, owner_steam_id=low_steam_id)
    assert low["candidates"] == []
    assert "insufficient_confidence" in low["diagnostics"]["effective_enemy_utility_damage"]["reason_codes"]

    zero_owner = _user(db, "utility-zero-baseline")
    zero_steam_id = "76561198000000203"
    _utility_trend_snapshots(
        db,
        owner=zero_owner,
        owner_steam_id=zero_steam_id,
        values=[*[0] * 5, *[0] * 5],
        prefix="zero-baseline",
    )
    zero = generate_rolling_mission_candidates(db, user_id=zero_owner.id, owner_steam_id=zero_steam_id)
    assert zero["candidates"] == []
    assert "invalid_baseline" in zero["diagnostics"]["effective_enemy_utility_damage"]["reason_codes"]

    conflict_owner = _user(db, "utility-conflict")
    conflict_steam_id = "76561198000000204"
    conflict_matches = []
    for index, value in enumerate([*[50] * 5, *[40] * 5], start=1):
        match = _match(db, owner=conflict_owner, external_match_id=f"conflict-{index}", day=index)
        conflict_matches.append(match)
        _rolling_metric_snapshot(
            db,
            match=match,
            owner_steam_id=conflict_steam_id,
            metrics={"effective_enemy_utility_damage": value},
            source="coach_metric_performance",
        )
    _rolling_metric_snapshot(
        db,
        match=conflict_matches[-1],
        owner_steam_id=conflict_steam_id,
        metrics={"effective_enemy_utility_damage": 1},
        source="legacy_owner_metrics",
    )
    conflict = generate_rolling_mission_candidates(
        db,
        user_id=conflict_owner.id,
        owner_steam_id=conflict_steam_id,
    )
    assert conflict["candidates"] == []
    assert "conflicting_metric_sources" in conflict["diagnostics"]["effective_enemy_utility_damage"]["reason_codes"]


def test_valid_utility_trend_persists_context_without_hypothesis_or_mission(db):
    owner = _user(db, "utility-persistence")
    owner_steam_id = "76561198000000301"
    _utility_trend_snapshots(
        db,
        owner=owner,
        owner_steam_id=owner_steam_id,
        values=[*[50] * 5, *[45] * 5],
        prefix="persistence",
    )

    result = persist_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
    )

    trend = result["diagnostics"]["effective_enemy_utility_damage"]
    assert result["coach_hypothesis_ids"] == []
    analysis_run = get_analysis_run(db, user_id=owner.id, analysis_run_id=result["analysis_run_id"])
    assert analysis_run is not None
    persisted_trend = json.loads(analysis_run.source_payload_json)["rolling_window"]["utility_trend"]
    assert persisted_trend["baseline_value"] == trend["baseline_value"]
    assert persisted_trend["recent_value"] == trend["recent_value"]
    assert trend["classification"] == "context-only"
    assert trend["mission_eligible"] is False
    assert list_coach_hypotheses(db, user_id=owner.id) == []
    assert list_coach_missions(db, user_id=owner.id) == []


def test_same_domain_active_mission_suppresses_candidates_and_utility_stays_context(db):
    owner = _user(db, "utility-domain-suppression")
    owner_steam_id = "76561198000000302"
    matches, _ = _utility_trend_snapshots(
        db,
        owner=owner,
        owner_steam_id=owner_steam_id,
        values=[*[50] * 5, *[40] * 5],
        prefix="domain-suppression",
    )
    for match in matches:
        _rolling_metric_snapshot(
            db,
            match=match,
            owner_steam_id=owner_steam_id,
            metrics={
                "rounds_played": 10,
                "untraded_death_rate": 0.8,
                "trade_status_known_deaths": 5,
            },
            source="coach_metric_performance",
        )
    active_mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Existing duel mission",
    )
    active_mission.owner_steam_id = owner_steam_id
    db.flush()

    result = persist_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
    )

    trade = next(candidate for candidate in result["candidates"] if candidate["family"] == "bad_fight_trade")
    assert all(candidate["family"] != "utility_value" for candidate in result["candidates"])
    assert trade["suppressed_by_active_mission"] is True
    assert trade["suppression_reason"] == "active_mission_same_domain"
    assert result["coach_hypothesis_ids"] == []


def test_rolling_window_weak_or_unavailable_evidence_generates_no_candidate(db):
    owner = _user(db, "owner")
    owner_steam_id = "76561198000000001"
    for index in range(1, 4):
        match = _match(db, owner=owner, external_match_id=f"weak-{index}", day=index)
        _rolling_metric_snapshot(
            db,
            match=match,
            owner_steam_id=owner_steam_id,
            metrics={
                "rounds_played": 10,
                "survival_rate": 0.58,
                "opening_death_rate": 0.22,
                "ambiguous_traded_deaths": 2,
            },
            confidence_level="low",
            usable_for_missions=False,
        )

    result = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
        window_type="last_30",
    )

    assert result["window"]["confidence"] == "low"
    assert result["candidates"] == []


def test_rolling_window_non_owner_snapshots_do_not_generate_candidate(db):
    owner = _user(db, "owner")
    other = _user(db, "other")
    owner_steam_id = "76561198000000001"
    for index in range(1, 4):
        match = _match(db, owner=other, external_match_id=f"non-owner-{index}", day=index)
        _rolling_metric_snapshot(
            db,
            match=match,
            owner_steam_id="76561198000000999",
            metrics={
                "rounds_played": 12,
                "opening_death_rate": 0.7,
                "survival_rate": 0.2,
            },
        )

    result = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
        window_type="last_30",
    )

    assert result["window"]["match_ids"] == []
    assert result["window"]["metric_snapshot_ids"] == []
    assert result["candidates"] == []


def test_rolling_candidates_suppress_active_duplicate_and_persist_hypotheses(db):
    owner = _user(db, "owner")
    owner_steam_id = "76561198000000001"
    active_mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Opening deaths",
    )
    active_mission.owner_steam_id = owner_steam_id
    for index in range(1, 4):
        match = _match(db, owner=owner, external_match_id=f"suppression-{index}", day=index)
        _rolling_metric_snapshot(
            db,
            match=match,
            owner_steam_id=owner_steam_id,
            metrics={
                "rounds_played": 10,
                "survival_rate": 0.5,
                "opening_death_rate": 0.34,
                "untraded_death_rate": 0.75,
                "trade_status_known_deaths": 5,
            },
        )

    result = persist_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=owner_steam_id,
        window_type="last_30",
    )

    opening = next(
        candidate for candidate in result["candidates"] if candidate["primary_metric"] == "opening_death_rate"
    )
    assert opening["suppressed_by_active_mission"] is True
    assert opening["suppression_reason"] == "active_mission_same_domain"
    assert opening["suppression_reason_codes"] == ["active_mission_same_domain"]
    assert opening["suppression_key"]["domain_key"] == "bad_fight_selection"
    assert result["coach_hypothesis_ids"] == []
    persisted = get_analysis_run(db, user_id=owner.id, analysis_run_id=result["analysis_run_id"])
    assert persisted is not None
    assert json.loads(persisted.analysis_scope_json)["window_type"] == "last_30"


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
    cancelled = cancel_coach_mission(
        db,
        user_id=owner.id,
        mission_id=mission.id,
        reason="superseded_by_utility_semantics_repair",
    )
    assert cancelled.status == "cancelled"
    assert cancelled.ended_at is not None
    assert json.loads(cancelled.source_payload_json)["lifecycle_events"][-1]["reason"] == (
        "superseded_by_utility_semantics_repair"
    )


def test_mission_lifecycle_transitions_are_explicit_and_inactive_missions_do_not_evaluate(db):
    owner = _user(db, "owner")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Opening deaths",
    )

    paused = pause_coach_mission(db, user_id=owner.id, mission_id=mission.id)
    assert paused.status == "paused"
    assert list_active_coach_missions(db, user_id=owner.id) == []
    with pytest.raises(ValueError, match="Cannot evaluate mission progress from status: paused"):
        evaluate_mission_progress(
            db,
            user_id=owner.id,
            mission_id=mission.id,
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

    resumed = resume_coach_mission(db, user_id=owner.id, mission_id=mission.id)
    assert resumed.status == "active"
    completed = complete_coach_mission(db, user_id=owner.id, mission_id=mission.id)
    assert completed.status == "completed"
    assert completed.ended_at is not None
    assert list_active_coach_missions(db, user_id=owner.id) == []
    with pytest.raises(ValueError, match="Cannot activate mission from status: completed"):
        resume_coach_mission(db, user_id=owner.id, mission_id=mission.id)


def test_fail_and_expire_helpers_are_terminal_and_duration_checked(db):
    owner = _user(db, "owner")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Opening deaths",
    )

    with pytest.raises(ValueError, match="Cannot expire mission before configured duration/window is exceeded"):
        expire_coach_mission(db, user_id=owner.id, mission_id=mission.id, observed_matches=4)

    expired = expire_coach_mission(db, user_id=owner.id, mission_id=mission.id, observed_matches=5)
    assert expired.status == "expired"
    assert expired.ended_at is not None
    with pytest.raises(ValueError, match="Cannot transition mission from expired to cancelled"):
        cancel_coach_mission(db, user_id=owner.id, mission_id=mission.id)

    failed_mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_survival_with_adr_guardrail_card(),
        title="Survival discipline",
    )
    failed = fail_coach_mission(db, user_id=owner.id, mission_id=failed_mission.id)
    assert failed.status == "failed"
    assert failed.ended_at is not None


def test_active_mission_listing_filters_by_owner_and_domain(db):
    owner = _user(db, "owner")
    other_owner = _user(db, "other")
    opening = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Opening deaths",
    )
    other_opening = _active_mission_from_card(
        db,
        owner=other_owner,
        card=_ready_opening_death_card(),
        title="Other opening deaths",
    )

    assert list_active_coach_missions(
        db,
        user_id=owner.id,
        owner_steam_id=opening.owner_steam_id,
        domain_key="bad_fight_selection",
    ) == [opening]
    assert list_active_coach_missions(
        db,
        user_id=owner.id,
        owner_steam_id=opening.owner_steam_id,
        domain_key="impact_leak",
    ) == []
    assert list_active_coach_missions(db, user_id=other_owner.id) == [other_opening]


def test_duplicate_active_mission_same_owner_domain_is_rejected_or_replaced(db):
    owner = _user(db, "owner")
    first = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Opening deaths",
    )
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id=first.owner_steam_id)
    duplicate_hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card=_ready_survival_with_adr_guardrail_card(),
    )

    with pytest.raises(ValueError, match="Duplicate active mission for owner/domain:"):
        activate_coach_mission(
            db,
            user_id=owner.id,
            hypothesis_id=duplicate_hypothesis.id,
            title="Same domain",
        )

    replacement = activate_coach_mission(
        db,
        user_id=owner.id,
        hypothesis_id=duplicate_hypothesis.id,
        title="Same domain",
        duplicate_policy="replace",
    )
    assert replacement.status == "active"
    assert first.status == "cancelled"
    assert first.ended_at is not None
    assert list_active_coach_missions(
        db,
        user_id=owner.id,
        owner_steam_id=first.owner_steam_id,
        domain_key="bad_fight_selection",
    ) == [replacement]


def test_cross_owner_lifecycle_mutations_are_denied_for_new_helpers(db):
    owner = _user(db, "owner")
    other_owner = _user(db, "other")
    mission = _active_mission_from_card(
        db,
        owner=owner,
        card=_ready_opening_death_card(),
        title="Opening deaths",
    )

    with pytest.raises(PermissionError):
        complete_coach_mission(db, user_id=other_owner.id, mission_id=mission.id)
    with pytest.raises(PermissionError):
        expire_coach_mission(db, user_id=other_owner.id, mission_id=mission.id, force=True)
    with pytest.raises(PermissionError):
        fail_coach_mission(db, user_id=other_owner.id, mission_id=mission.id)


def _user(db, display_name: str) -> User:
    user = User(display_name=display_name)
    db.add(user)
    db.flush()
    return user


def _match(db, *, owner: User, external_match_id: str, day: int) -> Match:
    match = Match(
        user_id=owner.id,
        source="steam",
        external_match_id=external_match_id,
        played_at=datetime(2026, 7, day),
        map_name="Mirage",
    )
    db.add(match)
    db.flush()
    return match


def _rolling_metric_snapshot(
    db,
    *,
    match: Match,
    owner_steam_id: str,
    metrics: dict,
    confidence_level: str = "high",
    usable_for_missions: bool = True,
    source: str = "coach_metric_performance",
) -> MetricSnapshot:
    confidence = {
        "source": "rolling-test",
        "metrics": {
            metric_name: {
                "level": confidence_level,
                "usable_for_insights": usable_for_missions,
                "usable_for_missions": usable_for_missions,
                "hard_recommendation_eligible": usable_for_missions,
            }
            for metric_name in (
                "survival_rate",
                "opening_death_rate",
                "opening_duel_win_rate",
                "untraded_death_rate",
                "traded_death_rate",
                "effective_enemy_utility_damage",
            )
        },
    }
    snapshot = MetricSnapshot(
        owner_user_id=match.user_id,
        match_id=match.id,
        player_key=f"steam:{owner_steam_id}",
        player_steamid=owner_steam_id,
        source=source,
        metric_domain="coach_utility" if source == "coach_metric_utility" else "coach_performance",
        semantic_version="3.0.0",
        validation_status="validated",
        source_event_set_id=f"fixture:{match.id}:{source}",
        metrics_json=json.dumps(metrics),
        confidence_baseline_json=json.dumps(confidence),
        caveats_json=json.dumps([]),
        metadata_json=json.dumps({"schema_version": "rolling-test"}),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _utility_trend_snapshots(
    db,
    *,
    owner: User,
    owner_steam_id: str,
    values: list[int | float],
    prefix: str,
    confidence_level: str = "high",
    usable_for_missions: bool = True,
) -> tuple[list[Match], list[MetricSnapshot]]:
    matches: list[Match] = []
    snapshots: list[MetricSnapshot] = []
    for index, value in enumerate(values, start=1):
        match = _match(db, owner=owner, external_match_id=f"{prefix}-{index}", day=index)
        matches.append(match)
        snapshots.append(
            _rolling_metric_snapshot(
                db,
                match=match,
                owner_steam_id=owner_steam_id,
                metrics={"effective_enemy_utility_damage": value},
                confidence_level=confidence_level,
                usable_for_missions=usable_for_missions,
                source="coach_metric_utility",
            )
        )
    return matches, snapshots


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
        "problem": "Opening deaths need repeatable duel discipline.",
        "evidence": [{"metric_id": "opening_death_rate", "value": 0.31, "metric_confidence": "medium"}],
        "confidence": "medium",
        "caveats": [],
        "recommended_focus": "Use bounded opening-duel discipline.",
        "mission_readiness": {
            "can_become_mission": True,
            "canonical_domain_key": "bad_fight_selection",
            "family": "bad_fight_selection",
            "target_metric_candidate": "opening_death_rate",
            "baseline_value": 0.31,
            "confidence_eligibility": {
                "level": "medium",
                "usable_for_missions": True,
                "hard_recommendation_eligible": True,
            },
            "missing_requirements": [],
            "blocking_reason_codes": [],
            "criteria": [
                {
                    "metric_name": "opening_death_rate",
                    "role": "primary",
                    "direction": "lower_is_better",
                    "baseline_value": 0.31,
                    "target_value": 0.26,
                    "min_sample_matches": 3,
                    "rule": {
                        "follow_rule": {
                            "metric_name": "opening_duel_attempts",
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
    match_id: int | None = None,
) -> dict:
    resolved_match_id = match_id or owner.id * 10000 + sample_rounds
    return {
        "id": match_id * 10 + owner.id if match_id is not None else owner.id * 1000 + sample_rounds,
        "match_id": resolved_match_id,
        "user_id": owner.id,
        "owner_steam_id": owner_steam_id,
        "source": "coach_metric_performance",
        "metrics": metrics,
        "confidence_baseline": {
            "metrics": {metric_name: {"level": "medium"} for metric_name in metrics}
        },
        "sample_matches": sample_matches,
        "sample_rounds": sample_rounds,
    }


def _canonical_snapshot(
    owner: User,
    mission: CoachMission,
    *,
    snapshot_id: int,
    match_id: int,
    source: str,
    metrics: dict,
    confidence: dict[str, str] | None = None,
    sample_rounds: int | None = None,
) -> dict:
    confidence_by_metric = (
        {metric_name: {"level": level} for metric_name, level in confidence.items()}
        if confidence is not None
        else {metric_name: {"level": "medium"} for metric_name in metrics}
    )
    snapshot = {
        "id": snapshot_id,
        "match_id": match_id,
        "user_id": owner.id,
        "owner_steam_id": mission.owner_steam_id,
        "player_steamid": mission.owner_steam_id,
        "source": source,
        "source_parser_artifact_id": snapshot_id + 10000,
        "source_event_set_id": f"fixture:{match_id}:{source}",
        "metrics": metrics,
        "confidence_baseline": {"metrics": confidence_by_metric},
        "caveats": [],
    }
    if sample_rounds is not None:
        snapshot["sample_rounds"] = sample_rounds
    return snapshot


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
        "source": "coach_metric_performance",
        "source_event_set_id": "fixture:e02",
        "metrics": metrics,
        "confidence_baseline": {"source": "core-combat-metrics-v1", "metrics": confidence},
        "caveats": [],
        "metadata": {"schema_version": "core-combat-metrics-v1"},
    }
