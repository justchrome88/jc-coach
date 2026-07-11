"""Optional structured stage observations for bounded acceptance runs."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from time import monotonic
from typing import Any

STAGE_TRACE_SCHEMA_VERSION = "jc-coach-stage-trace-v1"
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


@contextmanager
def stage_observer(callback: StageObserver | None) -> Iterator[None]:
    """Install a process-local observer for the current context only."""
    token = _OBSERVER.set(callback)
    try:
        yield
    finally:
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
    payload = {
        "schema_version": STAGE_TRACE_SCHEMA_VERSION,
        "stage": str(stage),
        "event": str(event),
        "status": status,
        **fields,
    }
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
    **fields: Any,
) -> Iterator[None]:
    """Measure a stage and emit exactly one terminal observation."""
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
        **fields,
    )


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
    "STAGE_TERMINAL_STATUSES",
    "STAGE_TRACE_SCHEMA_VERSION",
    "emit_stage_event",
    "observed_stage",
    "stage_observer",
)
