"""Owner-facing sync result serialization."""

from __future__ import annotations

from datetime import datetime
from time import monotonic
from typing import Any

from sqlalchemy.orm import Session

from app.services.owner.match_processing import (
    ACCEPTED_PARSER_ARTIFACT_STATUSES,
)
from app.services.owner.sync_discovery import (
    _is_actionable,
    _requires_acquisition,
)
from app.services.owner.sync_lineage import (
    _existing_lineage,
)
from app.services.owner.sync_support import (
    _failure,
    _iso,
    _log_phase,
    _utcnow,
)
from app.services.owner.sync_types import (
    _DURABLE_ENTITY_KEYS,
    DEFAULT_MAX_NEW_MATCHES,
    MAX_NEW_MATCHES,
    MAX_RETRYABLE_ATTEMPTS,
    OWNER_COACH_SYNC_OPERATION,
    OWNER_COACH_SYNC_RESULT_SCHEMA_VERSION,
    _Candidate,
    _OwnerContext,
)


def _candidate_result(
    db: Session,
    owner: _OwnerContext,
    candidate: _Candidate,
    *,
    planned: bool,
    dry_run: bool,
) -> dict[str, Any]:
    lineage = _existing_lineage(db, owner, candidate)
    if dry_run:
        status = "skipped"
        if planned:
            reason_codes = ["dry_run_planned"]
        elif _is_actionable(candidate):
            reason_codes = ["new_demo_acquisition_cap" if _requires_acquisition(candidate) else "max_new_matches_bound"]
        else:
            reason_codes = [candidate.reason_code]
    elif candidate.classification == "already_complete":
        status = "reused"
        reason_codes = [candidate.reason_code]
    elif candidate.classification == "unavailable":
        status = "unavailable"
        reason_codes = [candidate.reason_code]
    elif candidate.classification == "failed_terminal":
        status = "failed_terminal"
        reason_codes = [candidate.reason_code]
    elif not planned:
        status = "skipped"
        reason_codes = ["new_demo_acquisition_cap" if _requires_acquisition(candidate) else "max_new_matches_bound"]
    else:
        status = "created"
        reason_codes = ["planned_owner_match_cycle"]
    return {
        "identity": {
            "sharecode": candidate.sharecode,
            "external_match_id": candidate.source_match.external_match_id,
            "source_match_id": candidate.source_match.id,
            "source": candidate.source_match.source,
        },
        "discovery_classification": candidate.classification,
        "internal_classification": candidate.internal_classification,
        "selected": planned,
        "status": status,
        "reason_codes": reason_codes,
        "retry": {
            "attempt_count": candidate.attempt_count,
            "last_attempt_at": _iso(candidate.last_attempt_at) if candidate.last_attempt_at else None,
            "next_eligible_at": _iso(candidate.next_eligible_at) if candidate.next_eligible_at else None,
            "eligible": candidate.actionable
            if candidate.internal_classification in {"unavailable_retryable", "failed_retryable"}
            else None,
            "max_attempts": MAX_RETRYABLE_ATTEMPTS,
        },
        "planned_actions": _planned_actions(candidate) if dry_run and planned else [],
        "lineage": lineage,
        "failure": None,
    }

def _planned_actions(candidate: _Candidate) -> list[str]:
    actions: list[str] = []
    if candidate.demo_match is None and not candidate.source_match.demo_file:
        actions.extend(["acquire_demo", "retain_demo"])
    if candidate.artifact is None or candidate.artifact.status not in ACCEPTED_PARSER_ARTIFACT_STATUSES:
        actions.append("parse_demo")
    actions.extend(["process_owner_metrics", "refresh_coach_state"])
    return actions

def _empty_result(
    *,
    owner_user_id: int,
    started_at: datetime,
    dry_run: bool,
    max_new_matches: int,
    steam_account_id: int,
    specific_sharecode: str | None,
    specific_match_id: int | None,
) -> dict[str, Any]:
    return {
        "schema_version": OWNER_COACH_SYNC_RESULT_SCHEMA_VERSION,
        "run": {
            "status": "success",
            "owner_user_id": owner_user_id,
            "steam_account_id": steam_account_id,
            "started_at": _iso(started_at),
            "finished_at": None,
            "duration_ms": 0,
            "dry_run": dry_run,
            "max_new_matches": max_new_matches,
            "continue_on_match_error": True,
            "specific_sharecode": specific_sharecode,
            "specific_match_id": specific_match_id,
            "lock": {},
        },
        "discovery": {},
        "matches": [],
        "totals": {
            "discovered": 0,
            "new": 0,
            "reused": 0,
            "skipped": 0,
            "failed": 0,
        },
        "coach": {
            "active_missions": [],
            "latest_progress": [],
            "recommendation_suppression": {},
        },
        "mutations": {
            action: {entity: {"count": 0, "ids": []} for entity in _DURABLE_ENTITY_KEYS}
            for action in ("created", "reused", "updated", "skipped", "failed")
        },
        "warnings": [],
        "errors": [],
    }

def _early_result(
    *,
    owner_user_id: int,
    started_at: datetime,
    started_clock: float,
    dry_run: bool,
    status: str,
    reason_code: str,
    safe_message: str,
    exception_class: str,
) -> dict[str, Any]:
    result = _empty_result(
        owner_user_id=owner_user_id,
        started_at=started_at,
        dry_run=dry_run,
        max_new_matches=DEFAULT_MAX_NEW_MATCHES,
        steam_account_id=0,
        specific_sharecode=None,
        specific_match_id=None,
    )
    result["run"]["status"] = status
    result["run"]["steam_account_id"] = None
    result["run"]["lock"] = {"status": "not_acquired"}
    result["errors"].append(
        _failure(
            phase="owner_resolution",
            reason_code=reason_code,
            safe_message=safe_message,
            retryable=False,
            exception_class=exception_class,
        )
    )
    return _finish_result(result, started_clock=started_clock)

def _finish_result(result: dict[str, Any], *, started_clock: float) -> dict[str, Any]:
    result["run"]["finished_at"] = _iso(_utcnow())
    result["run"]["duration_ms"] = max(0, round((monotonic() - started_clock) * 1000))
    _log_phase("result_written", owner_user_id=result["run"].get("owner_user_id"), status=result["run"]["status"])
    return result

def _refresh_totals(result: dict[str, Any]) -> None:
    matches = result["matches"]
    result["totals"] = {
        "discovered": len(matches),
        "new": sum(item.get("discovery_classification") == "new" for item in matches),
        "reused": sum(item.get("status") == "reused" for item in matches),
        "skipped": sum(item.get("status") in {"skipped", "unavailable"} for item in matches),
        "failed": sum(item.get("status") in {"failed_retryable", "failed_terminal"} for item in matches),
    }

def _final_status(result: dict[str, Any]) -> str:
    statuses = [item.get("status") for item in result["matches"] if item.get("selected") or item.get("failure")]
    successful = sum(status in {"created", "reused"} for status in statuses)
    failed = sum(status in {"failed_retryable", "failed_terminal"} for status in statuses)
    lock_lost = any(error.get("reason_code") == "owner_sync_lock_lost" for error in result["errors"])
    coach_failed = any(error.get("phase") == "coach" for error in result["errors"])
    if lock_lost:
        return "partial_success" if successful else "blocked"
    if coach_failed:
        return "partial_success" if successful else "failed"
    if failed and successful:
        return "partial_success"
    if failed:
        return "failed"
    if successful:
        return "success"
    return "success_no_changes"

def _owner_error_code(exc: Exception) -> str:
    value = str(exc)
    return (
        value
        if value
        in {"invalid_owner_user_id", "owner_not_found", "owner_steam_account_missing", "owner_steam_account_mismatch"}
        else "owner_resolution_failed"
    )

def _owner_safe_message(exc: Exception) -> str:
    return {
        "invalid_owner_user_id": "A positive owner_user_id is required.",
        "owner_not_found": "The requested active owner does not exist.",
        "owner_steam_account_missing": "The requested owner has no linked Steam account.",
        "owner_steam_account_mismatch": "The selected Steam account does not belong to the owner.",
    }.get(str(exc), "Owner identity could not be resolved safely.")

def _discovery_error_code(exc: Exception) -> str:
    value = str(exc)
    allowed = {
        "specific_identity_conflict",
        "specific_match_not_found",
        "specific_sharecode_not_found",
        "cross_owner_match_denied",
    }
    return value if value in allowed else "owner_discovery_failed"

def _discovery_safe_message(exc: Exception) -> str:
    return {
        "specific_identity_conflict": "Choose either a specific sharecode or a specific match, not both.",
        "specific_match_not_found": "The requested match does not exist.",
        "specific_sharecode_not_found": "The requested sharecode is not present in this owner's synchronized state.",
        "cross_owner_match_denied": "The requested match or sharecode does not belong to this owner.",
    }.get(str(exc), "Owner match discovery failed closed.")

def _bounded_max_new_matches(value: int) -> int:
    if isinstance(value, bool):
        raise TypeError("max_new_matches must be an integer")
    normalized = int(value)
    if normalized < 1 or normalized > MAX_NEW_MATCHES:
        raise ValueError(f"max_new_matches must be between 1 and {MAX_NEW_MATCHES}")
    return normalized

def _match_import_target(owner_user_id: int, sharecode: str | None) -> str:
    return f"owner:{owner_user_id}:{OWNER_COACH_SYNC_OPERATION}:sharecode:{sharecode or 'unknown'}"

__all__ = (
)
