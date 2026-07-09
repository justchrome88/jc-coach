from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AnalysisRun, CoachHypothesis, CoachMission, MissionCriteria, MissionProgressEvaluation

MISSION_PROGRESS_STATUSES = {
    "improving",
    "unchanged",
    "regressing",
    "insufficient_data",
    "not_following",
}
INSIGHT_CONFIDENCE_SCORES = {
    "low": 0.25,
    "medium": 0.6,
    "high": 0.9,
}
MISSION_STATUSES = {"draft", "active", "completed", "failed", "paused", "cancelled"}
CRITERIA_ROLES = {"primary", "secondary", "guardrail"}
CRITERIA_DIRECTIONS = {
    "higher_is_better",
    "lower_is_better",
    "stay_above",
    "stay_below",
    "not_drop_more_than",
    "improve_or_same",
}
MISSION_ELIGIBLE_CONFIDENCE_LEVELS = {"medium", "high"}


def create_analysis_run(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str | None = None,
    mode: str = "personal",
    status: str = "created",
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    source: str | None = None,
    selected_metric_snapshot_ids: Sequence[int] | None = None,
    analysis_scope: Mapping[str, Any] | None = None,
    source_payload: Mapping[str, Any] | None = None,
) -> AnalysisRun:
    run = AnalysisRun(
        user_id=user_id,
        owner_steam_id=owner_steam_id,
        mode=mode,
        status=status,
        window_start=window_start,
        window_end=window_end,
        source=source,
        selected_metric_snapshot_ids_json=_json_list(selected_metric_snapshot_ids or []),
        analysis_scope_json=_json_object(analysis_scope or {}),
        source_payload_json=_json_object(source_payload or {}),
    )
    db.add(run)
    db.flush()
    return run


def get_analysis_run(db: Session, *, user_id: int, analysis_run_id: int) -> AnalysisRun | None:
    return db.scalar(
        select(AnalysisRun).where(AnalysisRun.id == analysis_run_id).where(AnalysisRun.user_id == user_id)
    )


def list_analysis_runs(db: Session, *, user_id: int) -> list[AnalysisRun]:
    return list(
        db.scalars(
            select(AnalysisRun)
            .where(AnalysisRun.user_id == user_id)
            .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
        ).all()
    )


def create_coach_hypothesis(
    db: Session,
    *,
    user_id: int,
    analysis_run_id: int,
    insight_card: Mapping[str, Any],
    status: str = "candidate",
) -> CoachHypothesis:
    analysis_run = _require_owned_analysis_run(db, user_id=user_id, analysis_run_id=analysis_run_id)
    hypothesis = CoachHypothesis(
        analysis_run_id=analysis_run.id,
        user_id=user_id,
        owner_steam_id=analysis_run.owner_steam_id,
        status=status,
        source_insight_card_id=_optional_str(insight_card.get("id") or insight_card.get("card_id")),
        problem=str(insight_card.get("problem") or ""),
        evidence_json=_json_any(insight_card.get("evidence") or []),
        confidence=_optional_float(insight_card.get("confidence")),
        caveats_json=_json_any(insight_card.get("caveats") or []),
        recommended_focus=str(insight_card.get("recommended_focus") or ""),
        mission_readiness_json=_json_any(_mission_readiness(insight_card)),
        target_metric_candidates_json=_json_any(_target_metric_candidates(insight_card)),
        source_card_json=_json_any(dict(insight_card)),
    )
    db.add(hypothesis)
    db.flush()
    return hypothesis


def get_coach_hypothesis(db: Session, *, user_id: int, hypothesis_id: int) -> CoachHypothesis | None:
    return db.scalar(
        select(CoachHypothesis).where(CoachHypothesis.id == hypothesis_id).where(CoachHypothesis.user_id == user_id)
    )


def list_coach_hypotheses(db: Session, *, user_id: int, analysis_run_id: int | None = None) -> list[CoachHypothesis]:
    stmt = (
        select(CoachHypothesis)
        .where(CoachHypothesis.user_id == user_id)
        .order_by(CoachHypothesis.created_at.desc(), CoachHypothesis.id.desc())
    )
    if analysis_run_id is not None:
        stmt = stmt.where(CoachHypothesis.analysis_run_id == analysis_run_id)
    return list(db.scalars(stmt).all())


def activate_coach_mission(
    db: Session,
    *,
    user_id: int,
    hypothesis_id: int,
    title: str,
    focus: str | None = None,
    status: str = "active",
    source_payload: Mapping[str, Any] | None = None,
) -> CoachMission:
    if status not in MISSION_STATUSES:
        raise ValueError(f"Unsupported mission status: {status}")
    hypothesis = _require_owned_hypothesis(db, user_id=user_id, hypothesis_id=hypothesis_id)
    criteria_specs = _criteria_specs_from_hypothesis(hypothesis)
    if status == "active":
        _validate_hypothesis_can_activate(hypothesis, criteria_specs)
    mission = CoachMission(
        hypothesis_id=hypothesis.id,
        user_id=user_id,
        owner_steam_id=hypothesis.owner_steam_id,
        status=status,
        title=title,
        focus=focus if focus is not None else hypothesis.recommended_focus,
        source_payload_json=_json_object(_mission_source_payload(hypothesis, source_payload)),
    )
    db.add(mission)
    db.flush()
    for criteria_spec in criteria_specs:
        _add_mission_criteria_from_spec(db, user_id=user_id, mission=mission, criteria_spec=criteria_spec)
    if status == "active":
        hypothesis.status = "mission_active"
    elif status == "draft":
        hypothesis.status = "mission_draft"
    db.flush()
    return mission


def create_draft_coach_mission(
    db: Session,
    *,
    user_id: int,
    hypothesis_id: int,
    title: str,
    focus: str | None = None,
    source_payload: Mapping[str, Any] | None = None,
) -> CoachMission:
    return activate_coach_mission(
        db,
        user_id=user_id,
        hypothesis_id=hypothesis_id,
        title=title,
        focus=focus,
        status="draft",
        source_payload=source_payload,
    )


def activate_draft_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
) -> CoachMission:
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    if mission.status == "active":
        return mission
    if mission.status not in {"draft", "paused"}:
        raise ValueError(f"Cannot activate mission from status: {mission.status}")
    hypothesis = _require_mission_hypothesis(db, mission)
    criteria_specs = _criteria_specs_from_hypothesis(hypothesis)
    _validate_hypothesis_can_activate(hypothesis, criteria_specs)
    if not list_mission_criteria(db, user_id=user_id, mission_id=mission.id):
        for criteria_spec in criteria_specs:
            _add_mission_criteria_from_spec(db, user_id=user_id, mission=mission, criteria_spec=criteria_spec)
    mission.status = "active"
    mission.ended_at = None
    hypothesis.status = "mission_active"
    db.flush()
    return mission


def get_coach_mission(db: Session, *, user_id: int, mission_id: int) -> CoachMission | None:
    return db.scalar(select(CoachMission).where(CoachMission.id == mission_id).where(CoachMission.user_id == user_id))


def list_coach_missions(db: Session, *, user_id: int, status: str | None = None) -> list[CoachMission]:
    stmt = (
        select(CoachMission)
        .where(CoachMission.user_id == user_id)
        .order_by(CoachMission.activated_at.desc(), CoachMission.id.desc())
    )
    if status is not None:
        stmt = stmt.where(CoachMission.status == status)
    return list(db.scalars(stmt).all())


def list_active_coach_missions(db: Session, *, user_id: int) -> list[CoachMission]:
    return list_coach_missions(db, user_id=user_id, status="active")


def update_coach_mission_status(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    status: str,
    ended_at: datetime | None = None,
) -> CoachMission:
    if status not in MISSION_STATUSES:
        raise ValueError(f"Unsupported mission status: {status}")
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    mission.status = status
    mission.ended_at = ended_at
    db.flush()
    return mission


def pause_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
) -> CoachMission:
    return update_coach_mission_status(db, user_id=user_id, mission_id=mission_id, status="paused")


def cancel_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    ended_at: datetime | None = None,
) -> CoachMission:
    return update_coach_mission_status(
        db,
        user_id=user_id,
        mission_id=mission_id,
        status="cancelled",
        ended_at=ended_at or datetime.now(UTC),
    )


def add_mission_criteria(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    metric_name: str,
    role: str,
    direction: str,
    baseline_value: float | None = None,
    target_value: float | None = None,
    min_sample_matches: int | None = None,
    min_sample_rounds: int | None = None,
    confidence_required: float | None = None,
    rule: Mapping[str, Any] | None = None,
) -> MissionCriteria:
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    if role not in CRITERIA_ROLES:
        raise ValueError(f"Unsupported mission criteria role: {role}")
    if direction not in CRITERIA_DIRECTIONS:
        raise ValueError(f"Unsupported mission criteria direction: {direction}")
    criteria = MissionCriteria(
        mission_id=mission.id,
        user_id=user_id,
        owner_steam_id=mission.owner_steam_id,
        metric_name=metric_name,
        role=role,
        direction=direction,
        baseline_value=baseline_value,
        target_value=target_value,
        min_sample_matches=min_sample_matches,
        min_sample_rounds=min_sample_rounds,
        confidence_required=confidence_required,
        rule_json=_json_object(rule or {}),
    )
    db.add(criteria)
    db.flush()
    return criteria


def list_mission_criteria(db: Session, *, user_id: int, mission_id: int) -> list[MissionCriteria]:
    _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    return list(
        db.scalars(
            select(MissionCriteria)
            .where(MissionCriteria.mission_id == mission_id)
            .where(MissionCriteria.user_id == user_id)
            .order_by(MissionCriteria.id.asc())
        ).all()
    )


def record_mission_progress_evaluation(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    status: str,
    evaluation_window_start: datetime | None = None,
    evaluation_window_end: datetime | None = None,
    result: Mapping[str, Any] | None = None,
    confidence: float | None = None,
    caveats: Sequence[Any] | None = None,
) -> MissionProgressEvaluation:
    if status not in MISSION_PROGRESS_STATUSES:
        raise ValueError(f"Unsupported mission progress status: {status}")
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    evaluation = MissionProgressEvaluation(
        mission_id=mission.id,
        user_id=user_id,
        owner_steam_id=mission.owner_steam_id,
        evaluation_window_start=evaluation_window_start,
        evaluation_window_end=evaluation_window_end,
        status=status,
        result_json=_json_object(result or {}),
        confidence=confidence,
        caveats_json=_json_list(caveats or []),
    )
    db.add(evaluation)
    db.flush()
    return evaluation


def list_mission_progress_evaluations(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
) -> list[MissionProgressEvaluation]:
    _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    return list(
        db.scalars(
            select(MissionProgressEvaluation)
            .where(MissionProgressEvaluation.mission_id == mission_id)
            .where(MissionProgressEvaluation.user_id == user_id)
            .order_by(MissionProgressEvaluation.created_at.desc(), MissionProgressEvaluation.id.desc())
        ).all()
    )


def _require_owned_analysis_run(db: Session, *, user_id: int, analysis_run_id: int) -> AnalysisRun:
    run = db.get(AnalysisRun, analysis_run_id)
    if run is None:
        raise ValueError(f"Analysis run does not exist: {analysis_run_id}")
    if run.user_id != user_id:
        raise PermissionError("Analysis run belongs to a different user.")
    return run


def _require_owned_hypothesis(db: Session, *, user_id: int, hypothesis_id: int) -> CoachHypothesis:
    hypothesis = db.get(CoachHypothesis, hypothesis_id)
    if hypothesis is None:
        raise ValueError(f"Coach hypothesis does not exist: {hypothesis_id}")
    if hypothesis.user_id != user_id:
        raise PermissionError("Coach hypothesis belongs to a different user.")
    return hypothesis


def _require_owned_mission(db: Session, *, user_id: int, mission_id: int) -> CoachMission:
    mission = db.get(CoachMission, mission_id)
    if mission is None:
        raise ValueError(f"Coach mission does not exist: {mission_id}")
    if mission.user_id != user_id:
        raise PermissionError("Coach mission belongs to a different user.")
    return mission


def _require_mission_hypothesis(db: Session, mission: CoachMission) -> CoachHypothesis:
    if mission.hypothesis_id is None:
        raise ValueError(f"Coach mission has no source hypothesis: {mission.id}")
    hypothesis = db.get(CoachHypothesis, mission.hypothesis_id)
    if hypothesis is None:
        raise ValueError(f"Coach mission source hypothesis does not exist: {mission.hypothesis_id}")
    if hypothesis.user_id != mission.user_id:
        raise PermissionError("Coach mission source hypothesis belongs to a different user.")
    return hypothesis


def _validate_hypothesis_can_activate(
    hypothesis: CoachHypothesis,
    criteria_specs: Sequence[Mapping[str, Any]],
) -> None:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    confidence_eligibility = readiness.get("confidence_eligibility")
    confidence_level = (
        _optional_lower_str(confidence_eligibility.get("level"))
        if isinstance(confidence_eligibility, Mapping)
        else None
    )
    blocking_reasons = _string_sequence(readiness.get("blocking_reason_codes"))
    if readiness.get("can_become_mission") is not True:
        reason = ",".join(blocking_reasons) or "mission_readiness_not_eligible"
        raise ValueError(f"Coach hypothesis cannot become an active mission: {reason}")
    if confidence_level not in MISSION_ELIGIBLE_CONFIDENCE_LEVELS:
        raise ValueError("Coach hypothesis cannot become an active mission: low_or_unavailable_confidence")
    if isinstance(confidence_eligibility, Mapping):
        if confidence_eligibility.get("usable_for_missions") is not True:
            raise ValueError("Coach hypothesis cannot become an active mission: confidence_not_mission_eligible")
        if confidence_eligibility.get("hard_recommendation_eligible") is not True:
            raise ValueError(
                "Coach hypothesis cannot become an active mission: metric_not_hard_recommendation_eligible"
            )
    if not criteria_specs:
        raise ValueError("Coach hypothesis cannot become an active mission: missing_mission_criteria")


def _mission_source_payload(
    hypothesis: CoachHypothesis,
    source_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(source_payload or {})
    payload.update(
        {
            "source_hypothesis_id": hypothesis.id,
            "analysis_run_id": hypothesis.analysis_run_id,
            "baseline_source": "coach_hypothesis_mission_readiness",
            "mission_readiness": _json_load_mapping(hypothesis.mission_readiness_json),
        }
    )
    return payload


def _criteria_specs_from_hypothesis(hypothesis: CoachHypothesis) -> list[dict[str, Any]]:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    explicit = readiness.get("criteria") or readiness.get("mission_criteria")
    if isinstance(explicit, Sequence) and not isinstance(explicit, str):
        return [_normalize_criteria_spec(item) for item in explicit if isinstance(item, Mapping)]
    evidence = _json_load_sequence(hypothesis.evidence_json)
    first_evidence = evidence[0] if evidence and isinstance(evidence[0], Mapping) else {}
    primary_metric = _readiness_target_metric(readiness, hypothesis) or _evidence_metric_name(first_evidence)
    baseline = _optional_number(readiness.get("baseline_value"))
    if baseline is None and evidence:
        baseline = _optional_number(evidence[0].get("value")) if isinstance(evidence[0], Mapping) else None
    if not primary_metric:
        return []

    direction = _default_metric_direction(primary_metric)
    primary = {
        "metric_name": primary_metric,
        "role": "primary",
        "direction": direction,
        "baseline_value": baseline,
        "target_value": _target_value(primary_metric, baseline, direction),
        "confidence_required": _confidence_required(readiness),
        "rule": {
            "source": "mission_readiness",
            "target_source": "mission_readiness_or_default",
            "blocking_reason_codes": _string_sequence(readiness.get("blocking_reason_codes")),
        },
    }
    specs = [_normalize_criteria_spec(primary)]

    for item in evidence[1:]:
        if not isinstance(item, Mapping):
            continue
        metric_name = _evidence_metric_name(item)
        baseline_value = _optional_number(item.get("value"))
        if not metric_name or metric_name == primary_metric or baseline_value is None:
            continue
        secondary_direction = _default_metric_direction(metric_name)
        specs.append(
            _normalize_criteria_spec(
                {
                    "metric_name": metric_name,
                    "role": "secondary",
                    "direction": secondary_direction,
                    "baseline_value": baseline_value,
                    "target_value": _target_value(metric_name, baseline_value, secondary_direction),
                    "confidence_required": _confidence_required(readiness),
                    "rule": {"source": "supporting_evidence"},
                }
            )
        )

    if baseline is not None:
        guardrail_direction = "stay_below" if direction == "lower_is_better" else "stay_above"
        specs.append(
            _normalize_criteria_spec(
                {
                    "metric_name": primary_metric,
                    "role": "guardrail",
                    "direction": guardrail_direction,
                    "baseline_value": baseline,
                    "target_value": baseline,
                    "confidence_required": _confidence_required(readiness),
                    "rule": {
                        "source": "baseline_regression_guardrail",
                        "baseline_comparison": "do_not_regress_from_activation_baseline",
                    },
                }
            )
        )
    return specs


def _add_mission_criteria_from_spec(
    db: Session,
    *,
    user_id: int,
    mission: CoachMission,
    criteria_spec: Mapping[str, Any],
) -> MissionCriteria:
    return add_mission_criteria(
        db,
        user_id=user_id,
        mission_id=mission.id,
        metric_name=str(criteria_spec["metric_name"]),
        role=str(criteria_spec["role"]),
        direction=str(criteria_spec["direction"]),
        baseline_value=_optional_number(criteria_spec.get("baseline_value")),
        target_value=_optional_number(criteria_spec.get("target_value")),
        min_sample_matches=_optional_int(criteria_spec.get("min_sample_matches")),
        min_sample_rounds=_optional_int(criteria_spec.get("min_sample_rounds")),
        confidence_required=_optional_number(criteria_spec.get("confidence_required")),
        rule=_mapping(criteria_spec.get("rule")),
    )


def _normalize_criteria_spec(value: Mapping[str, Any]) -> dict[str, Any]:
    metric_name = str(value.get("metric_name") or value.get("metric_id") or "").strip()
    role = str(value.get("role") or "primary").strip()
    direction = str(value.get("direction") or _default_metric_direction(metric_name)).strip()
    if not metric_name:
        raise ValueError("Mission criteria requires metric_name")
    if role not in CRITERIA_ROLES:
        raise ValueError(f"Unsupported mission criteria role: {role}")
    if direction not in CRITERIA_DIRECTIONS:
        raise ValueError(f"Unsupported mission criteria direction: {direction}")
    return {
        "metric_name": metric_name,
        "role": role,
        "direction": direction,
        "baseline_value": _optional_number(value.get("baseline_value")),
        "target_value": _optional_number(value.get("target_value")),
        "min_sample_matches": _optional_int(value.get("min_sample_matches")),
        "min_sample_rounds": _optional_int(value.get("min_sample_rounds")),
        "confidence_required": _optional_number(value.get("confidence_required")),
        "rule": _mapping(value.get("rule")),
    }


def _readiness_target_metric(readiness: Mapping[str, Any], hypothesis: CoachHypothesis) -> str | None:
    target = readiness.get("target_metric_candidate")
    if target:
        return str(target)
    candidates = readiness.get("target_metric_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, str):
        candidates = _json_load_sequence(hypothesis.target_metric_candidates_json)
    for item in candidates:
        if item:
            return str(item)
    return None


def _evidence_metric_name(evidence: Mapping[str, Any]) -> str | None:
    metric_name = evidence.get("metric_name") or evidence.get("metric_id")
    return str(metric_name) if metric_name else None


def _default_metric_direction(metric_name: str) -> str:
    lower_is_better = {
        "opening_death_rate",
        "untraded_death_rate",
        "death_rate",
        "deaths",
        "ambiguous_traded_deaths",
    }
    if metric_name in lower_is_better:
        return "lower_is_better"
    return "higher_is_better"


def _target_value(metric_name: str, baseline: float | None, direction: str) -> float | None:
    if baseline is None:
        return None
    if direction == "lower_is_better":
        if metric_name.endswith("_rate"):
            return round(max(0.0, baseline - 0.05), 3)
        return round(max(0.0, baseline * 0.9), 3)
    if direction == "higher_is_better":
        if metric_name.endswith("_rate"):
            return round(min(1.0, baseline + 0.05), 3)
        return round(baseline * 1.1, 3)
    return baseline


def _confidence_required(readiness: Mapping[str, Any]) -> float:
    confidence_eligibility = readiness.get("confidence_eligibility")
    level = (
        _optional_lower_str(confidence_eligibility.get("level"))
        if isinstance(confidence_eligibility, Mapping)
        else None
    )
    if level == "high":
        return INSIGHT_CONFIDENCE_SCORES["high"]
    return INSIGHT_CONFIDENCE_SCORES["medium"]


def _mission_readiness(insight_card: Mapping[str, Any]) -> Any:
    return insight_card.get("mission_readiness") or insight_card.get("mission_readiness_metadata") or {}


def _target_metric_candidates(insight_card: Mapping[str, Any]) -> Any:
    if "target_metric_candidates" in insight_card:
        return insight_card["target_metric_candidates"]
    mission_readiness = _mission_readiness(insight_card)
    if isinstance(mission_readiness, Mapping):
        if "target_metric_candidates" in mission_readiness:
            return mission_readiness["target_metric_candidates"]
        if "target_metrics" in mission_readiness:
            return mission_readiness["target_metrics"]
    if "target_metrics" in insight_card:
        return insight_card["target_metrics"]
    return []


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in INSIGHT_CONFIDENCE_SCORES:
            return INSIGHT_CONFIDENCE_SCORES[normalized]
    return float(value)


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_lower_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_object(value: Mapping[str, Any]) -> str:
    return _json_any(dict(value))


def _json_list(value: Sequence[Any]) -> str:
    return _json_any(list(value))


def _json_any(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _json_load_mapping(value: str) -> dict[str, Any]:
    loaded = json.loads(value)
    return dict(loaded) if isinstance(loaded, Mapping) else {}


def _json_load_sequence(value: str) -> list[Any]:
    loaded = json.loads(value)
    return list(loaded) if isinstance(loaded, list) else []


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_sequence(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [str(item) for item in value]
