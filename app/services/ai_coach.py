from __future__ import annotations

import hashlib
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
from app.services.ai_validator import render_ai_output_markdown, validate_ai_coach_output
from app.services.aim_stats import get_aim_profile
from app.services.analytics import compare_periods, detect_weaknesses, get_dashboard_status, get_map_stats, get_summary
from app.services.coach_rules import build_coach_focus
from app.services.demo_retention import ARTIFACT_CATEGORY_COACH_OUTPUT, artifact_retention_metadata
from app.services.match_queries import playable_match_select
from app.services.metric_confidence import (
    exact_date_window_metadata,
    exact_recent_matches,
    metric_confidence_map,
    metric_context,
)
from app.services.metric_truth import (
    METRIC_REGISTRY_VERSION,
    metric_truth_payload,
    suppressed_metrics_for_usage,
)
from app.services.mistake_detection import category_scorecard, detect_structured_mistakes
from app.services.ownership import get_owned_metric_snapshot
from app.services.recommendation_tracking import get_active_recommendation_progress, get_all_recommendation_progress
from app.services.report_generator import _serialize_recommendation_progress

AI_COACH_PROMPT_VERSION = "ai-coach-prompt-v1"
AI_COACH_PAYLOAD_SCHEMA_VERSION = "ai-coach-payload-v1"
AI_COACH_SNAPSHOT_CONTRACT_VERSION = "ai-coach-snapshot-v1"
AI_COACH_SNAPSHOT_GENERATED_BY = "app.services.ai_coach"
AI_COACH_DOMAIN_CONTRACT_VERSION = "cs2-domain-contract-v1"


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
            **_ai_coach_contract_snapshot(payload),
            **_ai_coach_domain_contract(payload),
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


def save_ai_coach_result(
    db: Session,
    markdown: str,
    source_ref: str | None = None,
    payload_snapshot: dict[str, Any] | None = None,
    user_id: int | None = None,
    source_metric_snapshot_id: int | None = None,
) -> CoachReport:
    raw_content = markdown.strip()
    if not raw_content:
        raise ValueError("AI coach result is empty.")
    if len(raw_content) > 60_000:
        raise ValueError("AI coach result is too long.")
    if user_id is not None and source_metric_snapshot_id is not None:
        if get_owned_metric_snapshot(db, user_id=user_id, snapshot_id=source_metric_snapshot_id) is None:
            raise PermissionError("Metric snapshot belongs to a different user.")
    snapshot = payload_snapshot or build_ai_coach_payload(db)
    validation = validate_ai_coach_output(raw_content, payload_snapshot=snapshot)
    content = (
        render_ai_output_markdown(validation.output)
        if validation.valid and validation.output is not None
        else validation.fallback_markdown
    )
    if content is None:
        raise ValueError("AI coach validation did not produce content.")
    matches = list(db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())))
    period_start = next((match.played_at for match in matches if match.played_at), None)
    period_end = next((match.played_at for match in reversed(matches) if match.played_at), None)
    latest_handoff = latest_ai_handoff()
    metadata = _ai_report_metadata(content, snapshot, latest_handoff, source_ref)
    metadata["ai_validation"] = validation.to_dict()
    if validation.valid and validation.output is not None:
        metadata["ai_structured_output"] = validation.output
    report = CoachReport(
        user_id=user_id,
        source_metric_snapshot_id=source_metric_snapshot_id,
        period_start=period_start,
        period_end=period_end,
        matches_count=len(matches),
        report_type="ai_coach",
        source_ref=source_ref or (latest_handoff or {}).get("prompt_path"),
        report_markdown=content,
        report_json=json.dumps(metadata, ensure_ascii=False, default=str),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def latest_ai_coach_report(db: Session, *, user_id: int | None = None) -> CoachReport | None:
    stmt = select(CoachReport).where(CoachReport.report_type == "ai_coach")
    if user_id is not None:
        stmt = stmt.where(CoachReport.user_id == user_id)
    return db.scalar(stmt.order_by(CoachReport.created_at.desc(), CoachReport.id.desc()).limit(1))


def list_ai_coach_reports(db: Session, limit: int = 10, *, user_id: int | None = None) -> list[CoachReport]:
    stmt = select(CoachReport).where(CoachReport.report_type == "ai_coach")
    if user_id is not None:
        stmt = stmt.where(CoachReport.user_id == user_id)
    return list(
        db.scalars(
            stmt.order_by(CoachReport.created_at.desc(), CoachReport.id.desc()).limit(limit)
        ).all()
    )


def serialize_ai_coach_report(report: CoachReport) -> dict[str, Any]:
    metadata = _json_loads(report.report_json)
    return {
        "id": report.id,
        "user_id": report.user_id,
        "source_metric_snapshot_id": report.source_metric_snapshot_id,
        "matches_count": report.matches_count,
        "period_start": report.period_start.isoformat() if report.period_start else None,
        "period_end": report.period_end.isoformat() if report.period_end else None,
        "source_ref": report.source_ref,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "provider": metadata.get("provider"),
        "status": metadata.get("status"),
        "payload_hash": metadata.get("payload_hash"),
        "payload_matches_count": (metadata.get("payload_summary") or {}).get("matches_count"),
        "content_chars": metadata.get("content_chars"),
        "report_markdown": report.report_markdown,
        "metadata": metadata,
    }


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
    matches = list(db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())))
    context = metric_context(matches)
    summary = get_summary(matches, context=context)
    comparison = compare_periods(matches, context=context)
    map_stats = get_map_stats(matches, context=context)
    weaknesses = detect_weaknesses(summary, comparison, map_stats)
    structured_mistakes = detect_structured_mistakes(matches)
    focus = build_coach_focus(summary, comparison, map_stats)
    recommendation_progress = get_active_recommendation_progress(db)
    all_recommendation_progress = get_all_recommendation_progress(db)
    recent_matches = exact_recent_matches(matches, 10, context=context)
    confidence_metadata = {
        "date_window": exact_date_window_metadata(matches, required_sample=15, context=context),
        "metrics": metric_confidence_map(
            (
                "result",
                "kd_ratio",
                "adr",
                "kast",
                "hltv_rating",
                "swing_score",
                "entry_deaths",
                "early_deaths",
                "utility_damage",
                "flash_assists",
                "side_split_metrics",
                "aim_rating",
                "grenade_rating",
                "traded_deaths",
                "crosshair_placement",
            ),
            matches,
            usage="ai",
            date_windowed=True,
            min_sample=15,
            context=context,
        ),
    }
    domain_contract = _ai_coach_domain_contract()
    return {
        "product": "CS2 Personal Coach",
        "ai_role": "AI coach over structured CS2 analytics, not raw demo parser",
        "contract_snapshot": _ai_coach_contract_snapshot(),
        **domain_contract,
        "summary": summary,
        "dashboard_status": get_dashboard_status(matches, context=context),
        "aim_profile": get_aim_profile(matches, context=context),
        "period_comparison": comparison,
        "map_stats": map_stats,
        "detected_weaknesses": weaknesses,
        "structured_mistakes": structured_mistakes,
        "coach_categories": category_scorecard(structured_mistakes),
        "coach_focus": focus,
        "metric_truth": {
            "metric_registry_version": METRIC_REGISTRY_VERSION,
            "definitions": metric_truth_payload(
                (
                    "adr",
                    "kast",
                    "kd_ratio",
                    "entry_deaths",
                    "early_deaths",
                    "trade_kills",
                    "traded_deaths",
                    "utility_damage",
                    "flash_assists",
                    "side_split_metrics",
                    "aim_rating",
                    "grenade_rating",
                )
            ),
            "suppressed_for_diagnosis": suppressed_metrics_for_usage("diagnosis"),
            "suppressed_for_recommendation": suppressed_metrics_for_usage("recommendation"),
            "confidence": confidence_metadata,
        },
        "metric_confidence": confidence_metadata,
        "active_recommendation": _serialize_recommendation_progress(recommendation_progress),
        "all_recommendations": [_serialize_recommendation_progress(item) for item in all_recommendation_progress],
        "recent_matches": [_serialize_match(match) for match in recent_matches],
        "rules": {
            "do_not_invent_facts": True,
            "use_only_payload_data": True,
            "mention_data_gaps": True,
            "use_exact_date_windows_for_trends": True,
            "do_not_treat_low_confidence_as_hard_evidence": True,
            "obey_domain_constraints": True,
            "do_not_claim_v1_0": True,
            "do_not_claim_public_or_friends_readiness": True,
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
            "- Используй metric_truth: suppressed metrics нельзя превращать в уверенный диагноз или рекомендацию.",
            "- Верни строго JSON по схеме: summary, diagnoses[], recommendations[], warnings[], "
            "evidence[], confidence.",
            "- В diagnoses указывай category, severity, claim, evidence_metric_ids[], confidence, caveats[].",
            "- В recommendations указывай category, action, rationale, target_metric_ids[], confidence, caveats[].",
            "- В evidence указывай metric_id, metric_confidence, caveats[] и, если есть в payload, "
            "problem/problem_id, match_ids/sample_count/window и recommendation_id.",
            "- Для approximate/warn metrics обязательно добавляй caveats; suppressed/unavailable metrics "
            "не используй как evidence.",
            "- Соблюдай domain_constraints, claim_guardrails, metric_confidence_policy, playlist_mode_policy, "
            "recommendation_policy и public_readiness_policy из payload.",
            "- Weak/low/unavailable metrics и missing metric_confidence не превращай в hard diagnosis, "
            "progress, failure или priority claim.",
            "- Playlist/mode остается unknown/provenance-only: не утверждай Premier, Competitive, Wingman, "
            "Casual, Deathmatch, FACEIT или custom, если reliable persisted metadata нет в payload.",
            "- Public/friends readiness заблокирован, v1.0 не заявлен, Steam import cap остается 1.",
            "- Не выдумывай parser data, exact match dates, confidence, economy model, positioning model, "
            "clutch model, trade model или map-specific certainty.",
            "- Не делай общий motivational текст. Дай конкретный фокус, причины и действия.",
            "- Главный результат: что игрок должен изменить в следующих 5-10 матчах.",
            "- Разбирай aim, map, grenades, entry duels и survival только в пределах поддержанных metrics.",
            "- Economy, positioning, clutch, hard trade и crosshair placement описывай только как data gap, "
            "если payload явно не содержит accepted evidence.",
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


def _ai_report_metadata(
    content: str,
    payload_snapshot: dict[str, Any],
    latest_handoff: dict[str, Any] | None,
    source_ref: str | None,
) -> dict[str, Any]:
    payload_json = json.dumps(payload_snapshot, ensure_ascii=False, sort_keys=True, default=str)
    provider = (latest_handoff or {}).get("provider") or _provider().name
    contract_snapshot = _ai_coach_contract_snapshot(payload_snapshot)
    domain_contract = _ai_coach_domain_contract(payload_snapshot)
    return {
        "type": "ai_coach",
        "status": "saved",
        "artifact_retention": artifact_retention_metadata(ARTIFACT_CATEGORY_COACH_OUTPUT),
        "provider": provider,
        "source_ref": source_ref,
        "handoff": latest_handoff,
        **contract_snapshot,
        **domain_contract,
        "contract_snapshot": contract_snapshot,
        "domain_contract": domain_contract,
        "payload_hash": hashlib.sha256(payload_json.encode("utf-8")).hexdigest()[:16],
        "payload_summary": {
            "matches_count": (payload_snapshot.get("summary") or {}).get("matches_count"),
            "structured_mistakes_count": len(payload_snapshot.get("structured_mistakes") or []),
            "recommendations_count": len(payload_snapshot.get("all_recommendations") or []),
            "recent_matches_count": len(payload_snapshot.get("recent_matches") or []),
        },
        "payload_snapshot": payload_snapshot,
        "content_chars": len(content),
        "saved_at": datetime.now(UTC).isoformat(),
    }


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _ai_coach_contract_snapshot(payload: dict[str, Any] | None = None) -> dict[str, str]:
    snapshot = payload.get("contract_snapshot") if isinstance(payload, dict) else None
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "ai_coach_prompt_version": str(snapshot.get("ai_coach_prompt_version") or AI_COACH_PROMPT_VERSION),
        "ai_coach_payload_schema_version": str(
            snapshot.get("ai_coach_payload_schema_version") or AI_COACH_PAYLOAD_SCHEMA_VERSION
        ),
        "metric_registry_version": str(snapshot.get("metric_registry_version") or METRIC_REGISTRY_VERSION),
        "snapshot_generated_by": str(snapshot.get("snapshot_generated_by") or AI_COACH_SNAPSHOT_GENERATED_BY),
        "snapshot_contract_version": str(
            snapshot.get("snapshot_contract_version") or AI_COACH_SNAPSHOT_CONTRACT_VERSION
        ),
    }


def _ai_coach_domain_contract(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = payload.get("domain_contract") if isinstance(payload, dict) else None
    if not isinstance(contract, dict):
        contract = payload if isinstance(payload, dict) else {}
    if contract.get("domain_contract_version") == AI_COACH_DOMAIN_CONTRACT_VERSION:
        return {
            "domain_contract_version": AI_COACH_DOMAIN_CONTRACT_VERSION,
            "domain_constraints": contract.get("domain_constraints") or {},
            "claim_guardrails": contract.get("claim_guardrails") or {},
            "metric_confidence_policy": contract.get("metric_confidence_policy") or {},
            "playlist_mode_policy": contract.get("playlist_mode_policy") or {},
            "recommendation_policy": contract.get("recommendation_policy") or {},
            "public_readiness_policy": contract.get("public_readiness_policy") or {},
        }
    return {
        "domain_contract_version": AI_COACH_DOMAIN_CONTRACT_VERSION,
        "domain_constraints": {
            "current_product_version": "v0.9",
            "v1_0_claim_allowed": False,
            "steam_import_max_demos_per_run": 1,
            "playlist_mode_status": "unknown_or_provenance_only",
            "public_friends_readiness": "blocked",
            "ready_for_major_cs2_feature_work": False,
            "accepted_active_hard_recommendation_id": 5,
            "legacy_recommendation_ids_blocked_for_new_hard_evaluations": [1, 3, 4],
            "unavailable_models": [
                "economy_model",
                "positioning_model",
                "clutch_model",
                "canonical_map_registry",
                "hard_trade_model",
                "crosshair_placement_model",
            ],
            "display_only_or_weak_domains": [
                "side_split_metrics",
                "trade_kills",
                "current_map_labels",
            ],
        },
        "claim_guardrails": {
            "use_only_payload_data": True,
            "do_not_invent_parser_data": True,
            "do_not_invent_exact_playlist_labels": True,
            "do_not_invent_match_dates": True,
            "do_not_invent_confidence": True,
            "do_not_invent_models": [
                "economy",
                "positioning",
                "clutch",
                "trade",
            ],
            "unsupported_claim_boundaries": [
                "exact_playlist_or_mode",
                "economy_decisions",
                "positioning_rotations_spacing_or_angles",
                "clutch_winrate_or_clutch_mistakes",
                "hard_trade_recommendations",
                "crosshair_placement_diagnosis",
                "canonical_map_or_map_specific_certainty",
            ],
            "unavailable_concepts_must_be_worded_as_data_gaps": True,
        },
        "metric_confidence_policy": {
            "metric_confidence_required_for_hard_claims": True,
            "missing_metric_confidence_blocks_hard_advice": True,
            "weak_metrics_must_remain_caveated": True,
            "low_or_unavailable_metrics_are_context_only": True,
            "warn_metrics_require_visible_caveats": True,
            "suppressed_metrics_cannot_support_diagnosis_or_recommendation": True,
            "confidence_cannot_exceed_weakest_evidence_link": True,
            "weak_or_suppressed_metric_examples": [
                "early_deaths",
                "kast",
                "hltv_rating",
                "swing_score",
                "flash_assists",
                "trade_kills",
                "traded_deaths",
                "side_split_metrics",
                "crosshair_placement",
            ],
        },
        "playlist_mode_policy": {
            "mode_status": "unknown_or_provenance_only",
            "accepted_current_labels": [
                "mode_unknown",
                "provenance_demo",
                "provenance_valve_matchmaking",
            ],
            "accepted_exact_date_source": "steam_gc_match_time",
            "unsupported_exact_playlist_claims": [
                "Premier",
                "Competitive",
                "Wingman",
                "Casual",
                "Deathmatch",
                "FACEIT",
                "custom",
            ],
            "source_labels_are_provenance_not_playlist": True,
        },
        "recommendation_policy": {
            "current_accepted_active_hard_recommendation_id": 5,
            "current_accepted_active_hard_recommendation_status": "accepted_active",
            "legacy_recommendations_not_for_new_hard_evaluations": [1, 3, 4],
            "one_primary_active_focus_contract": True,
            "hard_recommendation_evidence_chain": "problem -> metric -> match -> recommendation",
            "do_not_change_recommendation_selection": True,
        },
        "public_readiness_policy": {
            "current_product_version": "v0.9",
            "v1_0_claim_allowed": False,
            "public_readiness": "blocked",
            "friends_readiness": "blocked",
            "public_or_friends_claim_allowed": False,
        },
    }


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
        "swing_score": match.swing_score,
        "entry_kills": match.entry_kills,
        "entry_deaths": match.entry_deaths,
        "early_deaths": match.early_deaths,
        "utility_damage": match.utility_damage,
        "flash_assists": match.flash_assists,
        "date_truth": {
            "requires_exact_for_trends": True,
        },
    }
