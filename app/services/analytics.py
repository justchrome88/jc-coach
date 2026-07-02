from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from app.db.models import Match
from app.services.aim_stats import match_aim_profile

KEY_METRICS = (
    "winrate",
    "kd",
    "adr",
    "kast",
    "rating",
    "swing_score",
    "entry_diff",
    "utility_damage",
    "flash_assists",
    "deaths",
)


def get_summary(matches: Iterable[Match]) -> dict[str, Any]:
    items = _sort_matches(matches)
    count = len(items)
    wins = sum(1 for match in items if match.result == "win")
    losses = sum(1 for match in items if match.result == "loss")
    rounds_for = _sum(items, "rounds_for")
    rounds_against = _sum(items, "rounds_against")
    return {
        "matches_count": count,
        "wins": wins,
        "losses": losses,
        "winrate": _percent(wins, count),
        "avg_kd": _avg(items, "kd"),
        "avg_adr": _avg(items, "adr"),
        "avg_kast": _avg(items, "kast"),
        "avg_rating": _avg(items, "rating"),
        "avg_swing_score": _avg(items, "swing_score"),
        "avg_headshot_percent": _avg(items, "headshot_percent"),
        "avg_deaths": _avg(items, "deaths"),
        "avg_utility_damage": _avg(items, "utility_damage"),
        "avg_flash_assists": _avg(items, "flash_assists"),
        "entry_kills": _sum(items, "entry_kills"),
        "entry_deaths": _sum(items, "entry_deaths"),
        "entry_diff": _sum(items, "entry_kills") - _sum(items, "entry_deaths"),
        "round_diff": rounds_for - rounds_against,
        "rounds_for": rounds_for,
        "rounds_against": rounds_against,
        "form_score": calculate_form_score(items[-15:]),
        "recent_results": [match.result for match in items[-15:]],
        "available_metrics": _available_metrics(items),
    }


def get_dashboard_status(matches: Iterable[Match]) -> dict[str, Any]:
    items = _sort_matches(matches)
    recent = items[-15:]
    previous = items[-30:-15] if len(items) > 15 else []
    return {
        "source_breakdown": get_source_breakdown(items),
        "adr_profile": get_adr_profile(items),
        "data_quality": get_data_quality(items),
        "session": {
            "recent_matches": len(recent),
            "previous_matches": len(previous),
            "recent_winrate": _percent(sum(1 for match in recent if match.result == "win"), len(recent)),
            "recent_avg_adr": _avg(recent, "adr"),
            "recent_avg_kast": _avg(recent, "kast"),
            "recent_avg_swing_score": _avg(recent, "swing_score"),
        },
    }


def get_source_breakdown(matches: Iterable[Match]) -> list[dict[str, Any]]:
    buckets: dict[str, list[Match]] = defaultdict(list)
    for match in matches:
        buckets[match.source or "unknown"].append(match)
    return [
        {
            "source": source,
            "matches_count": len(items),
            "avg_adr": _avg(items, "adr"),
            "avg_kast": _avg(items, "kast"),
            "avg_swing_score": _avg(items, "swing_score"),
            "winrate": _percent(sum(1 for match in items if match.result == "win"), len(items)),
        }
        for source, items in sorted(buckets.items())
    ]


def get_data_quality(matches: Iterable[Match]) -> dict[str, Any]:
    items = _sort_matches(matches)
    total = len(items)
    required_fields = {
        "result": "result",
        "score": "rounds_for",
        "kills": "kills",
        "deaths": "deaths",
        "ADR": "adr",
        "KAST": "kast",
        "Swing": "swing_score",
        "entry": "entry_kills",
    }
    coverage = {
        name: _percent(sum(1 for match in items if getattr(match, attr, None) is not None), total) or 0
        for name, attr in required_fields.items()
    }
    if total == 0:
        label = "Нет данных"
    else:
        average_coverage = sum(coverage.values()) / len(coverage)
        label = "Высокое" if average_coverage >= 85 else "Среднее" if average_coverage >= 60 else "Низкое"
    return {"matches_count": total, "coverage": coverage, "label": label}


def get_adr_profile(matches: Iterable[Match]) -> dict[str, Any]:
    items = _sort_matches(matches)
    with_adr = [match for match in items if match.adr is not None]
    recent = items[-15:]
    previous = items[-30:-15] if len(items) > 15 else []
    best = max(with_adr, key=lambda match: match.adr or 0, default=None)
    worst = min(with_adr, key=lambda match: match.adr or 0, default=None)
    coverage = _percent(len(with_adr), len(items)) or 0
    recent_adr = _avg(recent, "adr")
    previous_adr = _avg(previous, "adr")
    confidence = "high" if coverage >= 90 and len(with_adr) >= 10 else "medium" if coverage >= 60 else "low"
    return {
        "average": _avg(items, "adr"),
        "recent_average": recent_adr,
        "previous_average": previous_adr,
        "delta": _delta(recent_adr, previous_adr),
        "coverage": coverage,
        "confidence": confidence,
        "best_match": best,
        "worst_match": worst,
        "source_breakdown": get_source_breakdown(with_adr),
        "interpretation": _adr_interpretation(recent_adr or _avg(items, "adr"), confidence),
    }


def compare_periods(matches: Iterable[Match], current_n: int = 15, previous_n: int = 15) -> dict[str, Any]:
    items = _sort_matches(matches)
    current = items[-current_n:]
    previous = items[-(current_n + previous_n) : -current_n] if len(items) > current_n else []
    current_summary = get_summary(current)
    previous_summary = get_summary(previous)
    metric_map = {
        "winrate": ("winrate", "pp"),
        "kd": ("avg_kd", ""),
        "adr": ("avg_adr", ""),
        "kast": ("avg_kast", "pp"),
        "rating": ("avg_rating", ""),
        "swing_score": ("avg_swing_score", "pp/round"),
        "entry_diff": ("entry_diff", ""),
        "utility_damage": ("avg_utility_damage", ""),
        "flash_assists": ("avg_flash_assists", ""),
        "deaths": ("avg_deaths", ""),
    }
    deltas = {}
    worsened = []
    for public_name, (summary_key, unit) in metric_map.items():
        current_value = current_summary.get(summary_key)
        previous_value = previous_summary.get(summary_key)
        delta = _delta(current_value, previous_value)
        deltas[public_name] = {"current": current_value, "previous": previous_value, "delta": delta, "unit": unit}
        if delta is not None and _is_worse(public_name, delta):
            worsened.append(public_name)

    return {
        "current_n": len(current),
        "previous_n": len(previous),
        "current": current_summary,
        "previous": previous_summary,
        "deltas": deltas,
        "worsened_metrics": worsened,
        "trend": "down" if len(worsened) >= 3 else "stable",
    }


def get_map_stats(matches: Iterable[Match]) -> list[dict[str, Any]]:
    buckets: dict[str, list[Match]] = defaultdict(list)
    for match in matches:
        buckets[match.map_name or "Unknown"].append(match)

    stats = []
    for map_name, items in buckets.items():
        summary = get_summary(items)
        stats.append(
            {
                "map_name": map_name,
                "matches_count": summary["matches_count"],
                "winrate": summary["winrate"],
                "avg_kd": summary["avg_kd"],
                "avg_adr": summary["avg_adr"],
                "avg_kast": summary["avg_kast"],
                "avg_rating": summary["avg_rating"],
                "avg_swing_score": summary["avg_swing_score"],
                "entry_diff": summary["entry_diff"],
                "avg_utility_damage": summary["avg_utility_damage"],
                "t_round_winrate": _side_winrate(items, "side_t_rounds_won", "side_t_rounds_lost"),
                "ct_round_winrate": _side_winrate(items, "side_ct_rounds_won", "side_ct_rounds_lost"),
            }
        )
    return sorted(stats, key=lambda item: (item["winrate"] if item["winrate"] is not None else -1), reverse=True)


def detect_weaknesses(
    summary: dict[str, Any],
    comparison: dict[str, Any],
    map_stats: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    weaknesses: list[dict[str, Any]] = []
    if summary["matches_count"] == 0:
        return weaknesses

    if (summary.get("avg_kd") or 0) >= 1.0 and (summary.get("winrate") or 0) < 50:
        weaknesses.append(
            _weakness(
                "Низкая конверсия статистики в победы",
                "decision_making",
                "medium",
                "K/D выглядит рабочим, но winrate низкий. Нужно разобрать смерти и решения в ключевых раундах.",
            )
        )
    if _worse_delta(comparison, "adr", -5) or (summary.get("avg_adr") is not None and summary["avg_adr"] < 72):
        weaknesses.append(
            _weakness(
                "ADR не создаёт достаточно давления",
                "aim_duels",
                "high",
                "Средний урон ниже уровня, который помогает стабильно закрывать раунды.",
            )
        )
    if summary.get("avg_kast") is not None and summary["avg_kast"] < 70:
        weaknesses.append(
            _weakness(
                "Низкий KAST",
                "survival",
                "high",
                "Слишком много раундов выпадает из-за ранних смертей, слабого трейда или низкого участия.",
            )
        )
    if (summary.get("entry_deaths") or 0) > (summary.get("entry_kills") or 0):
        weaknesses.append(
            _weakness(
                "Дисциплина первых дуэлей",
                "entry_duels",
                "high",
                "Entry deaths выше entry kills. Первые дуэли нужно брать только с понятным разменом.",
            )
        )
    if summary.get("avg_utility_damage") is not None and summary["avg_utility_damage"] < 70:
        weaknesses.append(
            _weakness(
                "Низкий impact гранат",
                "utility",
                "medium",
                "Utility damage низкий. Нужны повторяемые grenade routines на слабых картах.",
            )
        )
    if comparison.get("trend") == "down":
        weaknesses.append(
            _weakness(
                "Форма проседает",
                "discipline",
                "high",
                "Последний период хуже минимум по трём ключевым метрикам. Сначала нужна стабилизация.",
            )
        )

    for item in map_stats:
        if item["matches_count"] >= 3 and (item["winrate"] or 0) < 45:
            weaknesses.append(
                _weakness(
                    f"Слабая карта: {item['map_name']}",
                    "map_specific",
                    "medium",
                    f"Winrate на {item['map_name']} равен {item['winrate']}%. Нужен отдельный план по карте.",
                )
            )

    return weaknesses[:6]


def calculate_form_score(matches: Iterable[Match]) -> float | None:
    items = _sort_matches(matches)
    if not items:
        return None
    score = 0.0
    for match in items:
        score += 45 if match.result == "win" else 15 if match.result == "loss" else 25
        score += min(((match.kd or 0) - 0.8) * 18, 18)
        score += min(((match.adr or 0) - 65) * 0.35, 14)
        score += min(((match.kast or 0) - 65) * 0.35, 12)
        score += min(((match.rating or 0) - 0.9) * 24, 12)
        score += min(max((match.swing_score or 0) * 2.5, -8), 8)
    return round(max(0, min(100, score / len(items))), 1)


def chart_series(matches: Iterable[Match], limit: int = 30) -> dict[str, Any]:
    items = _sort_matches(matches)[-limit:]
    return {
        "labels": [match.played_at.strftime("%m-%d") if match.played_at else f"#{match.id}" for match in items],
        "kd": [match.kd for match in items],
        "adr": [match.adr for match in items],
        "kast": [match.kast for match in items],
        "rating": [match.rating for match in items],
        "swing": [match.swing_score for match in items],
    }


def match_detail(match: Match) -> dict[str, Any]:
    adr_note = _adr_interpretation(match.adr, "single")
    rounds = (match.rounds_for or 0) + (match.rounds_against or 0)
    parser_evidence = _parser_evidence(match)
    return {
        "score": f"{match.rounds_for or 0}:{match.rounds_against or 0}",
        "rounds": rounds or None,
        "adr_note": adr_note,
        "source_label": (match.source or "unknown").upper(),
        "has_demo": bool(match.demo_file),
        "parser_evidence": parser_evidence,
        "aim_profile": match_aim_profile(match),
        "combat": {
            "kills": match.kills,
            "deaths": match.deaths,
            "assists": match.assists,
            "kd": match.kd,
            "adr": match.adr,
            "kast": match.kast,
            "rating": match.rating,
            "swing_score": match.swing_score,
            "headshot_percent": match.headshot_percent,
        },
        "opening": {
            "entry_kills": match.entry_kills,
            "entry_deaths": match.entry_deaths,
            "early_deaths": match.early_deaths,
        },
        "utility": {
            "utility_damage": match.utility_damage,
            "flash_assists": match.flash_assists,
            "enemies_flashed": match.enemies_flashed,
        },
        "sides": {
            "t": _side_record(match.side_t_rounds_won, match.side_t_rounds_lost),
            "ct": _side_record(match.side_ct_rounds_won, match.side_ct_rounds_lost),
        },
    }


def _parser_evidence(match: Match) -> dict[str, Any] | None:
    if not match.raw_json:
        return None
    try:
        raw = json.loads(match.raw_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict) or raw.get("parser") != "demoparser2":
        return None
    return {
        "parser": raw.get("parser"),
        "confidence": raw.get("parser_confidence", "unknown"),
        "event_counts": raw.get("event_counts", {}),
        "metric_confidence": raw.get("metric_confidence", {}),
        "warnings": raw.get("warnings", []),
        "player": raw.get("player", {}),
        "available_players": raw.get("available_players", []),
    }


def _weakness(title: str, category: str, severity: str, evidence: str) -> dict[str, str]:
    return {"title": title, "category": category, "severity": severity, "evidence": evidence}


def _sort_matches(matches: Iterable[Match]) -> list[Match]:
    return sorted(
        list(matches),
        key=lambda match: (match.played_at is None, match.played_at or match.created_at, match.id or 0),
    )


def _avg(items: list[Match], attr: str) -> float | None:
    values = [getattr(item, attr) for item in items if getattr(item, attr) is not None]
    return round(sum(values) / len(values), 2) if values else None


def _sum(items: list[Match], attr: str) -> int:
    return int(sum(getattr(item, attr) or 0 for item in items))


def _percent(part: int, total: int) -> float | None:
    return round(part / total * 100, 1) if total else None


def _delta(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 2)


def _is_worse(metric: str, delta: float) -> bool:
    return delta > 0 if metric == "deaths" else delta < 0


def _worse_delta(comparison: dict[str, Any], metric: str, threshold: float) -> bool:
    delta = comparison.get("deltas", {}).get(metric, {}).get("delta")
    return delta is not None and delta <= threshold


def _side_winrate(items: list[Match], won_attr: str, lost_attr: str) -> float | None:
    won = _sum(items, won_attr)
    lost = _sum(items, lost_attr)
    return _percent(won, won + lost)


def _side_record(won: int | None, lost: int | None) -> dict[str, Any]:
    won_value = won or 0
    lost_value = lost or 0
    return {"won": won, "lost": lost, "winrate": _percent(won_value, won_value + lost_value)}


def _adr_interpretation(adr: float | None, confidence: str) -> str:
    if adr is None:
        return "ADR недоступен для этого набора данных."
    if adr >= 90:
        level = "очень сильный урон"
    elif adr >= 80:
        level = "хороший урон"
    elif adr >= 70:
        level = "рабочий, но нестабильный урон"
    else:
        level = "низкое давление по урону"
    if confidence == "low":
        return f"{level}; вывод осторожный, потому что ADR заполнен не во всех матчах."
    if confidence == "single":
        return f"{level} в этом матче."
    return f"{level}; доверие к ADR: {confidence}."


def _available_metrics(items: list[Match]) -> list[str]:
    available = []
    for field in KEY_METRICS:
        attr = {"winrate": "result", "entry_diff": "entry_kills", "deaths": "deaths"}.get(field, field)
        if any(getattr(item, attr, None) is not None for item in items):
            available.append(field)
    return available
