"""Owner-facing mission context and result serialization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    CoachMission,
    MissionProgressEvaluation,
)
from app.services.missions.payloads import (
    _domain_key_for_metric,
    _int_list,
    _json_load_mapping,
    _json_load_sequence,
    _mapping,
    _optional_int,
    _optional_str,
    mission_domain_key,
    mission_problem_key,
    serialize_mission_payload,
)
from app.services.missions.progress import (
    _active_mission_feedback,
    _component_summary,
    _mission_count_reason,
    _mission_payload_type,
    _no_evaluation_progress_summary,
    _progress_explanation,
)
from app.services.missions.repository import (
    list_active_coach_missions,
    list_mission_progress_evaluations,
)
from app.services.missions.types import (
    MissionSuppressionDecision,
)


def active_mission_context_for_owner(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str,
) -> dict[str, Any]:
    missions = list_active_coach_missions(db, user_id=user_id, owner_steam_id=owner_steam_id)
    summaries = []
    for mission in missions:
        evaluations = list_mission_progress_evaluations(db, user_id=user_id, mission_id=mission.id)
        summaries.append(
            serialize_active_mission_summary(
                mission,
                latest_evaluation=evaluations[0] if evaluations else None,
            )
        )
    return {
        "scope": "owner_active_missions",
        "user_id": user_id,
        "owner_steam_id": owner_steam_id,
        "active_mission_count": len(summaries),
        "active_missions": summaries,
        "suppression_keys": [summary["suppression_key"] for summary in summaries],
    }

def mission_suppression_key_from_payload(
    *,
    owner_user_id: int,
    owner_steam_id: str | None,
    mission_payload: Mapping[str, Any] | None,
    domain_key: str | None = None,
    problem_key: str | None = None,
) -> dict[str, Any]:
    payload = _mapping(mission_payload)
    success_metric = _mapping(payload.get("success_metric"))
    target_metric = _optional_str(success_metric.get("metric_name"))
    resolved_domain_key = domain_key or (_domain_key_for_metric(target_metric) if target_metric else None)
    return {
        "owner_user_id": owner_user_id,
        "owner_steam_id": owner_steam_id,
        "domain_key": resolved_domain_key,
        "problem_key": problem_key or resolved_domain_key,
        "target_metric": target_metric,
        "mission_payload_type": _mission_payload_type(payload, domain_key=resolved_domain_key),
    }

def mission_suppression_decision_for_payload(
    *,
    candidate_key: Mapping[str, Any],
    active_mission_summaries: Sequence[Mapping[str, Any]],
) -> MissionSuppressionDecision:
    key = dict(candidate_key)
    candidate_owner = key.get("owner_user_id")
    candidate_steam = key.get("owner_steam_id")
    candidate_domain = key.get("domain_key")
    for summary in active_mission_summaries:
        active_key = _mapping(summary.get("suppression_key"))
        if active_key.get("owner_user_id") != candidate_owner:
            continue
        if active_key.get("owner_steam_id") != candidate_steam:
            continue
        if active_key.get("domain_key") != candidate_domain:
            continue
        if summary.get("mission_status") == "active":
            return MissionSuppressionDecision(
                suppressed=True,
                reason="active_mission_same_domain",
                reason_codes=("active_mission_same_domain",),
                active_mission_id=_optional_int(summary.get("mission_id")),
                active_mission_title=_optional_str(summary.get("title")),
                active_mission_status=_optional_str(summary.get("mission_status")),
                active_mission_progress_status=_optional_str(summary.get("progress_status")),
                key=key,
            )
    return MissionSuppressionDecision(
        suppressed=False,
        reason=None,
        reason_codes=(),
        active_mission_id=None,
        active_mission_title=None,
        active_mission_status=None,
        active_mission_progress_status=None,
        key=key,
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

def serialize_active_mission_summary(
    mission: CoachMission,
    *,
    latest_evaluation: MissionProgressEvaluation | None = None,
) -> dict[str, Any]:
    mission_payload = _mapping(_json_load_mapping(mission.source_payload_json).get("mission_payload"))
    success_metric = _mapping(mission_payload.get("success_metric"))
    target_metric = _optional_str(success_metric.get("metric_name"))
    domain_key = mission_domain_key(mission)
    progress = (
        serialize_mission_progress_evaluation(latest_evaluation)
        if latest_evaluation is not None
        else _no_evaluation_progress_summary(mission, target_metric=target_metric)
    )
    comparison = _mapping(progress.get("snapshot_comparison"))
    before = _mapping(comparison.get("before"))
    after = _mapping(comparison.get("after"))
    primary = _mapping(progress.get("primary_metric_result"))
    metric_name = (
        _optional_str(comparison.get("metric_name"))
        or _optional_str(primary.get("metric_name"))
        or target_metric
    )
    return {
        "mission_id": mission.id,
        "title": mission.title,
        "mission_status": mission.status,
        "owner_steam_id": mission.owner_steam_id,
        "domain_key": domain_key,
        "problem_key": mission_problem_key(mission),
        "target_metric": target_metric,
        "mission_payload_type": _mission_payload_type(mission_payload, domain_key=domain_key),
        "metric": metric_name,
        "baseline_value": before.get("value") if before else primary.get("baseline_value"),
        "current_value": after.get("value") if after else primary.get("evaluation_value"),
        "delta": comparison.get("delta") if comparison else primary.get("delta"),
        "confidence": progress.get("confidence"),
        "caveats": list(progress.get("caveats") or []),
        "counted": progress.get("counted") is True,
        "progress_status": progress.get("status"),
        "progress_explanation": progress.get("progress_explanation"),
        "coach_feedback": _active_mission_feedback(
            mission_title=mission.title,
            progress_status=str(progress.get("status") or "no_evaluation_yet"),
            metric_name=metric_name,
            progress_explanation=_optional_str(progress.get("progress_explanation")),
        ),
        "latest_progress_evaluation": progress,
        "suppression_key": mission_suppression_key_from_payload(
            owner_user_id=mission.user_id,
            owner_steam_id=mission.owner_steam_id,
            mission_payload=mission_payload,
            domain_key=domain_key,
            problem_key=mission_problem_key(mission),
        ),
    }

def serialize_coach_mission(mission: CoachMission) -> dict[str, Any]:
    source_payload = _json_load_mapping(mission.source_payload_json)
    legacy_domain_key = source_payload.get("mission_domain_key") or source_payload.get("domain_key")
    return {
        "mission_id": mission.id,
        "hypothesis_id": mission.hypothesis_id,
        "user_id": mission.user_id,
        "owner_steam_id": mission.owner_steam_id,
        "status": mission.status,
        "domain_key": mission_domain_key(mission),
        "problem_key": mission_problem_key(mission),
        "legacy_domain_key": legacy_domain_key if legacy_domain_key != mission_domain_key(mission) else None,
        "title": mission.title,
        "focus": mission.focus,
        "mission_payload": serialize_mission_payload(source_payload.get("mission_payload")),
        "source_payload": source_payload,
        "activated_at": mission.activated_at.isoformat() if mission.activated_at else None,
        "ended_at": mission.ended_at.isoformat() if mission.ended_at else None,
    }

def _active_mission_primary_metrics(db: Session, *, user_id: int, owner_steam_id: str) -> set[str]:
    metrics: set[str] = set()
    for mission in list_active_coach_missions(db, user_id=user_id, owner_steam_id=owner_steam_id):
        source_payload = _json_load_mapping(mission.source_payload_json)
        mission_payload = _mapping(source_payload.get("mission_payload"))
        success_metric = _mapping(mission_payload.get("success_metric"))
        metric_name = success_metric.get("metric_name")
        if metric_name:
            metrics.add(str(metric_name))
    return metrics

def _active_mission_domain_keys(db: Session, *, user_id: int, owner_steam_id: str) -> set[str]:
    keys: set[str] = set()
    for mission in list_active_coach_missions(db, user_id=user_id, owner_steam_id=owner_steam_id):
        domain_key = mission_domain_key(mission)
        if domain_key:
            keys.add(domain_key)
    return keys

__all__ = (
    'active_mission_context_for_owner',
    'mission_suppression_decision_for_payload',
    'mission_suppression_key_from_payload',
    'serialize_active_mission_summary',
    'serialize_coach_mission',
    'serialize_mission_progress_evaluation',
)
