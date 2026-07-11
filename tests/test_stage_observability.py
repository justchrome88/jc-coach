from __future__ import annotations

import pytest

from app.services.shared.stage_observer import (
    emit_stage_event,
    observed_stage,
    stage_observer,
)


def test_observer_is_default_disabled_and_callback_failures_do_not_change_behavior():
    emit_stage_event(stage="preflight", event="completed", status="success")

    with stage_observer(lambda _event: (_ for _ in ()).throw(RuntimeError("observer failed"))):
        emit_stage_event(stage="preflight", event="completed", status="success")


def test_observed_stage_emits_timed_sanitized_terminal_event():
    events = []
    with stage_observer(events.append):
        with observed_stage(
            "impact_leak_provider",
            trace_id="safe",
            api_token="must-not-leak",
            signed_download_url="https://example.invalid/private",
        ):
            pass

    assert len(events) == 1
    event = events[0]
    assert event["schema_version"] == "jc-coach-stage-trace-v1"
    assert event["stage"] == "impact_leak_provider"
    assert event["status"] == "success"
    assert event["api_token"] == "[redacted]"
    assert event["signed_download_url"] == "[redacted]"
    assert event["duration_ms"] >= 0
    assert event["started_at_utc"]
    assert event["finished_at_utc"]


def test_observed_stage_emits_sanitized_failure_and_reraises():
    events = []
    with pytest.raises(ValueError, match="expected"):
        with stage_observer(events.append):
            with observed_stage("parser", failure_status="failed_retryable"):
                raise ValueError("expected raw detail")

    assert events[0]["status"] == "failed_retryable"
    assert events[0]["sanitized_error"] == "ValueError"


def test_invalid_terminal_status_is_rejected_only_when_observed():
    with stage_observer(list().append):
        with pytest.raises(ValueError, match="invalid_stage_terminal_status"):
            emit_stage_event(stage="parser", event="completed", status="unknown")
