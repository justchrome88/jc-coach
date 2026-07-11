"""Owner-sync application entrypoint and phase orchestration."""

from __future__ import annotations

from time import monotonic
from typing import Any

from sqlalchemy.orm import Session

from app.services.ingestion.discovery import PERSISTED_DRY_RUN_REASON
from app.services.owner.sync_discovery import (
    _discover_candidates,
    _is_actionable,
    _populate_discovery,
    _refresh_remote_discovery,
    _resolve_owner_context,
    _selected_candidate_ids,
)
from app.services.owner.sync_execution import (
    _account_existing_lineage,
    _persist_candidate_failure,
    _process_candidate,
    _safe_refresh_coach_output,
)
from app.services.owner.sync_locks import (
    _acquire_owner_sync_lock,
    _public_lock,
    _read_active_lock,
    _refresh_owner_sync_lock,
    _release_owner_sync_lock,
)
from app.services.owner.sync_serialization import (
    _bounded_max_new_matches,
    _candidate_result,
    _discovery_error_code,
    _discovery_safe_message,
    _early_result,
    _empty_result,
    _final_status,
    _finish_result,
    _owner_error_code,
    _owner_safe_message,
    _refresh_totals,
)
from app.services.owner.sync_support import (
    _failure,
    _log_no_mutation_phases,
    _log_phase,
    _mutation_add,
    _optional_text,
    _utcnow,
)
from app.services.owner.sync_types import (
    DEFAULT_MAX_NEW_MATCHES,
    MAX_NEW_DEMO_ACQUISITIONS_PER_SYNC,
    _MatchPhaseError,
    _OwnerContext,
    _OwnerSyncLock,
    logger,
)


def run_owner_coach_sync(
    db: Session,
    *,
    owner_user_id: int,
    max_new_matches: int = DEFAULT_MAX_NEW_MATCHES,
    dry_run: bool = False,
    continue_on_match_error: bool = True,
    steam_account_id: int | None = None,
    specific_sharecode: str | None = None,
    specific_match_id: int | None = None,
) -> dict[str, Any]:
    """Run or safely reuse the complete owner-scoped import-to-coach backend cycle."""
    started_at = _utcnow()
    started_clock = monotonic()
    normalized_sharecode = _optional_text(specific_sharecode)
    try:
        bounded_max = _bounded_max_new_matches(max_new_matches)
        owner = _resolve_owner_context(
            db,
            owner_user_id=owner_user_id,
            steam_account_id=steam_account_id,
        )
    except (TypeError, ValueError, PermissionError) as exc:
        return _early_result(
            owner_user_id=owner_user_id,
            started_at=started_at,
            started_clock=started_clock,
            dry_run=dry_run,
            status="blocked",
            reason_code=_owner_error_code(exc),
            safe_message=_owner_safe_message(exc),
            exception_class=type(exc).__name__,
        )

    _log_phase("owner_resolved", owner_user_id=owner.user.id, steam_account_id=owner.steam_account.id)
    result = _empty_result(
        owner_user_id=owner.user.id,
        started_at=started_at,
        dry_run=dry_run,
        max_new_matches=bounded_max,
        steam_account_id=owner.steam_account.id,
        specific_sharecode=normalized_sharecode,
        specific_match_id=specific_match_id,
    )
    result["run"]["continue_on_match_error"] = continue_on_match_error
    lock: _OwnerSyncLock | None = None

    if dry_run:
        active_lock = _read_active_lock(db, owner_user_id=owner.user.id)
        if active_lock is not None:
            result["run"]["status"] = "already_running"
            result["run"]["lock"] = _public_lock(active_lock, status="already_running")
            return _finish_result(result, started_clock=started_clock)
        result["run"]["lock"] = {"status": "not_acquired", "reason": "dry_run"}
        completed = _run_discovery_and_cycle(
            db,
            owner=owner,
            result=result,
            max_new_matches=bounded_max,
            dry_run=True,
            continue_on_match_error=continue_on_match_error,
            specific_sharecode=normalized_sharecode,
            specific_match_id=specific_match_id,
            lock=None,
            started_clock=started_clock,
        )
        completed["discovery"].update(
            {
                "discovery_mode": "persisted_dry_run",
                "remote_discovery_performed": False,
                "remote_discovery_reason_code": PERSISTED_DRY_RUN_REASON,
            }
        )
        return completed

    lock = _acquire_owner_sync_lock(db, owner_user_id=owner.user.id)
    if lock is None:
        active_lock = _read_active_lock(db, owner_user_id=owner.user.id)
        result["run"]["status"] = "already_running"
        result["run"]["lock"] = (
            _public_lock(active_lock, status="already_running")
            if active_lock is not None
            else {"status": "already_running", "owner_user_id": owner.user.id}
        )
        return _finish_result(result, started_clock=started_clock)

    result["run"]["lock"] = _public_lock(lock, status="acquired")
    _log_phase("lock_acquired", owner_user_id=owner.user.id, recovered_stale=lock.recovered_stale)
    try:
        if not _refresh_remote_discovery(
            db,
            owner=owner,
            result=result,
            specific_sharecode=normalized_sharecode,
            specific_match_id=specific_match_id,
        ):
            result["run"]["status"] = "blocked"
            return _finish_result(result, started_clock=started_clock)
        completed = _run_discovery_and_cycle(
            db,
            owner=owner,
            result=result,
            max_new_matches=bounded_max,
            dry_run=False,
            continue_on_match_error=continue_on_match_error,
            specific_sharecode=normalized_sharecode,
            specific_match_id=specific_match_id,
            lock=lock,
            started_clock=started_clock,
        )
        completed["discovery"]["discovery_mode"] = "real_sync"
        completed["discovery"]["remote_discovery"] = completed.pop("remote_discovery")
        return completed
    except Exception as exc:  # pragma: no cover - defensive service boundary
        db.rollback()
        result["errors"].append(
            _failure(
                phase="sync",
                reason_code="unexpected_sync_failure",
                safe_message="Owner coach synchronization failed unexpectedly.",
                retryable=True,
                exception_class=type(exc).__name__,
            )
        )
        logger.error(
            "owner_coach_sync failed owner_user_id=%s exception_class=%s",
            owner.user.id,
            type(exc).__name__,
        )
        _refresh_totals(result)
        result["run"]["status"] = (
            "partial_success"
            if any(item.get("status") in {"created", "reused"} and item.get("selected") for item in result["matches"])
            else "failed"
        )
        return _finish_result(result, started_clock=started_clock)
    finally:
        db.rollback()
        released = _release_owner_sync_lock(db, lock)
        result["run"]["lock"]["released"] = released
        _log_phase("lock_released", owner_user_id=owner.user.id, released=released)

def _run_discovery_and_cycle(
    db: Session,
    *,
    owner: _OwnerContext,
    result: dict[str, Any],
    max_new_matches: int,
    dry_run: bool,
    continue_on_match_error: bool,
    specific_sharecode: str | None,
    specific_match_id: int | None,
    lock: _OwnerSyncLock | None,
    started_clock: float,
) -> dict[str, Any]:
    try:
        candidates = _discover_candidates(
            db,
            owner=owner,
            specific_sharecode=specific_sharecode,
            specific_match_id=specific_match_id,
        )
    except (ValueError, PermissionError) as exc:
        result["run"]["status"] = "blocked"
        result["errors"].append(
            _failure(
                phase="discovery",
                reason_code=_discovery_error_code(exc),
                safe_message=_discovery_safe_message(exc),
                retryable=False,
                exception_class=type(exc).__name__,
                sharecode=specific_sharecode,
                match_id=specific_match_id,
            )
        )
        return _finish_result(result, started_clock=started_clock)

    selected_ids = _selected_candidate_ids(
        candidates,
        max_new_matches=max_new_matches,
        max_new_acquisitions=MAX_NEW_DEMO_ACQUISITIONS_PER_SYNC,
    )
    _populate_discovery(result, candidates=candidates, selected_ids=selected_ids)
    _log_phase(
        "discovery_complete",
        owner_user_id=owner.user.id,
        discovered=len(candidates),
        selected=len(selected_ids),
        dry_run=dry_run,
    )

    if dry_run:
        for candidate in candidates:
            planned = candidate.source_match.id in selected_ids and _is_actionable(candidate)
            match_result = _candidate_result(db, owner, candidate, planned=planned, dry_run=True)
            result["matches"].append(match_result)
            _account_existing_lineage(result, match_result)
        result["run"]["status"] = "success" if selected_ids else "success_no_changes"
        _refresh_totals(result)
        if not _safe_refresh_coach_output(db, owner=owner, result=result):
            result["run"]["status"] = "failed"
        _log_no_mutation_phases(owner.user.id)
        return _finish_result(result, started_clock=started_clock)

    if lock is not None and not _refresh_owner_sync_lock(db, lock):
        result["run"]["status"] = "blocked"
        result["errors"].append(
            _failure(
                phase="lock",
                reason_code="owner_sync_lock_lost",
                safe_message="The owner synchronization lease was lost before work started.",
                retryable=True,
            )
        )
        return _finish_result(result, started_clock=started_clock)

    stop_after_failure = False
    for candidate in candidates:
        selected = candidate.source_match.id in selected_ids and _is_actionable(candidate)
        if not selected:
            match_result = _candidate_result(db, owner, candidate, planned=False, dry_run=False)
            if stop_after_failure and _is_actionable(candidate):
                match_result["status"] = "skipped"
                match_result["reason_codes"] = ["strict_mode_stopped"]
            result["matches"].append(match_result)
            _account_existing_lineage(result, match_result)
            continue

        if stop_after_failure:
            match_result = _candidate_result(db, owner, candidate, planned=False, dry_run=False)
            match_result["status"] = "skipped"
            match_result["reason_codes"] = ["strict_mode_stopped"]
            result["matches"].append(match_result)
            continue

        try:
            match_result = _process_candidate(db, owner=owner, candidate=candidate, result=result)
        except _MatchPhaseError as exc:
            db.rollback()
            exc = _persist_candidate_failure(db, candidate=candidate, failure=exc)
            failure = _failure(
                phase=exc.phase,
                reason_code=exc.reason_code,
                safe_message=exc.safe_message,
                retryable=exc.retryable,
                exception_class=exc.exception_class,
                sharecode=candidate.sharecode,
                match_id=candidate.demo_match.id if candidate.demo_match is not None else candidate.source_match.id,
            )
            match_result = _candidate_result(db, owner, candidate, planned=False, dry_run=False)
            match_result["status"] = "failed_retryable" if exc.retryable else "failed_terminal"
            match_result["reason_codes"] = [exc.reason_code]
            match_result["failure"] = failure
            result["errors"].append(failure)
            _mutation_add(result, "updated", "matches", candidate.source_match.id)
            _mutation_add(result, "failed", "matches", candidate.source_match.id)
            if not continue_on_match_error:
                stop_after_failure = True
        result["matches"].append(match_result)
        if lock is not None and not _refresh_owner_sync_lock(db, lock):
            result["errors"].append(
                _failure(
                    phase="lock",
                    reason_code="owner_sync_lock_lost",
                    safe_message="The owner synchronization lease was lost during processing.",
                    retryable=True,
                )
            )
            stop_after_failure = True

    _log_phase("acquisition_complete", owner_user_id=owner.user.id)
    _log_phase("parse_complete", owner_user_id=owner.user.id)
    _log_phase("metrics_complete", owner_user_id=owner.user.id)
    _safe_refresh_coach_output(db, owner=owner, result=result)
    _log_phase("coach_complete", owner_user_id=owner.user.id)
    _refresh_totals(result)
    result["run"]["status"] = _final_status(result)
    return _finish_result(result, started_clock=started_clock)

__all__ = (
    'run_owner_coach_sync',
)
