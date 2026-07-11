"""Owner-sync shared pure support primitives."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.db.models import (
    Match,
    MetricSnapshot,
)
from app.services.owner.sync_types import (
    _URL_RE,
    _OwnerContext,
    logger,
)
from app.services.shared.stage_observer import emit_stage_event

_TRACE_STAGE_BY_OWNER_PHASE = {
    "owner_resolved": "owner_resolution",
    "discovery_complete": "target_discovery",
    "acquisition_complete": "demo_acquisition",
    "parse_complete": "parser",
    "metrics_complete": "metric_computation",
    "coach_complete": "mission_progress",
    "result_written": "final_acceptance",
}


def _match_belongs_to_owner(match: Match, owner: _OwnerContext) -> bool:
    has_direct_owner = False
    if match.user_id is not None:
        has_direct_owner = True
        if match.user_id != owner.user.id:
            return False
    if match.steam_account_id is not None:
        has_direct_owner = True
        if match.steam_account_id != owner.steam_account.id:
            return False
    if has_direct_owner:
        return True
    raw = _json_mapping(match.raw_json)
    raw_account_id = _optional_int(raw.get("steam_account_id"))
    raw_steam_id = _optional_text(raw.get("steam_id"))
    return raw_account_id == owner.steam_account.id and raw_steam_id == owner.steam_account.steam_id

def _require_match_owner(match: Match, owner: _OwnerContext) -> None:
    if not _match_belongs_to_owner(match, owner):
        raise PermissionError("cross_owner_match_denied")

def _snapshot_belongs_to_owner(snapshot: MetricSnapshot, owner: _OwnerContext) -> bool:
    return snapshot.player_steamid == owner.steam_account.steam_id or snapshot.player_key == (
        f"steam:{owner.steam_account.steam_id}"
    )

def _account_table_delta(result: dict[str, Any], entity: str, before: set[int], after: set[int]) -> None:
    for item in sorted(after - before):
        _mutation_add(result, "created", entity, item)

def _mutation_add(result: dict[str, Any], action: str, entity: str, entity_id: int | None) -> None:
    if entity_id is None:
        return
    bucket = result["mutations"][action][entity]
    if entity_id not in bucket["ids"]:
        bucket["ids"].append(entity_id)
        bucket["ids"].sort()
        bucket["count"] = len(bucket["ids"])

def _sanitize_message(value: str) -> str:
    return _URL_RE.sub("[redacted-url]", str(value))[:500]

def _failure(
    *,
    phase: str,
    reason_code: str,
    safe_message: str,
    retryable: bool,
    exception_class: str | None = None,
    sharecode: str | None = None,
    match_id: int | None = None,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "reason_code": reason_code,
        "safe_message": _sanitize_message(safe_message),
        "retryable": retryable,
        "identity": {"sharecode": sharecode, "match_id": match_id},
        "exception_class": exception_class,
    }

def _json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}

def _int_list(value: Any) -> list[int]:
    if not isinstance(value, (list, tuple, set)):
        return []
    output: list[int] = []
    for item in value:
        parsed = _optional_int(item)
        if parsed is not None and parsed not in output:
            output.append(parsed)
    return output

def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

def _iso(value: datetime) -> str:
    return value.isoformat()

def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed.replace(tzinfo=None)

def _log_phase(phase: str, **identifiers: Any) -> None:
    details = " ".join(f"{key}={value}" for key, value in identifiers.items() if value is not None)
    logger.info("owner_coach_sync phase=%s %s", phase, details)
    trace_stage = _TRACE_STAGE_BY_OWNER_PHASE.get(phase)
    if trace_stage is not None:
        trace_fields = dict(identifiers)
        runtime_status = trace_fields.pop("status", None)
        trace_status = {
            "already_running": "reused",
            "blocked": "blocked",
            "failed": "failed_retryable",
            "success_no_changes": "reused",
        }.get(str(runtime_status), "success")
        emit_stage_event(
            stage=trace_stage,
            event="state_transition",
            status=trace_status,
            implementation_version="owner-coach-sync-result-v1",
            runtime_status=runtime_status,
            **trace_fields,
        )

def _log_no_mutation_phases(owner_user_id: int) -> None:
    for phase in ("acquisition_complete", "parse_complete", "metrics_complete", "coach_complete"):
        _log_phase(phase, owner_user_id=owner_user_id, dry_run=True)

__all__ = (
)
