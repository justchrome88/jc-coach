"""Optional structured stage observations for bounded acceptance runs."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from time import monotonic
from typing import Any

STAGE_TRACE_SCHEMA_VERSION = "jc-coach-stage-trace-v1"
STAGE_TRACE_SCHEMA_VERSION_V2 = "jc-coach-stage-trace-v2"
STAGE_TRACE_MODES = frozenset({"live", "integration_replay", "failure_fixture", "summary"})
REQUIRED_STAGE_TRACE_V2_FIELDS = (
    "schema_version",
    "trace_mode",
    "trace_id",
    "run_id",
    "stage",
    "event",
    "attempt",
    "started_at_utc",
    "finished_at_utc",
    "duration_ms",
    "status",
    "implementation_version",
)
REQUIRED_ACCEPTANCE_STAGES = (
    "preflight",
    "owner_resolution",
    "target_discovery",
    "steam_history",
    "demo_acquisition",
    "storage_integrity",
    "import_identity",
    "parser",
    "normalized_event_set",
    "metric_computation",
    "metric_validation",
    "baseline_resolution",
    "impact_leak_evidence",
    "impact_leak_provider",
    "impact_leak_validation",
    "impact_leak_proposal",
    "bad_fight_selection_evidence",
    "bad_fight_selection_provider",
    "bad_fight_selection_validation",
    "bad_fight_selection_proposal",
    "impact_leak_activation",
    "bad_fight_selection_activation",
    "subsequent_match_evaluation",
    "mission_progress",
    "api_serialization",
    "idempotent_repeat",
    "concurrency",
    "failure_smoke",
    "final_acceptance",
)
STAGE_TERMINAL_STATUSES = frozenset(
    {
        "success",
        "reused",
        "skipped_with_reason",
        "insufficient_data",
        "failed_retryable",
        "failed_terminal",
        "blocked",
    }
)

StageObserver = Callable[[Mapping[str, Any]], None]
_OBSERVER: ContextVar[StageObserver | None] = ContextVar("jc_coach_stage_observer", default=None)
_TRACE_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar("jc_coach_stage_trace_context", default=None)


class StageTraceValidationError(ValueError):
    """Raised when a stage trace does not satisfy its declared schema."""


@contextmanager
def stage_observer(
    callback: StageObserver | None,
    *,
    schema_version: str = STAGE_TRACE_SCHEMA_VERSION,
    trace_mode: str | None = None,
    trace_id: str | None = None,
    run_id: str | None = None,
) -> Iterator[None]:
    """Install a process-local observer for the current context only."""
    if schema_version not in {STAGE_TRACE_SCHEMA_VERSION, STAGE_TRACE_SCHEMA_VERSION_V2}:
        raise ValueError("unsupported_stage_trace_schema_version")
    if schema_version == STAGE_TRACE_SCHEMA_VERSION_V2:
        if trace_mode not in STAGE_TRACE_MODES:
            raise ValueError("invalid_stage_trace_mode")
        if not trace_id or not run_id:
            raise ValueError("missing_stage_trace_identity")
    context = {
        "schema_version": schema_version,
        "trace_mode": trace_mode,
        "trace_id": trace_id,
        "run_id": run_id,
    }
    token = _OBSERVER.set(callback)
    context_token = _TRACE_CONTEXT.set(context)
    try:
        yield
    finally:
        _TRACE_CONTEXT.reset(context_token)
        _OBSERVER.reset(token)


def emit_stage_event(
    *,
    stage: str,
    event: str,
    status: str,
    started_at_utc: str | None = None,
    finished_at_utc: str | None = None,
    duration_ms: int | None = None,
    **fields: Any,
) -> None:
    """Emit a sanitized trace-ready event when an observer is installed."""
    observer = _OBSERVER.get()
    if observer is None:
        return
    if status not in STAGE_TERMINAL_STATUSES:
        raise ValueError("invalid_stage_terminal_status")
    context = _TRACE_CONTEXT.get() or {"schema_version": STAGE_TRACE_SCHEMA_VERSION}
    payload = {
        "schema_version": context["schema_version"],
        "stage": str(stage),
        "event": str(event),
        "status": status,
        **fields,
    }
    if context["schema_version"] == STAGE_TRACE_SCHEMA_VERSION_V2:
        payload.update(
            {
                "trace_mode": context["trace_mode"],
                "trace_id": context["trace_id"],
                "run_id": context["run_id"],
            }
        )
    if started_at_utc is not None:
        payload["started_at_utc"] = started_at_utc
    if finished_at_utc is not None:
        payload["finished_at_utc"] = finished_at_utc
    if duration_ms is not None:
        payload["duration_ms"] = max(0, int(duration_ms))
    sanitized = _sanitize(payload)
    try:
        observer(sanitized)
    except Exception:
        # Observability must never change Product behavior.
        return


@contextmanager
def observed_stage(
    stage: str,
    *,
    event: str = "completed",
    status: str = "success",
    failure_status: str = "failed_terminal",
    attempt: int = 1,
    implementation_version: str | None = None,
    **fields: Any,
) -> Iterator[None]:
    """Measure a stage and emit exactly one terminal observation."""
    context = _TRACE_CONTEXT.get()
    if context and context.get("schema_version") == STAGE_TRACE_SCHEMA_VERSION_V2:
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise ValueError("invalid_stage_attempt")
        if not implementation_version:
            raise ValueError("missing_stage_implementation_version")
    started = datetime.now(UTC)
    started_clock = monotonic()
    try:
        yield
    except Exception as exc:
        finished = datetime.now(UTC)
        emit_stage_event(
            stage=stage,
            event=event,
            status=failure_status,
            started_at_utc=started.isoformat(),
            finished_at_utc=finished.isoformat(),
            duration_ms=round((monotonic() - started_clock) * 1000),
            sanitized_error=type(exc).__name__,
            attempt=attempt,
            implementation_version=implementation_version,
            **fields,
        )
        raise
    finished = datetime.now(UTC)
    emit_stage_event(
        stage=stage,
        event=event,
        status=status,
        started_at_utc=started.isoformat(),
        finished_at_utc=finished.isoformat(),
        duration_ms=round((monotonic() - started_clock) * 1000),
        attempt=attempt,
        implementation_version=implementation_version,
        **fields,
    )


def validate_stage_trace(
    records: Sequence[Mapping[str, Any]],
    *,
    required_stages: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Validate compatible v1 summaries or strict v2 timed terminal traces."""
    if not records:
        raise StageTraceValidationError("empty_stage_trace")
    versions = {record.get("schema_version") for record in records}
    if len(versions) != 1:
        raise StageTraceValidationError("mixed_stage_trace_schema_versions")
    version = next(iter(versions))
    if version == STAGE_TRACE_SCHEMA_VERSION:
        _validate_v1_records(records)
        return {
            "schema_version": version,
            "trace_mode": "summary",
            "record_count": len(records),
            "all_zero_durations": all(int(record.get("duration_ms") or 0) == 0 for record in records),
        }
    if version != STAGE_TRACE_SCHEMA_VERSION_V2:
        raise StageTraceValidationError("unsupported_stage_trace_schema_version")
    return _validate_v2_records(records, required_stages=required_stages)


def _validate_v1_records(records: Sequence[Mapping[str, Any]]) -> None:
    for record in records:
        if not record.get("stage") or not record.get("event"):
            raise StageTraceValidationError("invalid_v1_terminal_record")
        if record.get("status") not in STAGE_TERMINAL_STATUSES:
            raise StageTraceValidationError("invalid_stage_terminal_status")


def _validate_v2_records(
    records: Sequence[Mapping[str, Any]],
    *,
    required_stages: Sequence[str] | None,
) -> dict[str, Any]:
    stages: list[str] = []
    durations: list[int] = []
    trace_identities: set[tuple[Any, Any, Any]] = set()
    live_reuse_stages = {
        "steam_history",
        "demo_acquisition",
        "parser",
        "impact_leak_provider",
        "bad_fight_selection_provider",
    }
    for record in records:
        missing = [field for field in REQUIRED_STAGE_TRACE_V2_FIELDS if field not in record]
        if missing:
            raise StageTraceValidationError(f"missing_v2_fields:{','.join(missing)}")
        if record.get("trace_mode") not in STAGE_TRACE_MODES:
            raise StageTraceValidationError("invalid_stage_trace_mode")
        if record.get("status") not in STAGE_TERMINAL_STATUSES:
            raise StageTraceValidationError("invalid_stage_terminal_status")
        attempt = record.get("attempt")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise StageTraceValidationError("invalid_stage_attempt")
        if not isinstance(record.get("implementation_version"), str) or not record["implementation_version"].strip():
            raise StageTraceValidationError("missing_stage_implementation_version")
        started = _parse_utc_timestamp(record.get("started_at_utc"), "started_at_utc")
        finished = _parse_utc_timestamp(record.get("finished_at_utc"), "finished_at_utc")
        if started > finished:
            raise StageTraceValidationError("stage_timestamp_order_invalid")
        duration = record.get("duration_ms")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
            raise StageTraceValidationError("invalid_stage_duration")
        wall_duration = round((finished - started).total_seconds() * 1000)
        if abs(wall_duration - duration) > max(50, round(wall_duration * 0.20)):
            raise StageTraceValidationError("stage_duration_not_bracketed_by_timestamps")
        if (
            record.get("trace_mode") == "live"
            and record.get("status") == "reused"
            and record.get("stage") in live_reuse_stages
        ):
            raise StageTraceValidationError("live_trace_reuses_external_or_provider_stage")
        stages.append(str(record["stage"]))
        durations.append(duration)
        trace_identities.add((record.get("trace_mode"), record.get("trace_id"), record.get("run_id")))
    if len(trace_identities) != 1:
        raise StageTraceValidationError("inconsistent_stage_trace_identity")
    if len(stages) != len(set(stages)):
        raise StageTraceValidationError("duplicate_terminal_stage")
    expected = tuple(required_stages or ())
    if expected:
        missing_stages = sorted(set(expected) - set(stages))
        extra_stages = sorted(set(stages) - set(expected))
        if missing_stages:
            raise StageTraceValidationError(f"missing_terminal_stages:{','.join(missing_stages)}")
        if extra_stages:
            raise StageTraceValidationError(f"unexpected_terminal_stages:{','.join(extra_stages)}")
    if not any(duration > 0 for duration in durations):
        raise StageTraceValidationError("all_zero_duration_trace")
    trace_mode, trace_id, run_id = next(iter(trace_identities))
    return {
        "schema_version": STAGE_TRACE_SCHEMA_VERSION_V2,
        "trace_mode": trace_mode,
        "trace_id": trace_id,
        "run_id": run_id,
        "record_count": len(records),
        "required_stage_count": len(expected),
        "all_zero_durations": False,
        "non_zero_duration_count": sum(duration > 0 for duration in durations),
    }


def _parse_utc_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise StageTraceValidationError(f"missing_{field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StageTraceValidationError(f"invalid_{field}") from exc
    if parsed.tzinfo is None:
        raise StageTraceValidationError(f"non_utc_{field}")
    return parsed.astimezone(UTC)


def _sanitize(value: Any, *, key: str = "") -> Any:
    lowered = key.lower()
    if any(
        marker in lowered
        for marker in (
            "secret",
            "password",
            "token",
            "cookie",
            "authorization",
            "url",
            "path",
            "command",
            "prompt",
            "response",
            "payload",
        )
    ):
        return "[redacted]"
    if isinstance(value, Mapping):
        return {str(item_key): _sanitize(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_sanitize(item, key=key) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


__all__ = (
    "REQUIRED_ACCEPTANCE_STAGES",
    "REQUIRED_STAGE_TRACE_V2_FIELDS",
    "STAGE_TERMINAL_STATUSES",
    "STAGE_TRACE_SCHEMA_VERSION",
    "STAGE_TRACE_SCHEMA_VERSION_V2",
    "STAGE_TRACE_MODES",
    "StageTraceValidationError",
    "emit_stage_event",
    "observed_stage",
    "stage_observer",
    "validate_stage_trace",
)
