from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
MISSION_PAYLOAD_SCHEMA_VERSION = "coach-mission-payload-v1"
REQUIRED_MISSION_PAYLOAD_FIELDS = ("title", "goal", "rules", "duration", "success_metric", "failure_condition")
SURVIVAL_OPENING_MISSION_METRICS = {"opening_death_rate", "survival_rate"}
BAD_FIGHT_TRADE_MISSION_METRICS = {"untraded_death_rate"}


@dataclass(frozen=True)
class MissionPayload:
    title: str
    goal: str
    rules: tuple[str, ...]
    duration: dict[str, Any]
    success_metric: dict[str, Any]
    failure_condition: dict[str, Any]
    linked_insight: dict[str, Any]
    schema_version: str = MISSION_PAYLOAD_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "goal": self.goal,
            "rules": list(self.rules),
            "duration": dict(self.duration),
            "success_metric": dict(self.success_metric),
            "failure_condition": dict(self.failure_condition),
            "linked_insight": dict(self.linked_insight),
        }


@dataclass(frozen=True)
class MissionPayloadValidationIssue:
    code: str
    message: str
    path: str


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
    mission_payload = mission_payload_from_hypothesis(hypothesis, title=title)
    if status == "active" and mission_payload is None:
        raise ValueError("Coach hypothesis cannot become an active mission: missing_mission_payload")
    mission = CoachMission(
        hypothesis_id=hypothesis.id,
        user_id=user_id,
        owner_steam_id=hypothesis.owner_steam_id,
        status=status,
        title=title,
        focus=focus if focus is not None else hypothesis.recommended_focus,
        source_payload_json=_json_object(_mission_source_payload(hypothesis, source_payload, mission_payload)),
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
    mission_payload = mission_payload_from_hypothesis(hypothesis, title=mission.title)
    if mission_payload is None:
        raise ValueError("Coach hypothesis cannot become an active mission: missing_mission_payload")
    if not list_mission_criteria(db, user_id=user_id, mission_id=mission.id):
        for criteria_spec in criteria_specs:
            _add_mission_criteria_from_spec(db, user_id=user_id, mission=mission, criteria_spec=criteria_spec)
    mission.status = "active"
    mission.ended_at = None
    source_payload = _json_load_mapping(mission.source_payload_json)
    source_payload["mission_payload"] = mission_payload
    mission.source_payload_json = _json_object(source_payload)
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


def evaluate_mission_progress(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    baseline_metric_snapshots: Sequence[Any] | None = None,
    evaluation_metric_snapshots: Sequence[Any],
    evaluation_window_start: datetime | None = None,
    evaluation_window_end: datetime | None = None,
    evaluation_window: Mapping[str, Any] | None = None,
) -> MissionProgressEvaluation:
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    if mission.status != "active":
        raise ValueError(f"Cannot evaluate mission progress from status: {mission.status}")
    criteria_rows = list_mission_criteria(db, user_id=user_id, mission_id=mission.id)
    baseline_window = (
        _metric_snapshot_window(mission, baseline_metric_snapshots)
        if baseline_metric_snapshots is not None
        else None
    )
    snapshot_window = _metric_snapshot_window(mission, evaluation_metric_snapshots)
    components = [
        _evaluate_criteria(criteria, snapshot_window, baseline_window=baseline_window)
        for criteria in criteria_rows
    ]
    status = _composite_progress_status(components)
    caveats = _evaluation_caveats(snapshot_window, components)
    snapshot_comparison = _snapshot_comparison(
        mission=mission,
        baseline_window=baseline_window,
        evaluation_window=snapshot_window,
        components=components,
    )
    window_payload = {
        "start": evaluation_window_start.isoformat() if evaluation_window_start else None,
        "end": evaluation_window_end.isoformat() if evaluation_window_end else None,
        "snapshot_ids": snapshot_window["snapshot_ids"],
        "snapshot_count": snapshot_window["snapshot_count"],
        "sample_matches": snapshot_window["sample_matches"],
        "sample_rounds": snapshot_window["sample_rounds"],
    }
    if evaluation_window:
        window_payload.update(dict(evaluation_window))
    result = {
        "mission_id": mission.id,
        "owner_steam_id": mission.owner_steam_id,
        "status": status,
        "evaluation_window_json": window_payload,
        "components": components,
        "component_metrics": {
            component["metric_name"]: component
            for component in components
        },
        "snapshot_comparison": snapshot_comparison,
        "source_metric_snapshot_ids": snapshot_window["snapshot_ids"],
        "target_met": _target_met(components),
        "progress_explanation": _progress_explanation(status, snapshot_comparison, caveats),
    }
    return record_mission_progress_evaluation(
        db,
        user_id=user_id,
        mission_id=mission.id,
        status=status,
        evaluation_window_start=evaluation_window_start,
        evaluation_window_end=evaluation_window_end,
        result=result,
        confidence=_evaluation_confidence(snapshot_window, components),
        caveats=caveats,
    )


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


def serialize_mission_progress_evaluation(evaluation: MissionProgressEvaluation) -> dict[str, Any]:
    result = _json_load_mapping(evaluation.result_json)
    components = [
        dict(component)
        for component in result.get("components", [])
        if isinstance(component, Mapping)
    ]
    primary = next((component for component in components if component.get("role") == "primary"), None)
    guardrails = [component for component in components if component.get("role") == "guardrail"]
    secondaries = [component for component in components if component.get("role") == "secondary"]
    target_met = result.get("target_met") is True
    counted_reason = _mission_count_reason(evaluation.status, components, target_met)
    return {
        "evaluation_id": evaluation.id,
        "mission_id": evaluation.mission_id,
        "owner_steam_id": evaluation.owner_steam_id,
        "evaluated_window": result.get("evaluation_window_json") or {},
        "source_metric_snapshot_ids": _int_list(result.get("source_metric_snapshot_ids")),
        "status": evaluation.status,
        "confidence": evaluation.confidence,
        "caveats": _json_load_sequence(evaluation.caveats_json),
        "primary_metric_result": _component_summary(primary),
        "secondary_metric_results": [_component_summary(component) for component in secondaries],
        "guardrail_results": [_component_summary(component) for component in guardrails],
        "snapshot_comparison": result.get("snapshot_comparison") or {},
        "target_met": target_met,
        "counted": target_met,
        "why_counted_or_not": counted_reason,
        "progress_explanation": result.get("progress_explanation")
        or _progress_explanation(
            evaluation.status,
            result.get("snapshot_comparison") or {},
            _json_load_sequence(evaluation.caveats_json),
        ),
    }


def mission_payload_from_insight_card(
    insight_card: Mapping[str, Any],
    *,
    title: str | None = None,
    duration: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    readiness = _mapping(_mission_readiness(insight_card))
    if readiness.get("can_become_mission") is not True:
        return None
    criteria_specs = _criteria_specs_from_insight_card(insight_card)
    if not criteria_specs:
        return None
    return _mission_payload_from_parts(
        title=title or _mission_title(
            problem=str(insight_card.get("problem") or ""),
            primary_metric=str(criteria_specs[0]["metric_name"]),
        ),
        problem=str(insight_card.get("problem") or ""),
        recommended_focus=str(insight_card.get("recommended_focus") or ""),
        caveats=_string_sequence(insight_card.get("caveats")),
        readiness=readiness,
        criteria_specs=criteria_specs,
        duration=duration,
        linked_insight={
            "source_insight_card_id": _optional_str(insight_card.get("id") or insight_card.get("card_id")),
            "source": "insight_card",
        },
    )


def mission_payload_from_hypothesis(
    hypothesis: CoachHypothesis,
    *,
    title: str | None = None,
    duration: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    if readiness.get("can_become_mission") is not True:
        return None
    criteria_specs = _criteria_specs_from_hypothesis(hypothesis)
    if not criteria_specs:
        return None
    return _mission_payload_from_parts(
        title=title or _mission_title(problem=hypothesis.problem, primary_metric=str(criteria_specs[0]["metric_name"])),
        problem=hypothesis.problem,
        recommended_focus=hypothesis.recommended_focus,
        caveats=_json_load_sequence(hypothesis.caveats_json),
        readiness=readiness,
        criteria_specs=criteria_specs,
        duration=duration,
        linked_insight={
            "source_hypothesis_id": hypothesis.id,
            "source_insight_card_id": hypothesis.source_insight_card_id,
            "analysis_run_id": hypothesis.analysis_run_id,
            "source": "coach_hypothesis",
        },
    )


def validate_mission_payload(
    raw_payload: Any,
    *,
    path: str = "$.mission_payload",
) -> tuple[MissionPayloadValidationIssue, ...]:
    if not isinstance(raw_payload, Mapping):
        return (
            MissionPayloadValidationIssue(
                "invalid_mission_payload",
                "Mission payload must be an object.",
                path,
            ),
        )
    payload = dict(raw_payload)
    issues: list[MissionPayloadValidationIssue] = []
    for field in REQUIRED_MISSION_PAYLOAD_FIELDS:
        if field not in payload:
            issues.append(
                MissionPayloadValidationIssue(
                    "missing_mission_payload_field",
                    f"Missing required mission payload field: {field}.",
                    f"{path}.{field}",
                )
            )
    _validate_payload_non_empty_string(payload, "title", path, issues)
    _validate_payload_non_empty_string(payload, "goal", path, issues)
    _validate_mission_rules(payload.get("rules"), path, issues)
    _validate_mission_duration(payload.get("duration"), path, issues)
    _validate_mission_success_metric(payload.get("success_metric"), path, issues)
    _validate_mission_failure_condition(payload.get("failure_condition"), path, issues)
    linked_insight = payload.get("linked_insight")
    if linked_insight is not None and not isinstance(linked_insight, Mapping):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_linked_insight",
                "Mission linked_insight must be an object when present.",
                f"{path}.linked_insight",
            )
        )
    return tuple(issues)


def serialize_mission_payload(raw_payload: Any) -> dict[str, Any]:
    if validate_mission_payload(raw_payload):
        return {}
    payload = dict(raw_payload)
    return MissionPayload(
        title=str(payload["title"]).strip(),
        goal=str(payload["goal"]).strip(),
        rules=tuple(str(rule).strip() for rule in payload["rules"]),
        duration=dict(payload["duration"]),
        success_metric=dict(payload["success_metric"]),
        failure_condition=dict(payload["failure_condition"]),
        linked_insight=dict(payload.get("linked_insight") or {}),
        schema_version=str(payload.get("schema_version") or MISSION_PAYLOAD_SCHEMA_VERSION),
    ).to_dict()


def serialize_coach_mission(mission: CoachMission) -> dict[str, Any]:
    source_payload = _json_load_mapping(mission.source_payload_json)
    return {
        "mission_id": mission.id,
        "hypothesis_id": mission.hypothesis_id,
        "user_id": mission.user_id,
        "owner_steam_id": mission.owner_steam_id,
        "status": mission.status,
        "title": mission.title,
        "focus": mission.focus,
        "mission_payload": serialize_mission_payload(source_payload.get("mission_payload")),
        "source_payload": source_payload,
        "activated_at": mission.activated_at.isoformat() if mission.activated_at else None,
        "ended_at": mission.ended_at.isoformat() if mission.ended_at else None,
    }


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


def _metric_snapshot_window(
    mission: CoachMission,
    evaluation_metric_snapshots: Sequence[Any],
) -> dict[str, Any]:
    metrics: dict[str, list[float]] = {}
    caveats: list[str] = []
    confidence_values: list[float] = []
    snapshot_ids: list[int] = []
    sample_matches = 0
    sample_rounds = 0
    for raw_snapshot in evaluation_metric_snapshots:
        snapshot = _snapshot_to_mapping(raw_snapshot)
        _validate_snapshot_owner(mission, snapshot)
        snapshot_id = _optional_int(snapshot.get("id"))
        if snapshot_id is not None:
            snapshot_ids.append(snapshot_id)
        metric_payload = _snapshot_payload_mapping(snapshot, "metrics", "metrics_json")
        for metric_name, raw_value in metric_payload.items():
            value = _metric_numeric_value(raw_value)
            if value is not None:
                metrics.setdefault(str(metric_name), []).append(value)
        confidence = _snapshot_confidence(snapshot)
        if confidence is not None:
            confidence_values.append(confidence)
        caveats.extend(_snapshot_caveats(snapshot))
        sample_matches += _sample_count(snapshot, "matches")
        sample_rounds += _sample_count(snapshot, "rounds")
    if evaluation_metric_snapshots and sample_matches == 0:
        sample_matches = len(evaluation_metric_snapshots)
    return {
        "metrics": {
            metric_name: sum(values) / len(values)
            for metric_name, values in metrics.items()
        },
        "snapshot_ids": snapshot_ids,
        "snapshot_count": len(evaluation_metric_snapshots),
        "sample_matches": sample_matches,
        "sample_rounds": sample_rounds,
        "confidence": min(confidence_values) if confidence_values else None,
        "caveats": caveats,
    }


def _evaluate_criteria(
    criteria: MissionCriteria,
    snapshot_window: Mapping[str, Any],
    *,
    baseline_window: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = _mapping(snapshot_window.get("metrics"))
    baseline_metrics = _mapping(baseline_window.get("metrics")) if baseline_window is not None else {}
    baseline_from_snapshot = (
        _optional_number(baseline_metrics.get(criteria.metric_name))
        if criteria.metric_name in baseline_metrics
        else None
    )
    baseline = baseline_from_snapshot if baseline_window is not None else criteria.baseline_value
    rule = _json_load_mapping(criteria.rule_json)
    component = {
        "criteria_id": criteria.id,
        "metric_name": criteria.metric_name,
        "role": criteria.role,
        "direction": criteria.direction,
        "baseline_value": baseline,
        "baseline_source": "metric_snapshots" if baseline_window is not None else "mission_activation",
        "baseline_metric_snapshot_ids": list(baseline_window.get("snapshot_ids") or [])
        if baseline_window is not None
        else [],
        "target_value": criteria.target_value,
        "observed_value": _optional_number(metrics.get(criteria.metric_name))
        if criteria.metric_name in metrics
        else None,
        "delta": None,
        "outcome": "insufficient_data",
        "reason_codes": [],
        "sample_matches": snapshot_window.get("sample_matches"),
        "sample_rounds": snapshot_window.get("sample_rounds"),
        "confidence": snapshot_window.get("confidence"),
        "rule": rule,
    }
    sample_reason = _insufficient_sample_reason(criteria, snapshot_window)
    confidence_reason = _insufficient_confidence_reason(criteria, snapshot_window)
    if criteria.metric_name not in metrics:
        component["reason_codes"].append("missing_metric")
        return component
    if baseline_window is not None and criteria.metric_name not in baseline_metrics:
        component["reason_codes"].append("missing_baseline_metric")
        return component
    if sample_reason:
        component["reason_codes"].append(sample_reason)
        return component
    if confidence_reason:
        component["reason_codes"].append(confidence_reason)
        return component

    follow_outcome = _not_following_outcome(rule, metrics)
    if follow_outcome is not None:
        component["outcome"] = follow_outcome
        component["reason_codes"].append(follow_outcome)
        return component

    observed = _optional_number(metrics.get(criteria.metric_name))
    if observed is not None and baseline is not None:
        component["delta"] = observed - baseline
    component["outcome"] = _directional_outcome(
        metric_name=criteria.metric_name,
        direction=criteria.direction,
        observed=observed,
        baseline=baseline,
        target=criteria.target_value,
        rule=rule,
    )
    component["target_reached"] = _target_reached(
        direction=criteria.direction,
        observed=observed,
        target=criteria.target_value,
        rule=rule,
    )
    component["reason_codes"].append(component["outcome"])
    return component


def _composite_progress_status(components: Sequence[Mapping[str, Any]]) -> str:
    if not components:
        return "insufficient_data"
    guardrail_outcomes = [
        component.get("outcome")
        for component in components
        if component.get("role") == "guardrail"
    ]
    if any(outcome == "regressing" for outcome in guardrail_outcomes):
        return "regressing"
    if any(outcome == "not_following" for outcome in guardrail_outcomes):
        return "not_following"
    outcomes = [str(component.get("outcome")) for component in components]
    if "insufficient_data" in outcomes:
        return "insufficient_data"
    if "not_following" in outcomes:
        return "not_following"
    if "regressing" in outcomes:
        return "regressing"
    if "improving" in outcomes:
        return "improving"
    return "unchanged"


def _directional_outcome(
    *,
    metric_name: str,
    direction: str,
    observed: float | None,
    baseline: float | None,
    target: float | None,
    rule: Mapping[str, Any],
) -> str:
    if observed is None or baseline is None:
        return "insufficient_data"
    if direction == "lower_is_better":
        return _compare_lower_is_better(observed, baseline)
    if direction == "higher_is_better":
        return _compare_higher_is_better(observed, baseline)
    if direction == "improve_or_same":
        metric_direction = str(rule.get("metric_direction") or _default_metric_direction(metric_name))
        if metric_direction == "lower_is_better":
            return _compare_lower_is_better(observed, baseline, unchanged_when_better=False)
        return _compare_higher_is_better(observed, baseline, unchanged_when_better=False)
    if direction == "not_drop_more_than":
        max_drop = _max_drop(rule, baseline, target)
        return "regressing" if observed < baseline - max_drop else "unchanged"
    if direction == "stay_above":
        floor = target if target is not None else baseline
        return "regressing" if observed < floor else "unchanged"
    if direction == "stay_below":
        ceiling = target if target is not None else baseline
        return "regressing" if observed > ceiling else "unchanged"
    return "insufficient_data"


def _compare_lower_is_better(
    observed: float,
    baseline: float,
    *,
    unchanged_when_better: bool = False,
) -> str:
    if observed < baseline:
        return "unchanged" if unchanged_when_better else "improving"
    if observed > baseline:
        return "regressing"
    return "unchanged"


def _compare_higher_is_better(
    observed: float,
    baseline: float,
    *,
    unchanged_when_better: bool = False,
) -> str:
    if observed > baseline:
        return "unchanged" if unchanged_when_better else "improving"
    if observed < baseline:
        return "regressing"
    return "unchanged"


def _target_reached(
    *,
    direction: str,
    observed: float | None,
    target: float | None,
    rule: Mapping[str, Any],
) -> bool | None:
    if observed is None or target is None:
        return None
    if direction in {"higher_is_better", "stay_above", "improve_or_same"}:
        return observed >= target
    if direction in {"lower_is_better", "stay_below"}:
        return observed <= target
    if direction == "not_drop_more_than":
        return observed >= target
    return None


def _target_met(components: Sequence[Mapping[str, Any]]) -> bool:
    progress_components = [
        component
        for component in components
        if component.get("role") in {"primary", "secondary"}
    ]
    if not progress_components:
        return False
    if not all(component.get("target_reached") is True for component in progress_components):
        return False
    return not any(
        component.get("role") == "guardrail" and component.get("outcome") in {"regressing", "not_following"}
        for component in components
    )


def _not_following_outcome(rule: Mapping[str, Any], metrics: Mapping[str, Any]) -> str | None:
    not_following_if = rule.get("not_following_if")
    if isinstance(not_following_if, Mapping) and _rule_condition_matches(not_following_if, metrics) is True:
        return "not_following"
    follow_rule = rule.get("follow_rule")
    if isinstance(follow_rule, Mapping):
        followed = _rule_condition_matches(follow_rule, metrics)
        if followed is None:
            return "insufficient_data"
        if followed is False:
            return "not_following"
    return None


def _rule_condition_matches(condition: Mapping[str, Any], metrics: Mapping[str, Any]) -> bool | None:
    metric_name = condition.get("metric_name") or condition.get("metric")
    if not metric_name or metric_name not in metrics:
        return None
    observed = _optional_number(metrics.get(str(metric_name)))
    expected = _optional_number(condition.get("value"))
    if observed is None or expected is None:
        return None
    operator = str(condition.get("operator") or ">=")
    if operator == ">=":
        return observed >= expected
    if operator == ">":
        return observed > expected
    if operator == "<=":
        return observed <= expected
    if operator == "<":
        return observed < expected
    if operator == "==":
        return observed == expected
    if operator == "!=":
        return observed != expected
    raise ValueError(f"Unsupported mission rule operator: {operator}")


def _insufficient_sample_reason(
    criteria: MissionCriteria,
    snapshot_window: Mapping[str, Any],
) -> str | None:
    sample_matches = _optional_int(snapshot_window.get("sample_matches")) or 0
    sample_rounds = _optional_int(snapshot_window.get("sample_rounds")) or 0
    if criteria.min_sample_matches is not None and sample_matches < criteria.min_sample_matches:
        return "insufficient_sample_matches"
    if criteria.min_sample_rounds is not None and sample_rounds < criteria.min_sample_rounds:
        return "insufficient_sample_rounds"
    return None


def _insufficient_confidence_reason(
    criteria: MissionCriteria,
    snapshot_window: Mapping[str, Any],
) -> str | None:
    if criteria.confidence_required is None:
        return None
    confidence = _optional_number(snapshot_window.get("confidence"))
    if confidence is None:
        return "missing_confidence"
    if confidence < criteria.confidence_required:
        return "insufficient_confidence"
    return None


def _evaluation_confidence(
    snapshot_window: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
) -> float | None:
    confidence = _optional_number(snapshot_window.get("confidence"))
    if confidence is None:
        return None
    if any(component.get("outcome") == "insufficient_data" for component in components):
        return min(confidence, 0.25)
    return confidence


def _evaluation_caveats(
    snapshot_window: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
) -> list[str]:
    caveats = [str(caveat) for caveat in snapshot_window.get("caveats") or []]
    for component in components:
        for reason in component.get("reason_codes") or []:
            if reason in {
                "missing_metric",
                "missing_baseline_metric",
                "insufficient_sample_matches",
                "insufficient_sample_rounds",
                "missing_confidence",
                "insufficient_confidence",
                "not_following",
            }:
                caveats.append(f"{component.get('metric_name')}:{reason}")
    return sorted(set(caveats))


def _component_summary(component: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if component is None:
        return None
    return {
        "criteria_id": component.get("criteria_id"),
        "metric_name": component.get("metric_name"),
        "role": component.get("role"),
        "direction": component.get("direction"),
        "baseline_value": component.get("baseline_value"),
        "baseline_source": component.get("baseline_source"),
        "baseline_metric_snapshot_ids": list(component.get("baseline_metric_snapshot_ids") or []),
        "evaluation_value": component.get("observed_value"),
        "delta": component.get("delta"),
        "target_value": component.get("target_value"),
        "outcome": component.get("outcome"),
        "target_reached": component.get("target_reached"),
        "reason_codes": list(component.get("reason_codes") or []),
        "sample_matches": component.get("sample_matches"),
        "sample_rounds": component.get("sample_rounds"),
        "confidence": component.get("confidence"),
    }


def _mission_count_reason(status: str, components: Sequence[Mapping[str, Any]], target_met: bool) -> str:
    if target_met:
        return "Primary and secondary mission targets were reached without failing guardrails."
    blocking = [
        f"{component.get('metric_name')}:{component.get('outcome')}"
        for component in components
        if component.get("outcome") in {"regressing", "insufficient_data", "not_following"}
        or component.get("target_reached") is False
    ]
    if blocking:
        return f"Mission did not count because {', '.join(blocking)}."
    return f"Mission did not count because evaluation status is {status}."


def _snapshot_comparison(
    *,
    mission: CoachMission,
    baseline_window: Mapping[str, Any] | None,
    evaluation_window: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    primary = next((component for component in components if component.get("role") == "primary"), None)
    if primary is None:
        return {}
    success_metric = _mission_success_metric(mission, primary)
    metric_name = str(success_metric.get("metric_name") or primary.get("metric_name") or "")
    before_value = _optional_number(primary.get("baseline_value"))
    after_value = _optional_number(primary.get("observed_value"))
    delta = after_value - before_value if before_value is not None and after_value is not None else None
    return {
        "success_metric": success_metric,
        "before": {
            "metric_snapshot_ids": list(baseline_window.get("snapshot_ids") or [])
            if baseline_window is not None
            else [],
            "value": before_value,
            "sample_matches": baseline_window.get("sample_matches") if baseline_window is not None else None,
            "sample_rounds": baseline_window.get("sample_rounds") if baseline_window is not None else None,
        },
        "after": {
            "metric_snapshot_ids": list(evaluation_window.get("snapshot_ids") or []),
            "value": after_value,
            "sample_matches": evaluation_window.get("sample_matches"),
            "sample_rounds": evaluation_window.get("sample_rounds"),
        },
        "metric_name": metric_name,
        "direction": success_metric.get("direction") or primary.get("direction"),
        "target_value": success_metric.get("target_value"),
        "delta": delta,
        "status": primary.get("outcome"),
    }


def _mission_success_metric(mission: CoachMission, primary_component: Mapping[str, Any]) -> dict[str, Any]:
    source_payload = _json_load_mapping(mission.source_payload_json)
    mission_payload = _mapping(source_payload.get("mission_payload"))
    success_metric = _mapping(mission_payload.get("success_metric"))
    metric_name = success_metric.get("metric_name") or primary_component.get("metric_name")
    return {
        "metric_name": str(metric_name or ""),
        "direction": str(success_metric.get("direction") or primary_component.get("direction") or ""),
        "target_value": _optional_number(success_metric.get("target_value"))
        if "target_value" in success_metric
        else _optional_number(primary_component.get("target_value")),
        "source": "mission_payload.success_metric" if success_metric else "mission_primary_criteria",
    }


def _progress_explanation(
    status: str,
    snapshot_comparison: Mapping[str, Any],
    caveats: Sequence[Any],
) -> str:
    metric_name = str(snapshot_comparison.get("metric_name") or "mission metric")
    before = _mapping(snapshot_comparison.get("before")).get("value")
    after = _mapping(snapshot_comparison.get("after")).get("value")
    before_text = _format_metric_value(before)
    after_text = _format_metric_value(after)
    if status == "improving":
        return f"Improving on the assigned focus: {metric_name} moved from {before_text} to {after_text}."
    if status == "unchanged":
        return f"Unchanged on the assigned focus: {metric_name} stayed near {before_text}."
    if status == "regressing":
        return f"Regressing on the assigned focus: {metric_name} moved from {before_text} to {after_text}."
    if status == "not_following":
        return f"Not enough evidence of following the assigned focus rules for {metric_name}."
    reason = ", ".join(str(caveat) for caveat in caveats) or "missing comparable metric data"
    return f"Insufficient data to judge the assigned focus for {metric_name}: {reason}."


def _format_metric_value(value: Any) -> str:
    number = _optional_number(value)
    if number is None:
        return "unknown"
    return f"{number:.3f}".rstrip("0").rstrip(".")


def _snapshot_to_mapping(snapshot: Any) -> dict[str, Any]:
    if isinstance(snapshot, Mapping):
        return dict(snapshot)
    value: dict[str, Any] = {}
    for name in (
        "id",
        "user_id",
        "owner_steam_id",
        "player_steamid",
        "metrics_json",
        "confidence_baseline_json",
        "caveats_json",
        "metadata_json",
    ):
        if hasattr(snapshot, name):
            value[name] = getattr(snapshot, name)
    return value


def _validate_snapshot_owner(mission: CoachMission, snapshot: Mapping[str, Any]) -> None:
    snapshot_user_id = _optional_int(snapshot.get("user_id"))
    if snapshot_user_id is not None and snapshot_user_id != mission.user_id:
        raise PermissionError("Evaluation metric snapshot belongs to a different user.")
    owner_steam_id = snapshot.get("owner_steam_id") or snapshot.get("player_steamid")
    if mission.owner_steam_id and owner_steam_id and str(owner_steam_id) != mission.owner_steam_id:
        raise PermissionError("Evaluation metric snapshot belongs to a different owner.")


def _snapshot_payload_mapping(snapshot: Mapping[str, Any], direct_key: str, json_key: str) -> dict[str, Any]:
    direct = snapshot.get(direct_key)
    if isinstance(direct, Mapping):
        return dict(direct)
    encoded = snapshot.get(json_key)
    if isinstance(encoded, str):
        return _json_load_mapping(encoded)
    if isinstance(encoded, Mapping):
        return dict(encoded)
    return {}


def _metric_numeric_value(raw_value: Any) -> float | None:
    if isinstance(raw_value, Mapping):
        raw_value = raw_value.get("value")
    try:
        return _optional_number(raw_value)
    except (TypeError, ValueError):
        return None


def _snapshot_confidence(snapshot: Mapping[str, Any]) -> float | None:
    direct_confidence = snapshot.get("confidence")
    if direct_confidence is not None:
        return _optional_float(direct_confidence)
    confidence_payload = _snapshot_payload_mapping(snapshot, "confidence_baseline", "confidence_baseline_json")
    for key in ("confidence", "overall", "level", "metric_confidence"):
        if key in confidence_payload:
            return _optional_float(confidence_payload[key])
    return None


def _snapshot_caveats(snapshot: Mapping[str, Any]) -> list[str]:
    direct = snapshot.get("caveats")
    if isinstance(direct, Sequence) and not isinstance(direct, str):
        return [str(item) for item in direct]
    encoded = snapshot.get("caveats_json")
    if isinstance(encoded, str):
        return [str(item) for item in _json_load_sequence(encoded)]
    return []


def _sample_count(snapshot: Mapping[str, Any], name: str) -> int:
    direct_key = f"sample_{name}"
    if direct_key in snapshot:
        return _optional_int(snapshot.get(direct_key)) or 0
    sample = snapshot.get("sample")
    if isinstance(sample, Mapping) and name in sample:
        return _optional_int(sample.get(name)) or 0
    metadata = _snapshot_payload_mapping(snapshot, "metadata", "metadata_json")
    if direct_key in metadata:
        return _optional_int(metadata.get(direct_key)) or 0
    if name in metadata:
        return _optional_int(metadata.get(name)) or 0
    return 0


def _max_drop(rule: Mapping[str, Any], baseline: float, target: float | None) -> float:
    configured = _optional_number(rule["max_drop"]) if "max_drop" in rule else None
    if configured is None and "accepted_drop" in rule:
        configured = _optional_number(rule["accepted_drop"])
    if configured is not None:
        return configured
    if target is not None and target < baseline:
        return baseline - target
    return 0.0


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
    mission_payload: Mapping[str, Any] | None,
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
    if mission_payload is not None:
        payload["mission_payload"] = dict(mission_payload)
    return payload


def _criteria_specs_from_hypothesis(hypothesis: CoachHypothesis) -> list[dict[str, Any]]:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    evidence = _json_load_sequence(hypothesis.evidence_json)
    return _criteria_specs_from_parts(
        readiness=readiness,
        evidence=evidence,
        target_metric_candidates=_json_load_sequence(hypothesis.target_metric_candidates_json),
    )


def _criteria_specs_from_insight_card(insight_card: Mapping[str, Any]) -> list[dict[str, Any]]:
    readiness = _mapping(_mission_readiness(insight_card))
    evidence = insight_card.get("evidence") if isinstance(insight_card.get("evidence"), list) else []
    return _criteria_specs_from_parts(
        readiness=readiness,
        evidence=evidence,
        target_metric_candidates=_target_metric_candidates(insight_card),
    )


def _criteria_specs_from_parts(
    *,
    readiness: Mapping[str, Any],
    evidence: Sequence[Any],
    target_metric_candidates: Sequence[Any],
) -> list[dict[str, Any]]:
    explicit = readiness.get("criteria") or readiness.get("mission_criteria")
    if isinstance(explicit, Sequence) and not isinstance(explicit, str):
        return [_normalize_criteria_spec(item) for item in explicit if isinstance(item, Mapping)]
    first_evidence = evidence[0] if evidence and isinstance(evidence[0], Mapping) else {}
    primary_metric = _readiness_target_metric(readiness, target_metric_candidates) or _evidence_metric_name(
        first_evidence
    )
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
        "min_sample_rounds": _mission_min_sample_rounds(primary_metric, first_evidence),
        "confidence_required": _confidence_required(readiness),
        "rule": {
            "source": _criteria_rule_source(primary_metric),
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
                    "min_sample_rounds": _mission_min_sample_rounds(metric_name, item),
                    "confidence_required": _confidence_required(readiness),
                    "rule": {"source": _criteria_rule_source(metric_name), "evidence_role": "supporting_evidence"},
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


def _mission_payload_from_parts(
    *,
    title: str,
    problem: str,
    recommended_focus: str,
    caveats: Sequence[Any],
    readiness: Mapping[str, Any],
    criteria_specs: Sequence[Mapping[str, Any]],
    duration: Mapping[str, Any] | None,
    linked_insight: Mapping[str, Any],
) -> dict[str, Any]:
    primary = _primary_criteria_spec(criteria_specs)
    if primary is None:
        raise ValueError("Mission payload requires primary mission criteria.")
    failure_condition = _failure_condition(criteria_specs)
    payload = MissionPayload(
        title=title.strip(),
        goal=_mission_goal(problem=problem, primary=primary),
        rules=tuple(_mission_rules(recommended_focus, caveats, primary, failure_condition)),
        duration=dict(duration or _mission_duration(primary)),
        success_metric=_success_metric(primary),
        failure_condition=failure_condition,
        linked_insight=dict(linked_insight),
    ).to_dict()
    issues = validate_mission_payload(payload)
    if issues:
        codes = ",".join(issue.code for issue in issues)
        raise ValueError(f"Invalid mission payload: {codes}")
    return payload


def _primary_criteria_spec(criteria_specs: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for criteria_spec in criteria_specs:
        if criteria_spec.get("role") == "primary":
            return dict(criteria_spec)
    return dict(criteria_specs[0]) if criteria_specs else None


def _mission_title(*, problem: str, primary_metric: str) -> str:
    if primary_metric == "untraded_death_rate":
        return "Reduce untraded deaths"
    if primary_metric == "opening_death_rate":
        return "Reduce opening deaths"
    if primary_metric == "survival_rate":
        return "Improve round survival"
    cleaned_problem = problem.strip().rstrip(".")
    if cleaned_problem:
        return cleaned_problem[:120]
    return f"Improve {primary_metric.replace('_', ' ')}"


def _mission_goal(*, problem: str, primary: Mapping[str, Any]) -> str:
    metric_name = str(primary["metric_name"])
    baseline = primary.get("baseline_value")
    target = primary.get("target_value")
    if baseline is not None and target is not None:
        if metric_name == "untraded_death_rate":
            return (
                f"Reduce untraded_death_rate from {float(baseline):.3f} to {float(target):.3f} "
                "over upcoming owner matches using supported trade-status metric snapshots."
            )
        if metric_name == "opening_death_rate":
            return (
                f"Reduce opening_death_rate from {float(baseline):.3f} to {float(target):.3f} "
                "over upcoming owner matches using supported metric snapshots."
            )
        if metric_name == "survival_rate":
            return (
                f"Raise survival_rate from {float(baseline):.3f} to {float(target):.3f} "
                "over upcoming owner matches using supported metric snapshots."
            )
        return (
            f"Move {metric_name} from {float(baseline):.3f} toward {float(target):.3f} "
            "using only supported owner metric snapshots."
        )
    return f"Improve {metric_name} using only supported owner metric snapshots."


def _mission_rules(
    recommended_focus: str,
    caveats: Sequence[Any],
    primary: Mapping[str, Any],
    failure_condition: Mapping[str, Any],
) -> list[str]:
    metric_name = str(primary["metric_name"])
    if metric_name == "untraded_death_rate":
        rules = [
            "For each upcoming match, avoid taking isolated fights unless a teammate can trade the death.",
            "Success is measured only by lowering untraded_death_rate in owner-scoped metric snapshots.",
            (
                "Failure is triggered if untraded_death_rate is above the activation baseline or cannot be "
                "evaluated with supported trade-status metrics."
            ),
        ]
    elif metric_name == "opening_death_rate":
        rules = [
            "For each upcoming match, avoid voluntary first contact in the opening phase unless trade support is set.",
            "Success is measured only by lowering opening_death_rate in owner-scoped metric snapshots.",
            (
                "Failure is triggered if opening_death_rate is above the activation baseline or cannot be "
                "evaluated with supported metrics."
            ),
        ]
    elif metric_name == "survival_rate":
        rules = [
            "For each upcoming match, prioritize staying alive through early fights before taking isolated space.",
            "Success is measured only by raising survival_rate in owner-scoped metric snapshots.",
            (
                "Failure is triggered if survival_rate drops below the activation baseline or cannot be "
                "evaluated with supported metrics."
            ),
        ]
    else:
        rules = []
    if rules and recommended_focus.strip():
        rules.append(f"Focus: {recommended_focus.strip()}")
    if not rules:
        rules = [
            recommended_focus.strip() or f"Work on {metric_name.replace('_', ' ')} in the next matches.",
            f"Count progress only when {primary['metric_name']} is present in owner-scoped metric snapshots.",
            f"Do not count the mission if {failure_condition['metric_name']} triggers the failure condition.",
        ]
    for caveat in _string_sequence(caveats)[:2]:
        rules.append(f"Caveat: {caveat}")
    return rules


def _mission_duration(primary: Mapping[str, Any]) -> dict[str, Any]:
    min_matches = _optional_int(primary.get("min_sample_matches")) or 3
    max_matches = max(min_matches, 5)
    return {
        "unit": "matches",
        "min_matches": min_matches,
        "max_matches": max_matches,
        "min_sample_rounds": primary.get("min_sample_rounds"),
        "description": f"Evaluate after {min_matches}-{max_matches} owner matches with supported metrics.",
    }


def _success_metric(primary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "metric_name": primary["metric_name"],
        "direction": primary["direction"],
        "baseline_value": primary.get("baseline_value"),
        "target_value": primary.get("target_value"),
        "min_sample_matches": primary.get("min_sample_matches"),
        "min_sample_rounds": primary.get("min_sample_rounds"),
        "confidence_required": primary.get("confidence_required"),
    }


def _failure_condition(criteria_specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    guardrail = next((dict(item) for item in criteria_specs if item.get("role") == "guardrail"), None)
    primary = _primary_criteria_spec(criteria_specs)
    source = guardrail or primary
    if source is None:
        raise ValueError("Mission payload requires failure criteria.")
    threshold = source.get("target_value")
    if threshold is None:
        threshold = source.get("baseline_value")
    return {
        "metric_name": source["metric_name"],
        "direction": source["direction"],
        "threshold_value": threshold,
        "reason": _failure_reason(source),
    }


def _validate_payload_non_empty_string(
    payload: Mapping[str, Any],
    field: str,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(payload.get(field), str) or not payload.get(field, "").strip():
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_payload_field",
                f"Mission payload field must be a non-empty string: {field}.",
                f"{path}.{field}",
            )
        )


def _validate_mission_rules(
    rules: Any,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(rules, list):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_rules",
                "Mission rules must be a list.",
                f"{path}.rules",
            )
        )
        return
    if not rules:
        issues.append(
            MissionPayloadValidationIssue(
                "missing_mission_rules",
                "Mission rules must include at least one rule.",
                f"{path}.rules",
            )
        )
    if any(not isinstance(rule, str) or not rule.strip() for rule in rules):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_rule",
                "Mission rules must be non-empty strings.",
                f"{path}.rules",
            )
        )


def _validate_mission_duration(
    duration: Any,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(duration, Mapping):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_duration",
                "Mission duration must be an object.",
                f"{path}.duration",
            )
        )
        return
    if not isinstance(duration.get("unit"), str) or not duration.get("unit", "").strip():
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_duration_unit",
                "Mission duration requires a non-empty unit.",
                f"{path}.duration.unit",
            )
        )
    min_matches = _optional_positive_int(duration.get("min_matches"))
    max_matches = _optional_positive_int(duration.get("max_matches"))
    if min_matches is None and max_matches is None:
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_duration_window",
                "Mission duration requires min_matches or max_matches.",
                f"{path}.duration",
            )
        )
    if min_matches is not None and max_matches is not None and max_matches < min_matches:
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_duration_window",
                "Mission duration max_matches must be greater than or equal to min_matches.",
                f"{path}.duration.max_matches",
            )
        )


def _validate_mission_success_metric(
    success_metric: Any,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(success_metric, Mapping):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_success_metric",
                "Mission success_metric must be an object.",
                f"{path}.success_metric",
            )
        )
        return
    _validate_metric_payload(success_metric, path, "success_metric", issues)
    if _optional_number_or_none(success_metric.get("target_value")) is None:
        issues.append(
            MissionPayloadValidationIssue(
                "missing_mission_success_target",
                "Mission success_metric requires a numeric target_value.",
                f"{path}.success_metric.target_value",
            )
        )


def _validate_mission_failure_condition(
    failure_condition: Any,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(failure_condition, Mapping):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_failure_condition",
                "Mission failure_condition must be an object.",
                f"{path}.failure_condition",
            )
        )
        return
    _validate_metric_payload(failure_condition, path, "failure_condition", issues)
    if _optional_number_or_none(failure_condition.get("threshold_value")) is None:
        issues.append(
            MissionPayloadValidationIssue(
                "missing_mission_failure_threshold",
                "Mission failure_condition requires a numeric threshold_value.",
                f"{path}.failure_condition.threshold_value",
            )
        )


def _validate_metric_payload(
    metric_payload: Mapping[str, Any],
    path: str,
    field: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(metric_payload.get("metric_name"), str) or not metric_payload.get("metric_name", "").strip():
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_metric_name",
                "Mission metric payload requires a non-empty metric_name.",
                f"{path}.{field}.metric_name",
            )
        )
    if metric_payload.get("direction") not in CRITERIA_DIRECTIONS:
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_metric_direction",
                "Mission metric direction is unsupported.",
                f"{path}.{field}.direction",
            )
        )


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


def _readiness_target_metric(readiness: Mapping[str, Any], target_metric_candidates: Sequence[Any]) -> str | None:
    target = readiness.get("target_metric_candidate")
    if target:
        return str(target)
    candidates = readiness.get("target_metric_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, str):
        candidates = target_metric_candidates
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


def _mission_min_sample_rounds(metric_name: str, evidence: Mapping[str, Any]) -> int | None:
    if metric_name in BAD_FIGHT_TRADE_MISSION_METRICS:
        rounds = _optional_int(evidence.get("rounds"))
        if rounds is not None and rounds > 0:
            return rounds
        return None
    if metric_name not in SURVIVAL_OPENING_MISSION_METRICS:
        return None
    sample_count = _optional_int(evidence.get("sample_count"))
    if sample_count is None or sample_count <= 0:
        return None
    return sample_count


def _criteria_rule_source(metric_name: str) -> str:
    if metric_name in BAD_FIGHT_TRADE_MISSION_METRICS:
        return "bad_fight_trade_mission_template"
    if metric_name in SURVIVAL_OPENING_MISSION_METRICS:
        return "survival_opening_mission_template"
    return "mission_readiness"


def _failure_reason(source: Mapping[str, Any]) -> str:
    metric_name = str(source.get("metric_name") or "")
    if metric_name == "untraded_death_rate":
        return (
            "Mission fails if untraded_death_rate rises above the activation baseline or cannot be evaluated "
            "with supported trade-status metrics."
        )
    if metric_name == "opening_death_rate":
        return (
            "Mission fails if opening_death_rate rises above the activation baseline or cannot be evaluated "
            "with supported metrics."
        )
    if metric_name == "survival_rate":
        return (
            "Mission fails if survival_rate drops below the activation baseline or cannot be evaluated "
            "with supported metrics."
        )
    return "Mission fails if this condition regresses or cannot be evaluated with supported metrics."


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


def _optional_number_or_none(value: Any) -> float | None:
    try:
        return _optional_number(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_positive_int(value: Any) -> int | None:
    try:
        parsed = _optional_int(value)
    except (TypeError, ValueError):
        return None
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    output: list[int] = []
    for item in value:
        try:
            output.append(int(item))
        except (TypeError, ValueError):
            continue
    return output


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
