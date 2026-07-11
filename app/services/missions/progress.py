"""Mission criteria evaluation and progress computation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    CoachMission,
    MissionCriteria,
    MissionProgressEvaluation,
)
from app.services.missions.payloads import (
    _default_metric_direction,
    _domain_key_for_metric,
    _json_load_mapping,
    _json_load_sequence,
    _mapping,
    _optional_float,
    _optional_int,
    _optional_number,
    _optional_positive_int,
    _optional_str,
)
from app.services.missions.repository import (
    _require_owned_mission,
    list_mission_criteria,
    record_mission_progress_evaluation,
)
from app.services.missions.types import (
    CORE_COMBAT_SNAPSHOT_SOURCE,
    UTILITY_SNAPSHOT_METRICS,
    UTILITY_SNAPSHOT_SOURCE,
)


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
    criteria_metric_names = {criteria.metric_name for criteria in criteria_rows}
    baseline_window = (
        _metric_snapshot_window(mission, baseline_metric_snapshots, metric_names=criteria_metric_names)
        if baseline_metric_snapshots is not None
        else None
    )
    snapshot_window = _metric_snapshot_window(
        mission,
        evaluation_metric_snapshots,
        metric_names=criteria_metric_names,
    )
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
    window_payload = dict(evaluation_window or {})
    window_payload.update({
        "start": evaluation_window_start.isoformat() if evaluation_window_start else None,
        "end": evaluation_window_end.isoformat() if evaluation_window_end else None,
        "snapshot_ids": snapshot_window["snapshot_ids"],
        "snapshot_count": snapshot_window["snapshot_count"],
        "match_ids": snapshot_window["match_ids"],
        "sample_matches": snapshot_window["sample_matches"],
        "sample_rounds": snapshot_window["sample_rounds"],
        "metric_samples": snapshot_window["metric_samples"],
    })
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

def _metric_snapshot_window(
    mission: CoachMission,
    evaluation_metric_snapshots: Sequence[Any],
    *,
    metric_names: set[str] | None = None,
) -> dict[str, Any]:
    candidates_by_metric_match: dict[str, dict[int, list[dict[str, Any]]]] = {}
    metric_reason_codes: dict[str, set[str]] = {}
    metric_lineage_ids: dict[str, list[int]] = {}
    caveats: list[str] = []
    snapshot_ids: list[int] = []
    seen_snapshot_keys: set[tuple[str, Any]] = set()
    for index, raw_snapshot in enumerate(evaluation_metric_snapshots):
        snapshot = _snapshot_to_mapping(raw_snapshot)
        _validate_snapshot_owner(mission, snapshot)
        snapshot_id = _optional_int(snapshot.get("id"))
        snapshot_key = ("id", snapshot_id) if snapshot_id is not None else ("position", index)
        if snapshot_key in seen_snapshot_keys:
            continue
        seen_snapshot_keys.add(snapshot_key)
        if snapshot_id is not None:
            snapshot_ids.append(snapshot_id)
        source = _optional_str(snapshot.get("source")) or "unknown"
        match_id = _optional_positive_int(snapshot.get("match_id"))
        metric_payload = _snapshot_payload_mapping(snapshot, "metrics", "metrics_json")
        for metric_name, raw_value in metric_payload.items():
            metric_name = str(metric_name)
            value = _metric_numeric_value(raw_value)
            if value is None:
                continue
            if snapshot_id is not None:
                metric_lineage_ids.setdefault(metric_name, []).append(snapshot_id)
            if match_id is None:
                metric_reason_codes.setdefault(metric_name, set()).add("missing_match_identity")
                continue
            candidates_by_metric_match.setdefault(metric_name, {}).setdefault(match_id, []).append(
                {
                    "snapshot_id": snapshot_id,
                    "source": source,
                    "value": value,
                    "confidence": _metric_snapshot_confidence(snapshot, metric_name),
                    "sample_rounds": _metric_sample_rounds(snapshot, metric_payload),
                    "source_parser_artifact_id": _optional_int(snapshot.get("source_parser_artifact_id")),
                    "source_event_set_id": _optional_str(snapshot.get("source_event_set_id")),
                }
            )
        caveats.extend(_snapshot_caveats(snapshot))

    metric_samples: dict[str, dict[str, Any]] = {}
    for metric_name in sorted(set(candidates_by_metric_match) | set(metric_reason_codes)):
        observations: list[dict[str, Any]] = []
        reason_codes = set(metric_reason_codes.get(metric_name, set()))
        deduplicated_snapshot_ids: list[int] = []
        unresolved_conflict = False
        for match_id, candidates in sorted(candidates_by_metric_match.get(metric_name, {}).items()):
            observation = _resolve_metric_observation(metric_name, match_id, candidates)
            reason_codes.update(observation["reason_codes"])
            deduplicated_snapshot_ids.extend(observation["deduplicated_snapshot_ids"])
            if observation["canonical"] is None:
                unresolved_conflict = True
                continue
            observations.append(observation["canonical"])
        missing_confidence = any(item["confidence"] is None for item in observations)
        if missing_confidence:
            reason_codes.add("missing_metric_specific_confidence")
        canonical_snapshot_ids = _ordered_ints(item["snapshot_id"] for item in observations)
        match_ids = [item["match_id"] for item in observations]
        confidence_values = [item["confidence"] for item in observations if item["confidence"] is not None]
        sources = sorted({item["source"] for item in observations})
        source_lineage = [
            {
                "match_id": match_id,
                "snapshot_id": candidate.get("snapshot_id"),
                "source": candidate.get("source"),
                "source_parser_artifact_id": candidate.get("source_parser_artifact_id"),
                "source_event_set_id": candidate.get("source_event_set_id"),
            }
            for match_id, candidates in sorted(candidates_by_metric_match.get(metric_name, {}).items())
            for candidate in candidates
        ]
        metric_samples[metric_name] = {
            "canonical_source": sources[0] if len(sources) == 1 else "+".join(sources),
            "snapshot_ids": canonical_snapshot_ids,
            "deduplicated_snapshot_ids": _ordered_ints(deduplicated_snapshot_ids),
            "source_snapshot_ids": _ordered_ints(metric_lineage_ids.get(metric_name, [])),
            "match_ids": match_ids,
            "sample_matches": len(match_ids),
            "sample_rounds": sum(item["sample_rounds"] for item in observations),
            "confidence": min(confidence_values) if confidence_values and not missing_confidence else None,
            "observations": [
                {
                    "match_id": item["match_id"],
                    "snapshot_id": item["snapshot_id"],
                    "source": item["source"],
                    "source_parser_artifact_id": item["source_parser_artifact_id"],
                    "source_event_set_id": item["source_event_set_id"],
                }
                for item in observations
            ],
            "source_lineage": source_lineage,
            "value": (
                sum(item["value"] for item in observations) / len(observations)
                if observations and not unresolved_conflict
                else None
            ),
            "reason_codes": sorted(reason_codes),
            "usable": bool(observations) and not unresolved_conflict,
        }

    relevant_names = metric_names if metric_names is not None else set(metric_samples)
    relevant_samples = [metric_samples[name] for name in sorted(relevant_names) if name in metric_samples]
    match_ids = sorted({match_id for sample in relevant_samples for match_id in sample["match_ids"]})
    relevant_confidences = [sample["confidence"] for sample in relevant_samples if sample["confidence"] is not None]
    relevant_confidence_missing = any(sample["confidence"] is None for sample in relevant_samples)
    return {
        "metrics": {
            metric_name: sample["value"]
            for metric_name, sample in metric_samples.items()
            if sample["usable"] and sample["value"] is not None
        },
        "metric_samples": metric_samples,
        "snapshot_ids": _ordered_ints(snapshot_ids),
        "snapshot_count": len(seen_snapshot_keys),
        "match_ids": match_ids,
        "sample_matches": len(match_ids),
        "sample_rounds": max((sample["sample_rounds"] for sample in relevant_samples), default=0),
        "confidence": (
            min(relevant_confidences)
            if relevant_confidences and not relevant_confidence_missing
            else None
        ),
        "caveats": sorted(set(caveats)),
    }

def _resolve_metric_observation(
    metric_name: str,
    match_id: int,
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    authoritative_source = _canonical_metric_source(metric_name)
    authoritative = [item for item in candidates if item.get("source") == authoritative_source]
    eligible = authoritative or list(candidates)
    values = {float(item["value"]) for item in eligible}
    all_values = {float(item["value"]) for item in candidates}
    reason_codes: set[str] = set()
    if len(candidates) > 1:
        reason_codes.add("duplicate_metric_source_deduplicated")
    if len(all_values) > 1:
        reason_codes.add("conflicting_metric_sources")
    if len(values) > 1 or (len(all_values) > 1 and not authoritative):
        return {
            "canonical": None,
            "deduplicated_snapshot_ids": _ordered_ints(item.get("snapshot_id") for item in candidates),
            "reason_codes": sorted(reason_codes),
        }
    selected = min(
        eligible,
        key=lambda item: (
            str(item.get("source") or ""),
            _optional_int(item.get("snapshot_id")) or 0,
        ),
    )
    canonical = dict(selected)
    canonical["match_id"] = match_id
    deduplicated = [
        item.get("snapshot_id")
        for item in candidates
        if item is not selected
    ]
    return {
        "canonical": canonical,
        "deduplicated_snapshot_ids": _ordered_ints(deduplicated),
        "reason_codes": sorted(reason_codes),
    }

def _canonical_metric_source(metric_name: str) -> str:
    if metric_name in UTILITY_SNAPSHOT_METRICS:
        return UTILITY_SNAPSHOT_SOURCE
    return CORE_COMBAT_SNAPSHOT_SOURCE

def _evaluate_criteria(
    criteria: MissionCriteria,
    snapshot_window: Mapping[str, Any],
    *,
    baseline_window: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = _mapping(snapshot_window.get("metrics"))
    metric_sample = _mapping(_mapping(snapshot_window.get("metric_samples")).get(criteria.metric_name))
    baseline_metrics = _mapping(baseline_window.get("metrics")) if baseline_window is not None else {}
    baseline_metric_sample = (
        _mapping(_mapping(baseline_window.get("metric_samples")).get(criteria.metric_name))
        if baseline_window is not None
        else {}
    )
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
        "baseline_metric_snapshot_ids": list(baseline_metric_sample.get("snapshot_ids") or []),
        "target_value": criteria.target_value,
        "observed_value": _optional_number(metrics.get(criteria.metric_name))
        if criteria.metric_name in metrics
        else None,
        "delta": None,
        "outcome": "insufficient_data",
        "reason_codes": list(metric_sample.get("reason_codes") or []),
        "canonical_source": metric_sample.get("canonical_source"),
        "metric_snapshot_ids": list(metric_sample.get("snapshot_ids") or []),
        "deduplicated_metric_snapshot_ids": list(metric_sample.get("deduplicated_snapshot_ids") or []),
        "match_ids": list(metric_sample.get("match_ids") or []),
        "sample_matches": metric_sample.get("sample_matches", 0),
        "sample_rounds": metric_sample.get("sample_rounds", 0),
        "confidence": metric_sample.get("confidence"),
        "rule": rule,
    }
    sample_reason = _insufficient_sample_reason(criteria, metric_sample)
    confidence_reason = _insufficient_confidence_reason(criteria, metric_sample)
    if criteria.metric_name not in metrics:
        component["reason_codes"].append("missing_metric")
        return component
    if baseline_window is not None and criteria.metric_name not in baseline_metrics:
        component["reason_codes"].append("missing_baseline_metric")
        return component
    if sample_reason:
        if sample_reason == "insufficient_sample_rounds" and not component["sample_rounds"]:
            component["reason_codes"].append("unavailable_round_sample")
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
    del snapshot_window
    confidences = [_optional_number(component.get("confidence")) for component in components]
    if not confidences or any(confidence is None for confidence in confidences):
        return None
    confidence = min(value for value in confidences if value is not None)
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
                "missing_match_identity",
                "missing_metric_specific_confidence",
                "insufficient_confidence",
                "conflicting_metric_sources",
                "duplicate_metric_source_deduplicated",
                "unavailable_round_sample",
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
        "metric_snapshot_ids": list(component.get("metric_snapshot_ids") or []),
        "deduplicated_metric_snapshot_ids": list(component.get("deduplicated_metric_snapshot_ids") or []),
        "match_ids": list(component.get("match_ids") or []),
        "canonical_source": component.get("canonical_source"),
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
    baseline_metric_sample = (
        _mapping(_mapping(baseline_window.get("metric_samples")).get(metric_name))
        if baseline_window is not None
        else {}
    )
    return {
        "success_metric": success_metric,
        "before": {
            "metric_snapshot_ids": list(primary.get("baseline_metric_snapshot_ids") or []),
            "deduplicated_metric_snapshot_ids": list(
                baseline_metric_sample.get("deduplicated_snapshot_ids") or []
            ),
            "source_metric_snapshot_ids": list(baseline_metric_sample.get("source_snapshot_ids") or []),
            "canonical_source": baseline_metric_sample.get("canonical_source"),
            "value": before_value,
            "match_ids": list(baseline_metric_sample.get("match_ids") or []),
            "sample_matches": baseline_metric_sample.get("sample_matches") if baseline_window is not None else None,
            "sample_rounds": baseline_metric_sample.get("sample_rounds") if baseline_window is not None else None,
        },
        "after": {
            "metric_snapshot_ids": list(primary.get("metric_snapshot_ids") or []),
            "deduplicated_metric_snapshot_ids": list(primary.get("deduplicated_metric_snapshot_ids") or []),
            "source_metric_snapshot_ids": list(
                _mapping(_mapping(evaluation_window.get("metric_samples")).get(metric_name)).get(
                    "source_snapshot_ids"
                )
                or []
            ),
            "canonical_source": primary.get("canonical_source"),
            "value": after_value,
            "match_ids": list(primary.get("match_ids") or []),
            "sample_matches": primary.get("sample_matches"),
            "sample_rounds": primary.get("sample_rounds"),
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

def _no_evaluation_progress_summary(mission: CoachMission, *, target_metric: str | None) -> dict[str, Any]:
    return {
        "evaluation_id": None,
        "mission_id": mission.id,
        "owner_steam_id": mission.owner_steam_id,
        "evaluated_window": {},
        "source_metric_snapshot_ids": [],
        "status": "no_evaluation_yet",
        "confidence": None,
        "caveats": ["no_evaluation_yet"],
        "primary_metric_result": {
            "metric_name": target_metric,
            "role": "primary",
            "reason_codes": ["no_evaluation_yet"],
        },
        "secondary_metric_results": [],
        "guardrail_results": [],
        "snapshot_comparison": {
            "metric_name": target_metric,
            "before": {"metric_snapshot_ids": [], "value": None},
            "after": {"metric_snapshot_ids": [], "value": None},
            "delta": None,
        },
        "target_met": False,
        "counted": False,
        "why_counted_or_not": "Mission has no persisted progress evaluation yet.",
        "progress_explanation": "No persisted mission progress evaluation is available yet.",
    }

def _active_mission_feedback(
    *,
    mission_title: str,
    progress_status: str,
    metric_name: str | None,
    progress_explanation: str | None,
) -> str:
    metric = metric_name or "mission metric"
    if progress_status == "improving":
        return f"{mission_title}: improving on {metric}; continue the active mission focus."
    if progress_status == "unchanged":
        return f"{mission_title}: {metric} is unchanged; continue the active mission focus."
    if progress_status == "regressing":
        return f"{mission_title}: regressing on {metric}; explain the failed metric before changing missions."
    if progress_status == "not_following":
        return f"{mission_title}: not_following; explain what rule was not followed before replacing the mission."
    if progress_status == "insufficient_data":
        return f"{mission_title}: insufficient_data for {metric}; do not make a hard progress or failure claim."
    if progress_status == "no_evaluation_yet":
        return f"{mission_title}: no_evaluation_yet; wait for persisted owner-scoped progress data."
    return progress_explanation or f"{mission_title}: continue the active mission focus."

def _mission_payload_type(payload: Mapping[str, Any], *, domain_key: str | None = None) -> str | None:
    success_metric = _mapping(payload.get("success_metric"))
    metric_name = _optional_str(success_metric.get("metric_name"))
    if domain_key:
        return f"{domain_key}_mission"
    if metric_name:
        return f"{_domain_key_for_metric(metric_name)}_mission"
    schema = _optional_str(payload.get("schema_version"))
    return schema

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
        "match_id",
        "user_id",
        "owner_steam_id",
        "player_key",
        "player_steamid",
        "source",
        "source_parser_artifact_id",
        "source_event_set_id",
        "metrics",
        "metrics_json",
        "confidence",
        "confidence_baseline",
        "confidence_baseline_json",
        "caveats",
        "caveats_json",
        "metadata",
        "metadata_json",
        "sample_matches",
        "sample_rounds",
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

def _metric_snapshot_confidence(snapshot: Mapping[str, Any], metric_name: str) -> float | None:
    confidence_payload = _snapshot_payload_mapping(snapshot, "confidence_baseline", "confidence_baseline_json")
    metric_confidences = confidence_payload.get("metrics")
    metric_confidence = metric_confidences.get(metric_name) if isinstance(metric_confidences, Mapping) else None
    if isinstance(metric_confidence, Mapping):
        for key in ("confidence", "score", "level", "metric_confidence"):
            if key in metric_confidence:
                return _confidence_value(metric_confidence[key])
    elif metric_confidence is not None:
        return _confidence_value(metric_confidence)
    direct_metric_confidences = snapshot.get("metric_confidence")
    if isinstance(direct_metric_confidences, Mapping) and metric_name in direct_metric_confidences:
        return _confidence_value(direct_metric_confidences[metric_name])
    metric_payload = _snapshot_payload_mapping(snapshot, "metrics", "metrics_json")
    if len(metric_payload) == 1 and snapshot.get("confidence") is not None:
        return _confidence_value(snapshot.get("confidence"))
    return None

def _confidence_value(value: Any) -> float | None:
    try:
        return _optional_float(value)
    except (TypeError, ValueError):
        return None

def _metric_sample_rounds(snapshot: Mapping[str, Any], metrics: Mapping[str, Any]) -> int:
    rounds = _optional_int(metrics.get("rounds_played")) if metrics.get("rounds_played") is not None else None
    if rounds is not None and rounds > 0:
        return rounds
    return _sample_count(snapshot, "rounds")

def _ordered_ints(values: Sequence[Any] | Any) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()
    for value in values:
        parsed = _optional_int(value)
        if parsed is not None and parsed not in seen:
            seen.add(parsed)
            ordered.append(parsed)
    return ordered

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

__all__ = (
    'evaluate_mission_progress',
)
