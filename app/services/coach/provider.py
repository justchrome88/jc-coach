"""Single boundary for configured AI provider adapters and execution."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import CoachReport
from app.services.coach import ai as coach_ai
from app.services.metrics.snapshots import MetricSnapshotAnalysisScope


class AIProvider(Protocol):
    name: str

    def prepare(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def generate(self, payload: dict[str, Any]) -> str: ...


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
        prompt = coach_ai.build_ai_coach_prompt(payload)
        payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        prompt_path.write_text(prompt, encoding="utf-8")
        command = f'{settings.ai_codex_command} --cd /opt/jc-coach "$(cat {prompt_path})"'
        metadata = {
            "provider": self.name,
            "status": "handoff_ready",
            "created_at": datetime.now(UTC).isoformat(),
            **coach_ai._ai_coach_contract_snapshot(payload),
            **coach_ai._ai_coach_domain_contract(payload),
            "prompt_path": str(prompt_path),
            "payload_path": str(payload_path),
            "result_path": str(result_path),
            "command": command,
            "note": "Run this command in the server shell or let Codex process the prompt manually.",
        }
        (target_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
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
        prompt = coach_ai.build_ai_coach_prompt(payload)
        base_url = settings.local_llm_base_url.rstrip("/")
        if base_url.endswith(":11434") or "ollama" in base_url:
            return _call_ollama(base_url, settings.local_llm_model, prompt, settings.local_llm_timeout_seconds)
        return _call_openai_compatible(
            base_url,
            settings.local_llm_model,
            prompt,
            settings.local_llm_timeout_seconds,
        )


def invoke_configured_structured_model(
    *, prompt: str, schema_path: Path, timeout_seconds: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Invoke the configured route and return schema-constrained JSON plus safe telemetry."""
    settings = get_settings()
    provider_name = settings.ai_provider.strip().lower()
    started = time.monotonic()
    if provider_name == "codex_cli_handoff":
        with tempfile.TemporaryDirectory(prefix="jc-coach-domain-ai-") as temporary:
            output_path = Path(temporary) / "result.json"
            command = [
                *settings.ai_codex_command.split(),
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "--json",
                "--cd",
                temporary,
                "--skip-git-repo-check",
                "-",
            ]
            try:
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds or settings.local_llm_timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError("configured_model_timeout") from exc
            if completed.returncode != 0 or not output_path.exists():
                raise RuntimeError("configured_model_invocation_failed")
            raw = output_path.read_text(encoding="utf-8")
            telemetry = _codex_jsonl_telemetry(completed.stdout)
        return json.loads(raw), {
            "provider": "codex_cli_handoff",
            "model": telemetry.get("model") or _codex_configured_model(),
            "route": "codex_exec_output_schema",
            "request_id": telemetry.get("thread_id"),
            "input_tokens": telemetry.get("input_tokens"),
            "output_tokens": telemetry.get("output_tokens"),
            "latency_ms": round((time.monotonic() - started) * 1000),
            "raw_response_hash": hashlib.sha256(raw.encode()).hexdigest(),
        }
    if provider_name == "local_llm":
        if not settings.local_llm_base_url or not settings.local_llm_model:
            raise RuntimeError("configured_model_unavailable")
        base_url = settings.local_llm_base_url.rstrip("/")
        if base_url.endswith(":11434") or "ollama" in base_url:
            raw = _call_ollama(
                base_url, settings.local_llm_model, prompt, timeout_seconds or settings.local_llm_timeout_seconds
            )
        else:
            raw = _call_openai_compatible(
                base_url, settings.local_llm_model, prompt, timeout_seconds or settings.local_llm_timeout_seconds
            )
        return json.loads(raw), {
            "provider": "local_llm",
            "model": settings.local_llm_model,
            "route": "local_llm_existing_adapter",
            "request_id": None,
            "input_tokens": None,
            "output_tokens": None,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "raw_response_hash": hashlib.sha256(raw.encode()).hexdigest(),
        }
    raise RuntimeError("configured_model_unavailable")


def configured_model_route_identity() -> str:
    settings = get_settings()
    if settings.ai_provider.strip().lower() == "codex_cli_handoff":
        return f"codex_cli_handoff:{_codex_configured_model()}"
    return f"{settings.ai_provider}:{settings.local_llm_model or 'unconfigured'}"


def prepare_ai_coach_handoff(
    db: Session,
    *,
    analysis_scope: MetricSnapshotAnalysisScope | None = None,
) -> dict[str, Any]:
    payload = coach_ai.build_ai_coach_payload(db, analysis_scope=analysis_scope)
    adapter = provider()
    result = adapter.prepare(payload)
    result["matches_count"] = payload["summary"]["matches_count"]
    result["weaknesses_count"] = len(payload["detected_weaknesses"])
    return result


def generate_ai_coach_with_provider(
    db: Session,
    *,
    analysis_scope: MetricSnapshotAnalysisScope | None = None,
) -> CoachReport:
    payload = coach_ai.build_ai_coach_payload(db, analysis_scope=analysis_scope)
    adapter = provider()
    content = adapter.generate(payload)
    return coach_ai.save_ai_coach_result(db, content, source_ref=adapter.name, payload_snapshot=payload)


def ai_provider_health() -> dict[str, Any]:
    settings = get_settings()
    adapter = provider()
    if isinstance(adapter, CodexCliHandoffProvider):
        return {"provider": adapter.name, "status": "handoff", "message": "Codex CLI handoff is available."}
    if not settings.local_llm_base_url or not settings.local_llm_model:
        return {"provider": adapter.name, "status": "not_configured"}
    return {
        "provider": adapter.name,
        "status": "configured",
        "base_url": settings.local_llm_base_url,
        "model": settings.local_llm_model,
    }


def provider() -> AIProvider:
    if get_settings().ai_provider.strip().lower() == "local_llm":
        return LocalLLMProvider()
    return CodexCliHandoffProvider()


def _codex_configured_model() -> str:
    config = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
    try:
        value = tomllib.loads(config.read_text(encoding="utf-8")).get("model")
    except (OSError, tomllib.TOMLDecodeError):
        value = None
    return str(value) if value else "configured_default"


def _codex_jsonl_telemetry(raw: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("thread_id"):
            result["thread_id"] = event["thread_id"]
        usage = event.get("usage") or (event.get("item") or {}).get("usage") or {}
        for key in ("input_tokens", "output_tokens"):
            if isinstance(usage.get(key), int):
                result[key] = int(usage[key])
        if event.get("model"):
            result["model"] = str(event["model"])
    return result


def _call_ollama(base_url: str, model: str, prompt: str, timeout: int) -> str:
    response = _post_json(f"{base_url}/api/generate", {"model": model, "prompt": prompt, "stream": False}, timeout)
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
    content = (choices[0].get("message") or {}).get("content")
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
