from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import CoachReport, Match
from app.services.analytics import compare_periods, detect_weaknesses, get_dashboard_status, get_map_stats, get_summary
from app.services.coach_rules import build_coach_focus
from app.services.mistake_detection import category_scorecard, detect_structured_mistakes
from app.services.recommendation_tracking import get_active_recommendation_progress, get_all_recommendation_progress
from app.services.report_generator import _serialize_recommendation_progress


class AIProvider(Protocol):
    name: str

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Prepare an AI coach task without requiring a specific model backend."""

    def generate(self, payload: dict[str, Any]) -> str:
        """Generate an AI coach report when the provider supports direct execution."""


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

    def generate(self, payload: dict[str, Any]) -> str:
        self.prepare(payload)
        raise RuntimeError("codex_cli_handoff prepares a prompt bundle; paste the Codex result back into the UI.")


@dataclass(frozen=True)
class LocalLLMProvider:
    name: str = "local_llm"

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        configured = bool(settings.local_llm_base_url and settings.local_llm_model)
        return {
            "provider": self.name,
            "status": "configured" if configured else "not_configured",
            "base_url": settings.local_llm_base_url,
            "model": settings.local_llm_model,
            "payload_preview": {
                "matches": payload["summary"]["matches_count"],
                "weaknesses": len(payload["detected_weaknesses"]),
            },
            "note": "Configure LOCAL_LLM_BASE_URL and LOCAL_LLM_MODEL to generate directly.",
        }

    def generate(self, payload: dict[str, Any]) -> str:
        settings = get_settings()
        if not settings.local_llm_base_url or not settings.local_llm_model:
            raise RuntimeError("Local LLM is not configured.")
        prompt = build_ai_coach_prompt(payload)
        base_url = settings.local_llm_base_url.rstrip("/")
        if base_url.endswith(":11434") or "ollama" in base_url:
            return _call_ollama(base_url, settings.local_llm_model, prompt, settings.local_llm_timeout_seconds)
        return _call_openai_compatible(
            base_url,
            settings.local_llm_model,
            prompt,
            settings.local_llm_timeout_seconds,
        )


def prepare_ai_coach_handoff(db: Session) -> dict[str, Any]:
    payload = build_ai_coach_payload(db)
    provider = _provider()
    result = provider.prepare(payload)
    result["matches_count"] = payload["summary"]["matches_count"]
    result["weaknesses_count"] = len(payload["detected_weaknesses"])
    return result


def generate_ai_coach_with_provider(db: Session) -> CoachReport:
    payload = build_ai_coach_payload(db)
    provider = _provider()
    content = provider.generate(payload)
    return save_ai_coach_result(db, content, source_ref=provider.name)


def ai_provider_health() -> dict[str, Any]:
    settings = get_settings()
    provider = _provider()
    if isinstance(provider, CodexCliHandoffProvider):
        return {"provider": provider.name, "status": "handoff", "message": "Codex CLI handoff is available."}
    if not settings.local_llm_base_url or not settings.local_llm_model:
        return {"provider": provider.name, "status": "not_configured"}
    return {
        "provider": provider.name,
        "status": "configured",
        "base_url": settings.local_llm_base_url,
        "model": settings.local_llm_model,
    }


def save_ai_coach_result(db: Session, markdown: str, source_ref: str | None = None) -> CoachReport:
    content = markdown.strip()
    if not content:
        raise ValueError("AI coach result is empty.")
    if len(content) > 60_000:
        raise ValueError("AI coach result is too long.")
    matches = list(db.scalars(select(Match).order_by(Match.played_at.asc().nulls_last(), Match.id.asc())))
    period_start = next((match.played_at for match in matches if match.played_at), None)
    period_end = next((match.played_at for match in reversed(matches) if match.played_at), None)
    latest_handoff = latest_ai_handoff()
    report = CoachReport(
        period_start=period_start,
        period_end=period_end,
        matches_count=len(matches),
        report_type="ai_coach",
        source_ref=source_ref or (latest_handoff or {}).get("prompt_path"),
        report_markdown=content,
        report_json=json.dumps(
            {
                "type": "ai_coach",
                "provider": (latest_handoff or {}).get("provider", "codex_cli_handoff"),
                "handoff": latest_handoff,
            },
            ensure_ascii=False,
            default=str,
        ),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def latest_ai_coach_report(db: Session) -> CoachReport | None:
    return db.scalar(
        select(CoachReport)
        .where(CoachReport.report_type == "ai_coach")
        .order_by(CoachReport.created_at.desc(), CoachReport.id.desc())
        .limit(1)
    )


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
    all_recommendation_progress = get_all_recommendation_progress(db)
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
        "all_recommendations": [_serialize_recommendation_progress(item) for item in all_recommendation_progress],
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
        return LocalLLMProvider()
    return CodexCliHandoffProvider()


def _call_ollama(base_url: str, model: str, prompt: str, timeout: int) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    response = _post_json(f"{base_url}/api/generate", payload, timeout)
    content = response.get("response")
    if not content:
        raise RuntimeError("Local LLM returned an empty Ollama response.")
    return str(content).strip()


def _call_openai_compatible(base_url: str, model: str, prompt: str, timeout: int) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a CS2 AI coach. Return a Russian coach report."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    response = _post_json(f"{base_url}/v1/chat/completions", payload, timeout)
    choices = response.get("choices") or []
    if not choices:
        raise RuntimeError("Local LLM returned no choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise RuntimeError("Local LLM returned an empty chat response.")
    return str(content).strip()


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Local LLM request failed: {exc}") from exc


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
