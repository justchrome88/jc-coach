from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import CoachReport, Match
from app.services.analytics import compare_periods, detect_weaknesses, get_map_stats, get_summary
from app.services.coach_rules import build_coach_focus
from app.services.match_queries import playable_match_select
from app.services.metric_confidence import (
    exact_date_matches,
    exact_date_window_metadata,
    metric_confidence_map,
    metric_context,
)
from app.services.recommendation_tracking import get_active_recommendation_progress


def generate_report(db: Session) -> CoachReport:
    matches = list(db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())))
    context = metric_context(matches)
    summary = get_summary(matches, context=context)
    comparison = compare_periods(matches, context=context)
    map_stats = get_map_stats(matches, context=context)
    weaknesses = detect_weaknesses(summary, comparison, map_stats)
    focus = build_coach_focus(summary, comparison, map_stats)
    recommendation_progress = get_active_recommendation_progress(db)
    metric_confidence = metric_confidence_map(
        (
            "result",
            "kd_ratio",
            "adr",
            "kast",
            "hltv_rating",
            "swing_score",
            "entry_deaths",
            "utility_damage",
            "flash_assists",
        ),
        matches,
        usage="diagnosis",
        date_windowed=True,
        min_sample=15,
        context=context,
    )
    report_payload = {
        "player_profile": {"skill_level": "low-mid", "goal": "improve consistently in CS2"},
        "summary": summary,
        "period_comparison": comparison,
        "map_stats": map_stats,
        "detected_weaknesses": weaknesses,
        "coach_focus": focus,
        "active_recommendation": _serialize_recommendation_progress(recommendation_progress),
        "available_metrics": summary.get("available_metrics", []),
        "date_window": exact_date_window_metadata(matches, required_sample=15, context=context),
        "metric_confidence": metric_confidence,
    }
    markdown = render_markdown_report(report_payload)
    exact_matches = exact_date_matches(matches, context=context)
    period_start = next((match.played_at for match in exact_matches if match.played_at), None)
    period_end = next((match.played_at for match in reversed(exact_matches) if match.played_at), None)
    report = CoachReport(
        period_start=period_start,
        period_end=period_end,
        matches_count=len(matches),
        report_markdown=markdown,
        report_json=json.dumps(report_payload, ensure_ascii=False, default=str),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    _write_report_file(report.id, markdown)
    return report


def latest_report(db: Session) -> CoachReport | None:
    return db.scalar(select(CoachReport).order_by(CoachReport.created_at.desc(), CoachReport.id.desc()).limit(1))


def render_markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    comparison = payload["period_comparison"]
    maps = payload["map_stats"]
    weaknesses = payload["detected_weaknesses"]
    focus = payload["coach_focus"]
    recommendation = payload.get("active_recommendation")
    date_window = payload.get("date_window") or {}
    confidence = payload.get("metric_confidence") or {}
    best_maps = maps[:3]
    weak_maps = sorted(maps, key=lambda item: item["winrate"] if item["winrate"] is not None else 101)[:3]
    summary_line = (
        f"Загружено матчей: {summary['matches_count']}. "
        f"Winrate: {_fmt(summary['winrate'], '%')}. "
        f"Средний K/D: {_fmt(summary['avg_kd'])}, "
        f"ADR: {_fmt(summary['avg_adr'])}, "
        f"KAST: {_fmt(summary['avg_kast'], '%')}, "
        f"rating: {_fmt(summary['avg_rating'])} ({_confidence_level(confidence, 'hltv_rating')})."
    )

    lines = [
        "# CS2 Coach Report",
        "",
        "## Краткий вывод",
        summary_line,
        (
            "Date-window confidence: "
            f"{date_window.get('confidence', 'unknown')}; exact-date matches "
            f"{date_window.get('exact_date_matches', 0)}, excluded non-exact "
            f"{date_window.get('excluded_from_exact_windows', 0)}."
        ),
        "Metric confidence caveat: KAST, swing, flash/utility and map stats are not standalone hard evidence.",
        f"Главный фокус: **{focus['title']}**. {focus['evidence']}",
        "",
        "## 3 главные проблемы",
    ]
    if weaknesses:
        for index, weakness in enumerate(weaknesses[:3], start=1):
            lines.append(f"{index}. **{weakness['title']}** ({weakness['category']}): {weakness['evidence']}")
    else:
        lines.append("1. Критичных проблем по текущим данным не видно. Нужны новые матчи и более полные поля.")

    lines.extend(["", "## Сильные стороны"])
    strengths = _strengths(summary, maps)
    lines.extend(f"- {item}" for item in strengths)

    lines.extend(["", "## Карты"])
    if maps:
        lines.append("Лучшие карты:")
        lines.extend(
            (
                f"- {item['map_name']}: {item['matches_count']} матч. ({item.get('sample_confidence', 'unknown')}), "
                f"winrate {_fmt(item['winrate'], '%')}, ADR {_fmt(item['avg_adr'])}"
            )
            for item in best_maps
        )
        lines.append("Карты для внимания:")
        lines.extend(
            (
                f"- {item['map_name']}: {item['matches_count']} матч. ({item.get('sample_confidence', 'unknown')}), "
                f"winrate {_fmt(item['winrate'], '%')}, entry diff {item['entry_diff']}"
            )
            for item in weak_maps
        )
    else:
        lines.append("Недостаточно матчей для статистики по картам.")

    lines.extend(["", "## Сравнение периодов"])
    if comparison["previous_n"]:
        for metric, data in comparison["deltas"].items():
            lines.append(
                f"- {metric}: сейчас {_fmt(data['current'])}, "
                f"раньше {_fmt(data['previous'])}, "
                f"изменение {_fmt(data['delta'])}{data['unit']}"
            )
    else:
        lines.append("Для сравнения нужно больше 15 матчей. Сейчас доступен только текущий период.")

    lines.extend(["", "## Фокус на 7 дней"])
    lines.extend(f"- {action}" for action in focus.get("actions", []))

    if recommendation:
        lines.extend(
            [
                "",
                "## Активная рекомендация",
                f"Цель: **{recommendation['title']}**.",
                (
                    f"Прогресс: {recommendation['completed_matches']}/{recommendation['target_matches']} матчей, "
                    f"score {recommendation['progress_score']}/100."
                ),
                (
                    f"Green/yellow/red: {recommendation['counts']['green']}/"
                    f"{recommendation['counts']['yellow']}/{recommendation['counts']['red']}."
                ),
                recommendation["summary"],
            ]
        )

    lines.extend(
        [
            "",
            "## План тренировок",
            "### День 1",
            "- Разобрать последние 3 поражения и отметить первые смерти, utility перед контактом "
            "и проигранные ключевые раунды.",
            "### День 2",
            "- Отработать гранаты и первые 30 секунд раунда на главной слабой карте.",
            "### День 3",
            "- Играть короткую сессию с одной целью: не отдавать изолированные entry deaths.",
            "### День 4",
            "- Повторить демо-ревью и сравнить решения в выигранных и проигранных раундах.",
            "### День 5",
            "- Сыграть 2-3 матча с узким map pool и записать ощущения после каждой карты.",
            "### День 6",
            "- Проверить динамику ADR/KAST/entry diff, скорректировать фокус.",
            "### День 7",
            "- Сгенерировать новый отчёт и сравнить период с текущей базой.",
            "",
            "## Метрики контроля",
            "- Winrate последних 15 матчей.",
            "- K/D и ADR exact-date окна.",
            "- KAST, swing, utility и flash assists только с caveat.",
            "- Entry diff и entry deaths per match с sample-size context.",
            "- Winrate и ADR на картах только при достаточном числе матчей.",
        ]
    )
    return "\n".join(lines)


def markdown_to_html(markdown: str) -> str:
    html_lines = []
    for line in markdown.splitlines():
        text = escape(line)
        if text.startswith("# "):
            html_lines.append(f"<h1>{text[2:]}</h1>")
        elif text.startswith("## "):
            html_lines.append(f"<h2>{text[3:]}</h2>")
        elif text.startswith("### "):
            html_lines.append(f"<h3>{text[4:]}</h3>")
        elif text.startswith("- "):
            html_lines.append(f"<li>{text[2:]}</li>")
        elif text and text[0].isdigit() and ". " in text[:4]:
            html_lines.append(f"<p>{text}</p>")
        elif text:
            html_lines.append(f"<p>{text}</p>")
    return "\n".join(html_lines).replace("**", "")


def _strengths(summary: dict[str, Any], maps: list[dict[str, Any]]) -> list[str]:
    strengths = []
    if summary.get("avg_kd") is not None and summary["avg_kd"] >= 1.1:
        strengths.append(f"K/D выше базового уровня: {_fmt(summary['avg_kd'])}.")
    if summary.get("avg_adr") is not None and summary["avg_adr"] >= 80:
        strengths.append(f"Хороший средний урон: {_fmt(summary['avg_adr'])} ADR.")
    if summary.get("avg_kast") is not None and summary["avg_kast"] >= 74:
        strengths.append(f"Стабильное участие в раундах: {_fmt(summary['avg_kast'], '%')} KAST.")
    if maps:
        strengths.append(f"Лучшая карта сейчас: {maps[0]['map_name']} с winrate {_fmt(maps[0]['winrate'], '%')}.")
    return strengths or [
        "Есть базовая статистика для старта. Следующий шаг - накопить больше матчей и отслеживать динамику."
    ]


def _serialize_recommendation_progress(progress: dict[str, Any] | None) -> dict[str, Any] | None:
    if not progress:
        return None
    recommendation = progress["recommendation"]
    return {
        "id": recommendation.id,
        "title": recommendation.title,
        "status": recommendation.status,
        "health": progress.get("health") or {},
        "baseline": progress["baseline"],
        "target": progress["target"],
        "counts": progress["counts"],
        "progress_score": progress["progress_score"],
        "completed_matches": progress["completed_matches"],
        "target_matches": progress["target_matches"],
        "summary": progress["summary"],
    }


def _fmt(value: Any, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value}{suffix}"


def _confidence_level(confidence: dict[str, Any], metric_id: str) -> str:
    item = confidence.get(metric_id) or {}
    return str(item.get("level") or "unknown")


def _write_report_file(report_id: int, markdown: str) -> None:
    settings = get_settings()
    path = Path(settings.reports_dir) / f"coach_report_{report_id}.md"
    path.write_text(markdown, encoding="utf-8")
