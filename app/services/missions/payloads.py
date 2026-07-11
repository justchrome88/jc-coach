"""Mission payload construction and validation."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from app.db.models import (
    CoachHypothesis,
    CoachMission,
)
from app.services.coach_domain_model import (
    canonical_domain_for_family,
    canonicalize_domain_key,
)
from app.services.missions.types import (
    BAD_FIGHT_TRADE_MISSION_METRICS,
    CRITERIA_DIRECTIONS,
    CRITERIA_ROLES,
    EFFECTIVE_UTILITY_METRIC,
    INSIGHT_CONFIDENCE_SCORES,
    MISSION_ELIGIBLE_CONFIDENCE_LEVELS,
    MISSION_PAYLOAD_SCHEMA_VERSION,
    REQUIRED_MISSION_PAYLOAD_FIELDS,
    SURVIVAL_OPENING_MISSION_METRICS,
    UTILITY_VALUE_MISSION_METRICS,
    MissionPayload,
    MissionPayloadValidationIssue,
)


def mission_payload_from_insight_card(
    insight_card: Mapping[str, Any],
    *,
    title: str | None = None,
    duration: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    readiness = _mapping(_mission_readiness(insight_card))
    if not _readiness_allows_mission_payload(readiness):
        return None
    criteria_specs = _criteria_specs_from_insight_card(insight_card)
    if not criteria_specs:
        return None
    linked_insight: dict[str, Any] = {
        "source_insight_card_id": _optional_str(insight_card.get("id") or insight_card.get("card_id")),
        "source": "insight_card",
    }
    trend_evidence = _mapping(readiness.get("trend_evidence"))
    if trend_evidence:
        linked_insight["trend_evidence"] = trend_evidence
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
        linked_insight=linked_insight,
    )

def mission_payload_from_hypothesis(
    hypothesis: CoachHypothesis,
    *,
    title: str | None = None,
    duration: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    if not _readiness_allows_mission_payload(readiness):
        return None
    criteria_specs = _criteria_specs_from_hypothesis(hypothesis)
    if not criteria_specs:
        return None
    linked_insight: dict[str, Any] = {
        "source_hypothesis_id": hypothesis.id,
        "source_insight_card_id": hypothesis.source_insight_card_id,
        "analysis_run_id": hypothesis.analysis_run_id,
        "source": "coach_hypothesis",
    }
    trend_evidence = _mapping(readiness.get("trend_evidence"))
    if trend_evidence:
        linked_insight["trend_evidence"] = trend_evidence
    return _mission_payload_from_parts(
        title=title or _mission_title(problem=hypothesis.problem, primary_metric=str(criteria_specs[0]["metric_name"])),
        problem=hypothesis.problem,
        recommended_focus=hypothesis.recommended_focus,
        caveats=_json_load_sequence(hypothesis.caveats_json),
        readiness=readiness,
        criteria_specs=criteria_specs,
        duration=duration,
        linked_insight=linked_insight,
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

def mission_domain_key(mission: CoachMission) -> str | None:
    source_payload = _json_load_mapping(mission.source_payload_json)
    domain_key = source_payload.get("mission_domain_key") or source_payload.get("domain_key")
    if domain_key:
        return canonicalize_domain_key(str(domain_key))
    mission_payload = _mapping(source_payload.get("mission_payload"))
    success_metric = _mapping(mission_payload.get("success_metric"))
    metric_name = success_metric.get("metric_name")
    if metric_name:
        return _domain_key_for_metric(str(metric_name))
    return None

def mission_problem_key(mission: CoachMission) -> str | None:
    source_payload = _json_load_mapping(mission.source_payload_json)
    problem_key = source_payload.get("problem_key")
    if problem_key:
        return canonicalize_domain_key(str(problem_key))
    return mission_domain_key(mission)

def _readiness_allows_mission_payload(readiness: Mapping[str, Any]) -> bool:
    if readiness.get("can_become_mission") is not True:
        return False
    if _string_sequence(readiness.get("blocking_reason_codes")):
        return False
    confidence_eligibility = readiness.get("confidence_eligibility")
    if not isinstance(confidence_eligibility, Mapping):
        return False
    confidence_level = _optional_lower_str(confidence_eligibility.get("level"))
    return (
        confidence_level in MISSION_ELIGIBLE_CONFIDENCE_LEVELS
        and confidence_eligibility.get("usable_for_missions") is True
        and confidence_eligibility.get("hard_recommendation_eligible") is True
    )

def _mission_source_payload(
    hypothesis: CoachHypothesis,
    source_payload: Mapping[str, Any] | None,
    mission_payload: Mapping[str, Any] | None,
    *,
    criteria_specs: Sequence[Mapping[str, Any]],
    domain_key: str | None,
) -> dict[str, Any]:
    payload = dict(source_payload or {})
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    payload.update(
        {
            "source_hypothesis_id": hypothesis.id,
            "analysis_run_id": hypothesis.analysis_run_id,
            "source_insight_card_id": hypothesis.source_insight_card_id,
            "baseline_source": "coach_hypothesis_mission_readiness",
            "mission_readiness": readiness,
            "mission_domain_key": domain_key,
            "problem_key": domain_key,
            "activation_metadata": _mission_activation_metadata(
                hypothesis=hypothesis,
                readiness=readiness,
                criteria_specs=criteria_specs,
                domain_key=domain_key,
            ),
        }
    )
    if mission_payload is not None:
        payload["mission_payload"] = dict(mission_payload)
    return payload

def _mission_activation_metadata(
    *,
    hypothesis: CoachHypothesis,
    readiness: Mapping[str, Any],
    criteria_specs: Sequence[Mapping[str, Any]],
    domain_key: str | None,
) -> dict[str, Any]:
    primary = _primary_criteria_spec(criteria_specs)
    return {
        "source_hypothesis_id": hypothesis.id,
        "analysis_run_id": hypothesis.analysis_run_id,
        "source_insight_card_id": hypothesis.source_insight_card_id,
        "owner_steam_id": hypothesis.owner_steam_id,
        "domain_key": domain_key,
        "problem_key": domain_key,
        "primary_metric": primary.get("metric_name") if primary else None,
        "criteria_count": len(criteria_specs),
        "baseline_values": _criteria_values_by_metric(criteria_specs, "baseline_value"),
        "target_values": _criteria_values_by_metric(criteria_specs, "target_value"),
        "confidence_required": primary.get("confidence_required") if primary else None,
        "confidence_eligibility": _mapping(readiness.get("confidence_eligibility")),
        "window": _mapping(readiness.get("window")),
    }

def _mission_domain_key_from_parts(
    *,
    hypothesis: CoachHypothesis,
    criteria_specs: Sequence[Mapping[str, Any]],
    mission_payload: Mapping[str, Any] | None,
) -> str | None:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    source = _optional_str(readiness.get("source"))
    if source == "rolling_metric_window":
        window = _mapping(readiness.get("window"))
        candidate_source = _optional_str(window.get("candidate_family") or readiness.get("family"))
        if candidate_source:
            return _domain_key_for_family(candidate_source)
    mission_payload_metric = _mapping(_mapping(mission_payload).get("success_metric")).get("metric_name")
    if mission_payload_metric:
        return _domain_key_for_metric(str(mission_payload_metric))
    primary = _primary_criteria_spec(criteria_specs)
    if primary is not None:
        return _domain_key_for_metric(str(primary["metric_name"]))
    readiness_metric = _readiness_target_metric(
        readiness,
        _json_load_sequence(hypothesis.target_metric_candidates_json),
    )
    if readiness_metric:
        return _domain_key_for_metric(readiness_metric)
    return None

def _domain_key_for_metric(metric_name: str, *, family: str | None = None) -> str | None:
    if family:
        return _domain_key_for_family(family)
    if metric_name in BAD_FIGHT_TRADE_MISSION_METRICS or metric_name == "traded_death_rate":
        return "bad_fight_selection"
    if metric_name in SURVIVAL_OPENING_MISSION_METRICS or metric_name == "opening_duel_win_rate":
        return "bad_fight_selection"
    if metric_name in UTILITY_VALUE_MISSION_METRICS or metric_name.startswith(("utility_", "flash_", "he_")):
        return None
    return canonicalize_domain_key(metric_name)

def _domain_key_for_family(family: str) -> str | None:
    return canonical_domain_for_family(family)

def _criteria_values_by_metric(criteria_specs: Sequence[Mapping[str, Any]], field: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in criteria_specs:
        value = item.get(field)
        if value is None:
            continue
        metric_name = str(item["metric_name"])
        if item.get("role") == "primary" or metric_name not in values:
            values[metric_name] = value
    return values

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
    if primary_metric == EFFECTIVE_UTILITY_METRIC:
        return "Recover utility damage toward personal baseline"
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
        if metric_name == EFFECTIVE_UTILITY_METRIC:
            return (
                f"Recover recent effective enemy utility damage from {float(baseline):.3f} toward the player's "
                "preceding "
                f"personal baseline of {float(target):.3f} using supported owner metric snapshots."
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
    elif metric_name == EFFECTIVE_UTILITY_METRIC:
        rules = [
            "Measure recovery only with canonical owner-scoped effective_enemy_utility_damage observations.",
            (
                "Recover toward the preceding personal baseline without treating an absolute utility value "
                "as universally good or bad."
            ),
            "Treat a drop below the recent-segment activation baseline as further deterioration.",
            (
                "Do not infer grenade quality, lineup quality, flash value, or an exact tactical cause "
                "from utility damage."
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
        rounds = _optional_int(evidence.get("rounds_played"))
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
    if metric_name == EFFECTIVE_UTILITY_METRIC:
        return (
            "Mission guardrail triggers if effective_enemy_utility_damage drops below the recent "
            "personal-segment baseline."
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

__all__ = (
    'mission_domain_key',
    'mission_payload_from_hypothesis',
    'mission_payload_from_insight_card',
    'mission_problem_key',
    'serialize_mission_payload',
    'validate_mission_payload',
)
