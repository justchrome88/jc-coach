from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.db.models import Match
from app.services.analytics import get_map_stats, get_summary

MISTAKE_CATEGORIES = {
    "aim": "Aim",
    "map": "Map",
    "crosshair_placement": "Crosshair placement",
    "grenades": "Grenades",
    "entry_duels": "Entry duels",
    "survival": "Survival",
    "utility": "Utility",
    "economy": "Economy",
}


def detect_structured_mistakes(matches: list[Match]) -> list[dict[str, Any]]:
    if not matches:
        return []
    ordered = sorted(matches, key=lambda match: (match.played_at is None, match.played_at, match.id or 0))
    summary = get_summary(ordered)
    mistakes: list[dict[str, Any]] = []
    mistakes.extend(_global_mistakes(summary))
    mistakes.extend(_map_mistakes(ordered))
    mistakes.extend(_match_mistakes(ordered[-15:]))
    return _prioritize(mistakes)


def mistakes_by_match_id(matches: list[Match]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for mistake in detect_structured_mistakes(matches):
        match_id = mistake.get("match_id")
        if match_id is not None:
            grouped[int(match_id)].append(mistake)
    return dict(grouped)


def category_scorecard(mistakes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scorecard = []
    for category, label in MISTAKE_CATEGORIES.items():
        items = [mistake for mistake in mistakes if mistake["category"] == category]
        severity_points = sum({"high": 3, "medium": 2, "low": 1}.get(item["severity"], 1) for item in items)
        if not items:
            status = "ok" if category not in {"crosshair_placement", "economy"} else "no_data"
            score = 100 if status == "ok" else None
        else:
            score = max(0, 100 - severity_points * 12)
            status = "critical" if score < 55 else "watch" if score < 80 else "ok"
        scorecard.append(
            {
                "category": category,
                "label": label,
                "status": status,
                "score": score,
                "mistakes_count": len(items),
                "top_mistake": items[0] if items else None,
            }
        )
    return scorecard


def match_coach_sections(match: Match, mistakes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entry_problem = (match.entry_deaths or 0) > (match.entry_kills or 0)
    if any(item["severity"] == "high" for item in mistakes):
        mistakes_status = "critical"
    elif mistakes:
        mistakes_status = "watch"
    else:
        mistakes_status = "ok"
    return [
        {
            "title": "Aim",
            "status": _status_from_metric(match.adr, good=80, watch=70, higher_is_better=True),
            "metrics": {"ADR": match.adr, "K/D": match.kd, "HS%": match.headshot_percent},
            "note": _aim_note(match),
        },
        {
            "title": "Entry duels",
            "status": "watch" if entry_problem else "ok",
            "metrics": {"Entry kills": match.entry_kills, "Entry deaths": match.entry_deaths},
            "note": "Первые контакты проиграны чаще, чем выиграны."
            if entry_problem
            else "Entry баланс не выглядит проблемным.",
        },
        {
            "title": "Survival",
            "status": _status_from_metric(match.kast, good=74, watch=68, higher_is_better=True),
            "metrics": {"KAST": match.kast, "Early deaths": match.early_deaths},
            "note": _survival_note(match),
        },
        {
            "title": "Grenades",
            "status": _status_from_metric(match.utility_damage, good=80, watch=40, higher_is_better=True),
            "metrics": {
                "Utility damage": match.utility_damage,
                "Flash assists": match.flash_assists,
                "Enemies flashed": match.enemies_flashed,
            },
            "note": _utility_note(match),
        },
        {
            "title": "Mistakes",
            "status": mistakes_status,
            "metrics": {"Detected": len(mistakes)},
            "note": mistakes[0]["title"] if mistakes else "Критичных структурных ошибок по этому матчу не найдено.",
        },
    ]


def _global_mistakes(summary: dict[str, Any]) -> list[dict[str, Any]]:
    mistakes = []
    if summary.get("avg_adr") is not None and summary["avg_adr"] < 70:
        mistakes.append(
            _mistake(
                "low_adr_pressure",
                "Aim pressure is too low",
                "aim",
                "high",
                "medium",
                {"avg_adr": summary["avg_adr"], "threshold": 70},
                "Играть следующие матчи с целью держать ADR 75+ без увеличения entry deaths.",
            )
        )
    if summary.get("avg_kast") is not None and summary["avg_kast"] < 68:
        mistakes.append(
            _mistake(
                "low_kast_participation",
                "Low round participation",
                "survival",
                "high",
                "medium",
                {"avg_kast": summary["avg_kast"], "threshold": 68},
                "Снизить изолированные смерти и играть от трейда в первых 40 секундах раунда.",
            )
        )
    if (summary.get("entry_deaths") or 0) > (summary.get("entry_kills") or 0):
        mistakes.append(
            _mistake(
                "bad_entry_duels",
                "Entry deaths exceed entry kills",
                "entry_duels",
                "high",
                "high",
                {"entry_kills": summary.get("entry_kills"), "entry_deaths": summary.get("entry_deaths")},
                "Брать первый контакт только с флешкой, инфой или готовым разменом.",
            )
        )
    if summary.get("avg_utility_damage") is not None and summary["avg_utility_damage"] < 45:
        mistakes.append(
            _mistake(
                "weak_utility_impact",
                "Low utility impact",
                "grenades",
                "medium",
                "medium",
                {"avg_utility_damage": summary["avg_utility_damage"], "threshold": 45},
                "Выбрать 2 карты и отработать повторяемые HE/molotov timings под частые позиции.",
            )
        )
    mistakes.append(
        _mistake(
            "crosshair_placement_no_data",
            "Crosshair placement cannot be evaluated yet",
            "crosshair_placement",
            "low",
            "low",
            {"required_data": "player view angles and position timeline"},
            "Пока не делаем выводы по постановке прицела, пока parser не дает надежные view/position данные.",
        )
    )
    return mistakes


def _map_mistakes(matches: list[Match]) -> list[dict[str, Any]]:
    mistakes = []
    for item in get_map_stats(matches):
        if item["matches_count"] >= 2 and (item["winrate"] or 0) < 45:
            mistakes.append(
                _mistake(
                    "weak_map",
                    f"Weak map: {item['map_name']}",
                    "map",
                    "medium",
                    "medium",
                    {
                        "map_name": item["map_name"],
                        "matches_count": item["matches_count"],
                        "winrate": item["winrate"],
                        "avg_adr": item["avg_adr"],
                    },
                    f"Сузить план на {item['map_name']}: первые смерти, T/CT сторона и 3 повторяемых opening сценария.",
                )
            )
    return mistakes


def _match_mistakes(matches: list[Match]) -> list[dict[str, Any]]:
    mistakes = []
    for match in matches:
        if match.id is None:
            continue
        if (match.entry_deaths or 0) >= 3:
            mistakes.append(
                _mistake(
                    "match_early_deaths",
                    "Too many early/entry deaths in match",
                    "survival",
                    "high",
                    "high",
                    {"entry_deaths": match.entry_deaths, "early_deaths": match.early_deaths},
                    "На следующей игре на этой карте первые 30 секунд играть только от пары или utility.",
                    match_id=match.id,
                )
            )
        if match.adr is not None and match.adr < 60:
            mistakes.append(
                _mistake(
                    "match_low_adr",
                    "Low ADR in match",
                    "aim",
                    "medium",
                    "high",
                    {"adr": match.adr, "threshold": 60},
                    "Разобрать раунды без урона: где контакт был поздним, где была пассивность, где умер без damage.",
                    match_id=match.id,
                )
            )
        if match.kast is not None and match.kast < 62:
            mistakes.append(
                _mistake(
                    "match_low_kast",
                    "Low KAST in match",
                    "survival",
                    "medium",
                    "medium",
                    {"kast": match.kast, "threshold": 62},
                    "Приоритизировать трейд и выживание после первого контакта.",
                    match_id=match.id,
                )
            )
        if match.utility_damage is not None and match.utility_damage < 20 and (match.flash_assists or 0) == 0:
            mistakes.append(
                _mistake(
                    "match_no_utility_value",
                    "No visible utility value",
                    "grenades",
                    "medium",
                    "medium",
                    {"utility_damage": match.utility_damage, "flash_assists": match.flash_assists},
                    "Добавить минимум одну damage grenade и одну support flash в opening plan.",
                    match_id=match.id,
                )
            )
    return mistakes


def _mistake(
    mistake_type: str,
    title: str,
    category: str,
    severity: str,
    confidence: str,
    evidence: dict[str, Any],
    recommendation: str,
    match_id: int | None = None,
) -> dict[str, Any]:
    return {
        "type": mistake_type,
        "title": title,
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "match_id": match_id,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def _prioritize(mistakes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    confidence_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        mistakes,
        key=lambda item: (
            severity_rank.get(item["severity"], 9),
            confidence_rank.get(item["confidence"], 9),
            item["category"],
            item["type"],
        ),
    )


def _status_from_metric(value: float | int | None, good: float, watch: float, higher_is_better: bool) -> str:
    if value is None:
        return "no_data"
    if higher_is_better:
        return "ok" if value >= good else "watch" if value >= watch else "critical"
    return "ok" if value <= good else "watch" if value <= watch else "critical"


def _aim_note(match: Match) -> str:
    if match.adr is None:
        return "ADR недоступен, aim вывод ограничен."
    if match.adr >= 80:
        return "Урон достаточный, дальше важнее не терять KAST и entry discipline."
    if match.adr >= 70:
        return "Урон рабочий, но нужно добирать impact в проигранных раундах."
    return "Низкое давление по урону: нужно разобрать раунды без damage и первые контакты."


def _survival_note(match: Match) -> str:
    if match.kast is None:
        return "KAST недоступен, survival вывод ограничен."
    if match.kast >= 74:
        return "Хорошее участие в раундах."
    if match.kast >= 68:
        return "Участие среднее: вероятно, часть смертей без трейда или impact."
    return "Низкий KAST: слишком много раундов без kill/assist/survive/trade value."


def _utility_note(match: Match) -> str:
    if match.utility_damage is None and match.flash_assists is None:
        return "Utility данные недоступны."
    if (match.utility_damage or 0) >= 80 or (match.flash_assists or 0) >= 2:
        return "Utility дала заметный вклад."
    if (match.utility_damage or 0) >= 40 or (match.flash_assists or 0) >= 1:
        return "Utility была, но impact можно усилить."
    return "Utility почти не дала видимого value."
