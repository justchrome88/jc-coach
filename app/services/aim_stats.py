from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from app.db.models import Match
from app.services.metric_confidence import (
    MetricContext,
    exact_period_windows,
    metric_confidence_map,
    metric_context,
    raw_match,
    sort_matches,
)

AIM_DATA_GAPS = [
    "accuracy requires reliable weapon_fire and hit correlation",
    "first_bullet_accuracy requires shot timeline",
    "spray_control requires bullet trajectory data",
    "ttk requires precise damage/death timing",
    "crosshair_placement requires view angles and position timeline",
]


def get_aim_profile(matches: Iterable[Match], *, context: MetricContext | None = None) -> dict[str, Any]:
    items = sort_matches(matches)
    ctx = context or metric_context(items)
    recent, previous, window_meta = exact_period_windows(items, context=ctx)
    weapon_breakdown = _aggregate_weapon_breakdown(items, context=ctx)
    return {
        "matches_count": len(items),
        "averages": {
            "adr": _avg(items, "adr"),
            "kd": _avg(items, "kd"),
            "headshot_percent": _avg(items, "headshot_percent"),
            "damage_per_death": _avg_aim_summary(items, "damage_per_death", context=ctx),
            "opening_duel_success": _opening_duel_success(items),
            "multi_kill_rounds": _sum_aim_summary(items, "multi_kill_rounds", context=ctx),
        },
        "recent": {
            "matches_count": len(recent),
            "adr": _avg(recent, "adr"),
            "headshot_percent": _avg(recent, "headshot_percent"),
            "opening_duel_success": _opening_duel_success(recent),
        },
        "previous": {
            "matches_count": len(previous),
            "adr": _avg(previous, "adr"),
            "headshot_percent": _avg(previous, "headshot_percent"),
            "opening_duel_success": _opening_duel_success(previous),
        },
        "deltas": {
            "adr": _delta(_avg(recent, "adr"), _avg(previous, "adr")),
            "headshot_percent": _delta(_avg(recent, "headshot_percent"), _avg(previous, "headshot_percent")),
            "opening_duel_success": _delta(_opening_duel_success(recent), _opening_duel_success(previous)),
        },
        "weapon_breakdown": weapon_breakdown,
        "top_weapons": sorted(
            weapon_breakdown.values(),
            key=lambda item: (item["kills"], item["damage"]),
            reverse=True,
        )[:8],
        "coverage": _coverage(items, context=ctx),
        "confidence": _confidence(items, weapon_breakdown, context=ctx),
        "metric_confidence": metric_confidence_map(
            ("adr", "kd_ratio", "headshot_rate", "entry_deaths"),
            items,
            date_windowed=True,
            min_sample=15,
            context=ctx,
        ),
        "date_window": window_meta,
        "data_gaps": AIM_DATA_GAPS,
        "interpretation": _interpretation(items, weapon_breakdown),
    }


def match_aim_profile(match: Match) -> dict[str, Any]:
    raw = _raw(match)
    aim_summary = raw.get("aim_summary") if isinstance(raw.get("aim_summary"), dict) else {}
    weapon_breakdown = raw.get("weapon_breakdown") if isinstance(raw.get("weapon_breakdown"), dict) else {}
    entry_attempts = (match.entry_kills or 0) + (match.entry_deaths or 0)
    return {
        "adr": match.adr,
        "kd": match.kd,
        "headshot_percent": match.headshot_percent,
        "damage_per_death": aim_summary.get("damage_per_death"),
        "opening_duel_success": round((match.entry_kills or 0) / entry_attempts * 100, 2) if entry_attempts else None,
        "multi_kill_rounds": aim_summary.get("multi_kill_rounds"),
        "weapon_breakdown": weapon_breakdown,
        "top_weapons": sorted(
            weapon_breakdown.values(),
            key=lambda item: (item.get("kills") or 0, item.get("damage") or 0),
            reverse=True,
        )[:5],
        "data_gaps": raw.get("aim_data_gaps") or AIM_DATA_GAPS,
    }


def _aggregate_weapon_breakdown(
    matches: list[Match],
    *,
    context: MetricContext | None = None,
) -> dict[str, dict[str, Any]]:
    aggregate: dict[str, dict[str, Any]] = {}
    for match in matches:
        weapon_breakdown = raw_match(match, context=context).get("weapon_breakdown")
        if not isinstance(weapon_breakdown, dict):
            continue
        for weapon, stats in weapon_breakdown.items():
            if not isinstance(stats, dict):
                continue
            bucket = aggregate.setdefault(
                str(weapon),
                {"weapon": str(weapon), "kills": 0, "headshots": 0, "deaths": 0, "damage": 0, "matches": 0},
            )
            bucket["kills"] += int(stats.get("kills") or 0)
            bucket["headshots"] += int(stats.get("headshots") or 0)
            bucket["deaths"] += int(stats.get("deaths") or 0)
            bucket["damage"] += int(stats.get("damage") or 0)
            bucket["matches"] += 1
    for bucket in aggregate.values():
        bucket["headshot_percent"] = (
            round(bucket["headshots"] / bucket["kills"] * 100, 2) if bucket["kills"] else None
        )
    return aggregate


def _coverage(matches: list[Match], *, context: MetricContext | None = None) -> dict[str, float]:
    ctx = context or metric_context(matches)
    total = len(matches)
    return {
        "adr": _percent(sum(1 for match in matches if match.adr is not None), total),
        "headshot_percent": _percent(sum(1 for match in matches if match.headshot_percent is not None), total),
        "opening_duels": _percent(
            sum(1 for match in matches if (match.entry_kills or 0) + (match.entry_deaths or 0) > 0),
            total,
        ),
        "weapon_breakdown": _percent(
            sum(1 for match in matches if isinstance(raw_match(match, context=ctx).get("weapon_breakdown"), dict)),
            total,
        ),
    }


def _confidence(
    matches: list[Match],
    weapon_breakdown: dict[str, Any],
    *,
    context: MetricContext | None = None,
) -> str:
    coverage = _coverage(matches, context=context)
    if len(matches) >= 10 and coverage["adr"] >= 80 and coverage["weapon_breakdown"] >= 60:
        return "high"
    if len(matches) >= 3 and coverage["adr"] >= 60:
        return "medium"
    if weapon_breakdown or coverage["adr"] > 0:
        return "low"
    return "no_data"


def _interpretation(matches: list[Match], weapon_breakdown: dict[str, Any]) -> str:
    if not matches:
        return "Aim profile появится после импорта матчей."
    adr = _avg(matches, "adr")
    hs = _avg(matches, "headshot_percent")
    if adr is None:
        return "Недостаточно ADR данных для aim вывода."
    if adr >= 85 and (hs or 0) >= 35:
        return "Aim impact выглядит сильным: ADR и HS% держатся высоко."
    if adr >= 75:
        return "Aim impact рабочий, следующий шаг - стабильность opening duels и weapon breakdown."
    return "Aim pressure низкий: нужно поднимать damage per round и качество первых контактов."


def _opening_duel_success(matches: list[Match]) -> float | None:
    kills = sum(match.entry_kills or 0 for match in matches)
    deaths = sum(match.entry_deaths or 0 for match in matches)
    attempts = kills + deaths
    return round(kills / attempts * 100, 2) if attempts else None


def _avg_aim_summary(
    matches: list[Match],
    key: str,
    *,
    context: MetricContext | None = None,
) -> float | None:
    values = []
    for match in matches:
        value = raw_match(match, context=context).get("aim_summary", {}).get(key)
        if value is not None:
            values.append(float(value))
    return round(sum(values) / len(values), 2) if values else None


def _sum_aim_summary(
    matches: list[Match],
    key: str,
    *,
    context: MetricContext | None = None,
) -> int:
    total = 0
    for match in matches:
        total += int(raw_match(match, context=context).get("aim_summary", {}).get(key) or 0)
    return total


def _avg(matches: list[Match], attr: str) -> float | None:
    values = [getattr(match, attr) for match in matches if getattr(match, attr) is not None]
    return round(sum(values) / len(values), 2) if values else None


def _delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 2)


def _percent(value: int, total: int) -> float:
    return round(value / total * 100, 2) if total else 0.0


def _raw(match: Match) -> dict[str, Any]:
    if not match.raw_json:
        return {}
    try:
        loaded = json.loads(match.raw_json)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _sort_matches(matches: Iterable[Match]) -> list[Match]:
    return sort_matches(matches)
