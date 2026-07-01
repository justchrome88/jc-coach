from __future__ import annotations

from typing import Any

from app.services.analytics import detect_weaknesses


def build_coach_focus(
    summary: dict[str, Any],
    comparison: dict[str, Any],
    map_stats: list[dict[str, Any]],
) -> dict[str, Any]:
    weaknesses = detect_weaknesses(summary, comparison, map_stats)
    if not weaknesses:
        return {
            "title": "Поддерживать стабильность",
            "category": "discipline",
            "severity": "low",
            "evidence": "По загруженным данным не видно критичной просадки.",
            "actions": [
                "Продолжай загружать матчи после каждой сессии.",
                "Разбери одно поражение и одну победу, сравни решения в ключевых раундах.",
                "По возможности добавь больше полей в CSV/JSON.",
            ],
        }
    primary = weaknesses[0].copy()
    primary["actions"] = actions_for_category(primary["category"])
    return primary


def actions_for_category(category: str) -> list[str]:
    actions = {
        "utility": [
            "Выбери две слабые карты и выучи по 3 повторяемых grenade pack для каждой.",
            "Используй гранаты до первого контакта, а не сохраняй их для уже проигранных ретейков.",
            "Следующие 10 матчей отслеживай utility damage и flash assists.",
        ],
        "entry_duels": [
            "Не бери первый контакт без тиммейта, готового к размену.",
            "До занятия пространства проговаривай маршрут на первые 30 секунд.",
            "Каждую entry death помечай причиной: изоляция, поздний трейд или плохой тайминг.",
        ],
        "survival": [
            "Ставь tradeable-позицию выше изолированной дуэли.",
            "После первого урона меняй позицию, не повторяй тот же угол.",
            "Контрольные метрики: KAST и deaths per match.",
        ],
        "map_specific": [
            "Собери одностраничный playbook по слабой карте.",
            "Подготовь два T-default и две CT-расстановки перед следующей игрой.",
            "Временно сузь map pool, если карта продолжает ломать прогресс.",
        ],
        "aim_duels": [
            "Перед матчами делай 15 минут counter-strafe и burst discipline.",
            "Не форси low-percentage re-peek после полученного урона.",
            "Отслеживай ADR, opening deaths и rating вместе.",
        ],
        "decision_making": [
            "Разбери три проигранных swing round и запиши более надёжное решение.",
            "Замедляй mid-round решения после первого фрага твоей команды.",
            "Фокусируйся на bomb/space value, а не на low-impact exit kills.",
        ],
        "discipline": [
            "Сыграй блок стабилизации: меньше карт, меньше solo plays, понятнее utility.",
            "После двух low-focus поражений останавливайся и разбирай матчи вместо новой очереди.",
            "Сравни следующие 10 матчей с предыдущими 10.",
        ],
    }
    return actions.get(category, actions["discipline"])
