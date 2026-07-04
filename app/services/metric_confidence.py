from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from app.db.models import Match
from app.services.match_queries import is_playable_match
from app.services.metric_truth import metric_definition, usage_decision

EXACT_DATE_STATUS = "exact_match_date_available"
EXACT_DATE_SOURCE = "steam_gc_match_time"
APPROXIMATE_DATE_STATUS = "approximate_match_date"

ConfidenceLevel = str


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

    if decision == "suppressed" or definition.reliability == "unavailable":
        level: ConfidenceLevel = "unavailable"
        reasons.append(f"{canonical_id} is {definition.reliability} and {decision} for {usage}.")
    elif not items or present == 0:
        level = "unavailable"
        reasons.append(f"{canonical_id} has no populated values in this sample.")
    elif date_meta and date_meta["insufficient_exact_sample"]:
        level = "low_confidence"
        reasons.extend(date_meta["warnings"])
    elif definition.reliability == "trusted" and parser_level in {"high", "unknown"} and len(items) >= min_sample:
        level = "exact"
    elif definition.reliability in {"trusted", "medium"} and parser_level not in {"low", "unavailable"}:
        level = "partial"
    else:
        level = "low_confidence"

    if definition.reliability in {"approximate", "low"}:
        reasons.append(f"{canonical_id} registry reliability is {definition.reliability}.")
    if parser_level in {"low", "unavailable"}:
        reasons.append(f"{canonical_id} parser confidence is {parser_level}.")
    if coverage < 100 and level != "unavailable":
        reasons.append(f"{canonical_id} coverage is {coverage}%.")

    return {
        "metric_id": canonical_id,
        "name": definition.display_name,
        "level": level,
        "registry_reliability": definition.reliability,
        "usage_decision": decision,
        "sample_size": len(items),
        "present_count": present,
        "coverage": coverage,
        "parser_confidence": parser_level,
        "date_window": date_meta,
        "reasons": reasons,
    }


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
        return "exact"
    if exact_count >= max(5, required_sample // 2):
        return "partial"
    if exact_count > 0:
        return "low_confidence"
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
