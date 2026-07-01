from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Match
from app.services.analytics import compare_periods, detect_weaknesses, get_dashboard_status, get_map_stats, get_summary
from app.services.coach_rules import build_coach_focus
from app.services.mistake_detection import category_scorecard, detect_structured_mistakes
from app.services.recommendation_tracking import get_active_recommendation_progress
from app.services.report_generator import _serialize_recommendation_progress


class AIProvider(Protocol):
    name: str

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Prepare an AI coach task without requiring a specific model backend."""


@dataclass(frozen=True)
class CodexCliHandoffProvider:
    name: str = "codex_cli_handoff"

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        target_dir = Path(settings.ai_handoff_dir) / timestamp
        target_dir.mkdir(parents=True, exist_ok=True)
        payload_path = target_dir / "coach_payload.json"
        prompt_path = target_dir / "codex_prompt.md"
        result_path = target_dir / "ai_coach_result.md"
        prompt = build_ai_coach_prompt(payload)
        payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        prompt_path.write_text(prompt, encoding="utf-8")
        command = f"{settings.ai_codex_command} --cd /opt/jc-coach \"$(cat {prompt_path})\""
        metadata = {
            "provider": self.name,
            "status": "handoff_ready",
            "created_at": datetime.now(UTC).isoformat(),
            "prompt_path": str(prompt_path),
            "payload_path": str(payload_path),
            "result_path": str(result_path),
            "command": command,
            "note": "Run this command in the server shell or let Codex process the prompt manually.",
        }
        (target_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata


@dataclass(frozen=True)
class LocalLLMPlannedProvider:
    name: str = "local_llm_planned"

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        return {
            "provider": self.name,
            "status": "not_configured",
            "base_url": settings.local_llm_base_url,
            "model": settings.local_llm_model,
            "payload_preview": {
                "matches": payload["summary"]["matches_count"],
                "weaknesses": len(payload["detected_weaknesses"]),
            },
            "note": "Local LLM provider is planned. Configure LOCAL_LLM_BASE_URL and LOCAL_LLM_MODEL later.",
        }


def prepare_ai_coach_handoff(db: Session) -> dict[str, Any]:
    payload = build_ai_coach_payload(db)
    provider = _provider()
    result = provider.prepare(payload)
    result["matches_count"] = payload["summary"]["matches_count"]
    result["weaknesses_count"] = len(payload["detected_weaknesses"])
    return result


def latest_ai_handoff() -> dict[str, Any] | None:
    handoff_root = Path(get_settings().ai_handoff_dir)
    metadata_files = sorted(handoff_root.glob("*/metadata.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not metadata_files:
        return None
    try:
        return json.loads(metadata_files[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def build_ai_coach_payload(db: Session) -> dict[str, Any]:
    matches = list(db.scalars(select(Match).order_by(Match.played_at.asc().nulls_last(), Match.id.asc())))
    summary = get_summary(matches)
    comparison = compare_periods(matches)
    map_stats = get_map_stats(matches)
    weaknesses = detect_weaknesses(summary, comparison, map_stats)
    structured_mistakes = detect_structured_mistakes(matches)
    focus = build_coach_focus(summary, comparison, map_stats)
    recommendation_progress = get_active_recommendation_progress(db)
    recent_matches = matches[-10:]
    return {
        "product": "CS2 Personal Coach",
        "ai_role": "AI coach over structured CS2 analytics, not raw demo parser",
        "summary": summary,
        "dashboard_status": get_dashboard_status(matches),
        "period_comparison": comparison,
        "map_stats": map_stats,
        "detected_weaknesses": weaknesses,
        "structured_mistakes": structured_mistakes,
        "coach_categories": category_scorecard(structured_mistakes),
        "coach_focus": focus,
        "active_recommendation": _serialize_recommendation_progress(recommendation_progress),
        "recent_matches": [_serialize_match(match) for match in recent_matches],
        "rules": {
            "do_not_invent_facts": True,
            "use_only_payload_data": True,
            "mention_data_gaps": True,
            "primary_goal": "give one main training focus and measurable next-match actions",
        },
    }


def build_ai_coach_prompt(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Ты AI-тренер по CS2 внутри продукта CS2 Personal Coach.",
            "",
            "Задача: по структурированным данным ниже написать coach report на русском.",
            "",
            "Жесткие правила:",
            "- Не выдумывай факты, которых нет в JSON.",
            "- Если данных мало или confidence низкий, прямо скажи об этом.",
            "- Не делай общий motivational текст. Дай конкретный фокус, причины и действия.",
            "- Главный результат: что игрок должен изменить в следующих 5-10 матчах.",
            "- Разбирай отдельно aim, map, crosshair placement, grenades, entry duels и survival.",
            "- Если по crosshair placement нет данных, не делай выводы, а отметь data gap.",
            "- Структура ответа: краткий диагноз, 3 главные ошибки, рекомендации по категориям, "
            "план на неделю, метрики контроля.",
            "",
            "JSON payload:",
            "```json",
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            "```",
        ]
    )


def _provider() -> AIProvider:
    provider = get_settings().ai_provider.strip().lower()
    if provider == "local_llm":
        return LocalLLMPlannedProvider()
    return CodexCliHandoffProvider()


def _serialize_match(match: Match) -> dict[str, Any]:
    return {
        "id": match.id,
        "source": match.source,
        "played_at": match.played_at.isoformat() if match.played_at else None,
        "map_name": match.map_name,
        "result": match.result,
        "score": f"{match.rounds_for or 0}:{match.rounds_against or 0}",
        "kills": match.kills,
        "deaths": match.deaths,
        "assists": match.assists,
        "kd": match.kd,
        "adr": match.adr,
        "kast": match.kast,
        "rating": match.rating,
        "entry_kills": match.entry_kills,
        "entry_deaths": match.entry_deaths,
        "early_deaths": match.early_deaths,
        "utility_damage": match.utility_damage,
        "flash_assists": match.flash_assists,
    }
