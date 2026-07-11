from __future__ import annotations

import time

import pytest

from app.services.shared.stage_observer import (
    REQUIRED_ACCEPTANCE_STAGES,
    STAGE_TRACE_SCHEMA_VERSION_V2,
    StageTraceValidationError,
    emit_stage_event,
    observed_stage,
    stage_observer,
    validate_stage_trace,
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


def test_v2_real_delay_emits_bracketed_timing_attempt_and_implementation():
    events = []
    with stage_observer(
        events.append,
        schema_version=STAGE_TRACE_SCHEMA_VERSION_V2,
        trace_mode="integration_replay",
        trace_id="trace-safe",
        run_id="run-safe",
    ):
        with observed_stage(
            "impact_leak_provider",
            status="reused",
            attempt=2,
            implementation_version="provider-reuse-v1",
        ):
            time.sleep(0.01)

    event = events[0]
    assert event["trace_mode"] == "integration_replay"
    assert event["attempt"] == 2
    assert event["implementation_version"] == "provider-reuse-v1"
    assert event["duration_ms"] > 0
    assert event["started_at_utc"] <= event["finished_at_utc"]


def test_v2_provider_retry_attempt_is_preserved():
    events = []
    with stage_observer(
        events.append,
        schema_version=STAGE_TRACE_SCHEMA_VERSION_V2,
        trace_mode="failure_fixture",
        trace_id="trace-safe",
        run_id="run-safe",
    ):
        with observed_stage(
            "impact_leak_provider",
            status="failed_retryable",
            attempt=2,
            implementation_version="configured-provider-v1",
        ):
            pass

    assert events[0]["attempt"] == 2


def test_v1_validation_remains_supported():
    result = validate_stage_trace(
        [
            {
                "schema_version": "jc-coach-stage-trace-v1",
                "stage": "preflight",
                "event": "completed",
                "status": "success",
                "duration_ms": 0,
            }
        ]
    )

    assert result["trace_mode"] == "summary"
    assert result["all_zero_durations"] is True


@pytest.mark.parametrize("missing", ["started_at_utc", "attempt", "implementation_version"])
def test_v2_rejects_missing_required_timing_fields(missing):
    record = _v2_record(stage="preflight", duration_ms=1)
    record.pop(missing)

    with pytest.raises(StageTraceValidationError, match="missing_v2_fields"):
        validate_stage_trace([record])


def test_all_zero_summary_cannot_claim_live_mode():
    record = _v2_record(stage="preflight", duration_ms=0, trace_mode="live")

    with pytest.raises(StageTraceValidationError, match="all_zero_duration_trace"):
        validate_stage_trace([record])


def test_live_trace_cannot_reuse_external_or_provider_stage():
    record = _v2_record(
        stage="demo_acquisition",
        duration_ms=1,
        trace_mode="live",
        status="reused",
    )

    with pytest.raises(StageTraceValidationError, match="live_trace_reuses"):
        validate_stage_trace([record])


def test_complete_trace_validation_rejects_duplicate_or_missing_stages():
    records = [
        _v2_record(stage=stage, duration_ms=1 if index == 0 else 0)
        for index, stage in enumerate(REQUIRED_ACCEPTANCE_STAGES)
    ]
    validate_stage_trace(records, required_stages=REQUIRED_ACCEPTANCE_STAGES)

    with pytest.raises(StageTraceValidationError, match="duplicate_terminal_stage"):
        validate_stage_trace([*records, records[0]], required_stages=REQUIRED_ACCEPTANCE_STAGES)
    with pytest.raises(StageTraceValidationError, match="missing_terminal_stages"):
        validate_stage_trace(records[:-1], required_stages=REQUIRED_ACCEPTANCE_STAGES)


def _v2_record(
    *,
    stage: str,
    duration_ms: int,
    trace_mode: str = "integration_replay",
    status: str = "success",
):
    return {
        "schema_version": "jc-coach-stage-trace-v2",
        "trace_mode": trace_mode,
        "trace_id": "trace-safe",
        "run_id": "run-safe",
        "stage": stage,
        "event": "completed",
        "attempt": 1,
        "started_at_utc": "2026-07-11T10:00:00+00:00",
        "finished_at_utc": f"2026-07-11T10:00:00.{duration_ms:03d}+00:00",
        "duration_ms": duration_ms,
        "status": status,
        "implementation_version": "fixture-v1",
    }
