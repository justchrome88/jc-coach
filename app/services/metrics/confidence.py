"""Metric confidence context and date-window policy."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from app.db.models import Match
from app.services.shared.match_queries import is_playable_match
from app.services.shared.metric_policy import metric_definition, usage_decision

EXACT_DATE_STATUS = "exact_match_date_available"
EXACT_DATE_SOURCE = "steam_gc_match_time"
APPROXIMATE_DATE_STATUS = "approximate_match_date"

ConfidenceLevel = str
CONFIDENCE_LEVELS = {"high", "medium", "low", "unavailable"}
_LEGACY_LEVELS = {
    "exact": "high",
    "trusted": "high",
    "partial": "medium",
    "low_confidence": "low",
}


METRIC_ATTRS = {
    "result": "result",
    "round_score": "rounds_for",
    "kills": "kills",
    "deaths": "deaths",
    "assists": "assists",
    "kd_ratio": "kd",
    "adr": "adr",
    "kast": "kast",
    "hltv_rating": "rating",
    "headshot_rate": "headshot_percent",
    "entry_kills": "entry_kills",
    "entry_deaths": "entry_deaths",
    "early_deaths": "early_deaths",
    "utility_damage": "utility_damage",
    "flash_assists": "flash_assists",
    "enemies_flashed": "enemies_flashed",
    "swing_score": "swing_score",
    "side_split_metrics": "side_t_rounds_won",
}

PARSER_CONFIDENCE_KEYS = {
    "adr": "adr",
    "kast": "kast",
    "entry_kills": "entry_duels",
    "entry_deaths": "entry_duels",
    "early_deaths": "early_deaths",
    "utility_damage": "utility",
    "flash_assists": "flash",
    "enemies_flashed": "flash",
    "swing_score": "swing",
    "headshot_rate": "weapon_accuracy",
    "side_split_metrics": "side_stats",
}


@dataclass
class MetricContext:
    matches: list[Match] = field(default_factory=list)
    raw_by_object_id: dict[int, dict[str, Any]] = field(default_factory=dict)
    window_cache: dict[tuple[tuple[int, ...], int], dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_matches(cls, matches: Iterable[Match]) -> MetricContext:
        return cls(list(matches))

    def raw(self, match: Match) -> dict[str, Any]:
        key = id(match)
        if key not in self.raw_by_object_id:
            self.raw_by_object_id[key] = _load_raw(match)
        return self.raw_by_object_id[key]


def metric_context(matches: Iterable[Match]) -> MetricContext:
    return MetricContext.from_matches(matches)


def sort_matches(matches: Iterable[Match]) -> list[Match]:
    return sorted(
        list(matches),
        key=lambda match: (match.played_at is None, match.played_at or match.created_at, match.id or 0),
    )


def exact_date_matches(matches: Iterable[Match], *, context: MetricContext | None = None) -> list[Match]:
    ctx = context or metric_context(matches)
    return [match for match in sort_matches(matches) if is_exact_date_match(match, context=ctx)]


def exact_recent_matches(matches: Iterable[Match], limit: int, *, context: MetricContext | None = None) -> list[Match]:
    if limit <= 0:
        return []
    return exact_date_matches(matches, context=context)[-limit:]


def exact_date_window_metadata(
    matches: Iterable[Match],
    *,
    required_sample: int = 15,
    context: MetricContext | None = None,
) -> dict[str, Any]:
    ctx = context or metric_context(matches)
    items = [match for match in sort_matches(matches) if is_playable_match(match)]
    cache_key = (tuple(id(match) for match in items), required_sample)
    if cache_key in ctx.window_cache:
        return dict(ctx.window_cache[cache_key])
    exact = [match for match in items if is_exact_date_match(match, context=ctx)]
    approximate = [match for match in items if is_approximate_date_match(match, context=ctx)]
    exact_ids = {id(match) for match in exact}
    approximate_ids = {id(match) for match in approximate}
    unknown = [match for match in items if id(match) not in exact_ids and id(match) not in approximate_ids]
    insufficient = len(exact) < required_sample
    metadata = {
        "total_playable_matches": len(items),
        "exact_date_matches": len(exact),
        "approximate_date_matches": len(approximate),
        "unknown_date_matches": len(unknown),
        "excluded_from_exact_windows": len(approximate) + len(unknown),
        "confidence": _sample_confidence(len(exact), required_sample),
        "insufficient_exact_sample": insufficient,
        "warnings": _window_warnings(len(exact), len(approximate), len(unknown), required_sample),
    }
    ctx.window_cache[cache_key] = metadata
    return dict(metadata)


def exact_period_windows(
    matches: Iterable[Match],
    *,
    current_n: int = 15,
    previous_n: int = 15,
    context: MetricContext | None = None,
) -> tuple[list[Match], list[Match], dict[str, Any]]:
    ctx = context or metric_context(matches)
    exact = exact_date_matches(matches, context=ctx)
    current = exact[-current_n:]
    previous = exact[-(current_n + previous_n) : -current_n] if len(exact) > current_n else []
    metadata = exact_date_window_metadata(matches, required_sample=current_n, context=ctx)
    metadata.update(
        {
            "current_requested": current_n,
            "previous_requested": previous_n,
            "current_exact_matches": len(current),
            "previous_exact_matches": len(previous),
        }
    )
    return current, previous, metadata


def metric_confidence(
    metric_id: str,
    matches: Iterable[Match],
    *,
    usage: str = "display",
    date_windowed: bool = False,
    min_sample: int = 5,
    context: MetricContext | None = None,
    date_window_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = context or metric_context(matches)
    items = [match for match in sort_matches(matches) if is_playable_match(match)]
    definition = metric_definition(metric_id)
    canonical_id = definition.metric_id
    attr = METRIC_ATTRS.get(canonical_id)
    present = sum(1 for match in items if _metric_present(match, canonical_id, attr))
    coverage = round(present / len(items) * 100, 2) if items else 0.0
    decision = usage_decision(canonical_id, usage) if canonical_id != "unknown" else "suppressed"
    parser_level = _parser_level(canonical_id, items, context=ctx)
    date_meta = (
        date_window_metadata
        if date_windowed and date_window_metadata is not None
        else exact_date_window_metadata(items, required_sample=min_sample, context=ctx)
        if date_windowed
        else None
    )
    reasons: list[str] = []
    reason_codes: list[str] = []

    if decision == "suppressed" or definition.reliability == "unavailable":
        level: ConfidenceLevel = "unavailable"
        reasons.append(f"{canonical_id} is {definition.reliability} and {decision} for {usage}.")
        reason_codes.append("metric_suppressed_for_usage")
    elif not items or present == 0:
        level = "unavailable"
        reasons.append(f"{canonical_id} has no populated values in this sample.")
        reason_codes.append("metric_no_populated_values")
    elif date_meta and date_meta["insufficient_exact_sample"]:
        level = "low"
        reasons.extend(date_meta["warnings"])
        reason_codes.append("insufficient_exact_date_sample")
    elif definition.reliability == "trusted" and parser_level in {"high", "unknown"} and len(items) >= min_sample:
        level = "high"
        reason_codes.append("trusted_metric_with_required_sample")
    elif definition.reliability in {"trusted", "medium"} and parser_level not in {"low", "unavailable"}:
        level = "medium"
        reason_codes.append("trusted_or_medium_metric_partial_support")
    else:
        level = "low"
        reason_codes.append("weak_metric_or_source")

    if definition.reliability in {"approximate", "low"}:
        reasons.append(f"{canonical_id} registry reliability is {definition.reliability}.")
        reason_codes.append("registry_reliability_limited")
    if parser_level in {"low", "unavailable"}:
        reasons.append(f"{canonical_id} parser confidence is {parser_level}.")
        reason_codes.append(f"parser_confidence_{parser_level}")
    if coverage < 100 and level != "unavailable":
        reasons.append(f"{canonical_id} coverage is {coverage}%.")
        reason_codes.append("metric_coverage_gap")

    record = confidence_record(
        canonical_id,
        level,
        usage=usage,
        reasons=reasons,
        reason_codes=reason_codes,
        source_trust={
            "registry_reliability": definition.reliability,
            "usage_decision": decision,
            "parser_confidence": parser_level,
            "sample_size": len(items),
            "present_count": present,
            "coverage": coverage,
        },
    )
    record.update(
        {
        "metric_id": canonical_id,
        "name": definition.display_name,
        "registry_reliability": definition.reliability,
        "usage_decision": decision,
        "sample_size": len(items),
        "present_count": present,
        "coverage": coverage,
        "parser_confidence": parser_level,
        "date_window": date_meta,
        }
    )
    return record


def metric_confidence_map(
    metric_ids: Iterable[str],
    matches: Iterable[Match],
    *,
    usage: str = "display",
    date_windowed: bool = False,
    min_sample: int = 5,
    context: MetricContext | None = None,
) -> dict[str, dict[str, Any]]:
    items = list(matches)
    ctx = context or metric_context(items)
    date_meta = exact_date_window_metadata(items, required_sample=min_sample, context=ctx) if date_windowed else None
    return {
        metric_definition(metric_id).metric_id: metric_confidence(
            metric_id,
            items,
            usage=usage,
            date_windowed=date_windowed,
            min_sample=min_sample,
            context=ctx,
            date_window_metadata=date_meta,
        )
        for metric_id in metric_ids
    }


def is_exact_date_match(match: Match, *, context: MetricContext | None = None) -> bool:
    if not match.played_at or not is_playable_match(match):
        return False
    raw = raw_match(match, context=context)
    nested = raw.get("match") if isinstance(raw.get("match"), dict) else {}
    status = raw.get("match_date_status") or nested.get("match_date_status")
    source = raw.get("match_date_source") or nested.get("match_date_source") or raw.get("played_at_source")
    if status == EXACT_DATE_STATUS and source == EXACT_DATE_SOURCE:
        return True
    if status == APPROXIMATE_DATE_STATUS or source in {"file_modified_fallback", "demo_header", "unavailable"}:
        return False
    return match.source not in {"demo", "steam_history"}


def is_approximate_date_match(match: Match, *, context: MetricContext | None = None) -> bool:
    raw = raw_match(match, context=context)
    nested = raw.get("match") if isinstance(raw.get("match"), dict) else {}
    status = raw.get("match_date_status") or nested.get("match_date_status")
    source = raw.get("match_date_source") or nested.get("match_date_source") or raw.get("played_at_source")
    return bool(match.played_at) and (
        status == APPROXIMATE_DATE_STATUS or source in {"file_modified_fallback", "demo_header"}
    )


def _metric_present(match: Match, canonical_id: str, attr: str | None) -> bool:
    if canonical_id == "round_score":
        return match.rounds_for is not None and match.rounds_against is not None
    return bool(attr and getattr(match, attr, None) is not None)


def _parser_level(canonical_id: str, matches: list[Match], *, context: MetricContext) -> str:
    key = PARSER_CONFIDENCE_KEYS.get(canonical_id)
    if key is None:
        return "unknown"
    values = []
    for match in matches:
        metric_conf = context.raw(match).get("metric_confidence")
        if isinstance(metric_conf, dict) and metric_conf.get(key):
            values.append(str(metric_conf[key]))
    if not values:
        return "unknown"
    rank = {"unavailable": 0, "low": 1, "medium": 2, "high": 3}
    return min(values, key=lambda value: rank.get(value, 1))


def _sample_confidence(exact_count: int, required_sample: int) -> str:
    if exact_count >= required_sample:
        return "high"
    if exact_count >= max(5, required_sample // 2):
        return "medium"
    if exact_count > 0:
        return "low"
    return "unavailable"


def _window_warnings(exact_count: int, approximate_count: int, unknown_count: int, required_sample: int) -> list[str]:
    warnings = []
    if approximate_count or unknown_count:
        warnings.append(
            f"{approximate_count + unknown_count} non-exact matches excluded from exact date windows."
        )
    if exact_count < required_sample:
        warnings.append(f"Only {exact_count} exact-date matches available; requested sample is {required_sample}.")
    return warnings


def raw_match(match: Match, *, context: MetricContext | None = None) -> dict[str, Any]:
    if context is not None:
        return context.raw(match)
    return _load_raw(match)


def _raw(match: Match) -> dict[str, Any]:
    return _load_raw(match)


def _load_raw(match: Match) -> dict[str, Any]:
    if not match.raw_json:
        return {}
    try:
        loaded = json.loads(match.raw_json)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def normalize_confidence_level(level: Any) -> ConfidenceLevel:
    normalized = str(level or "").strip().lower()
    normalized = _LEGACY_LEVELS.get(normalized, normalized)
    return normalized if normalized in CONFIDENCE_LEVELS else "unavailable"


def confidence_record(
    metric_id: str,
    level: Any,
    *,
    usage: str = "display",
    reasons: Iterable[str] = (),
    reason_codes: Iterable[str] = (),
    source_trust: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_confidence_level(level)
    definition = metric_definition(metric_id)
    decision = usage_decision(definition.metric_id, usage) if definition.metric_id != "unknown" else "suppressed"
    codes = _ordered_unique([str(code) for code in reason_codes if str(code).strip()])
    if normalized == "low":
        codes.append("low_confidence_blocks_hard_recommendation")
    elif normalized == "unavailable":
        codes.append("unavailable_metric_blocks_hard_recommendation")
    if decision == "warn":
        codes.append("warn_metric_requires_caveat")
    elif decision == "suppressed":
        codes.append("suppressed_metric_blocks_hard_recommendation")

    hard_eligible = normalized in {"high", "medium"} and decision == "allowed"
    insight_usable = normalized in {"high", "medium"} and decision != "suppressed"
    trust = {
        "registry_reliability": definition.reliability,
        "usage_decision": decision,
    }
    if source_trust:
        trust.update(source_trust)

    return {
        "level": normalized,
        "reasons": _ordered_unique([str(reason) for reason in reasons if str(reason).strip()]),
        "reason_codes": _ordered_unique(codes),
        "source_trust": trust,
        "usable_for_insights": insight_usable,
        "usable_for_missions": hard_eligible,
        "hard_recommendation_eligible": hard_eligible,
    }


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered
