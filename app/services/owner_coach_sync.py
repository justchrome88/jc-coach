from __future__ import annotations

import json
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Any

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    AnalysisRun,
    AppSetting,
    CoachHypothesis,
    DemoParseArtifact,
    ImportJob,
    Match,
    MetricSnapshot,
    MissionProgressEvaluation,
    SteamAccount,
    User,
)
from app.services.ai_coach import (
    ANALYSIS_RUN_SOURCE,
    POST_METRICS_COACH_LOOP_HOOK,
    POST_METRICS_COACH_LOOP_SOURCE,
    build_ai_coach_payload,
)
from app.services.ingestion.discovery import PERSISTED_DRY_RUN_REASON
from app.services.ingestion.jobs import IMPORT_JOB_ACTIVE_STATUSES, IMPORT_JOB_COMPLETED
from app.services.ingestion.orchestration import run_demo_import_orchestration
from app.services.ingestion.steam import queue_match_history_sync, sync_match_history_job
from app.services.metrics.snapshots import owner_player_metric_snapshot_scope
from app.services.mission_domain import active_mission_context_for_owner, list_mission_criteria
from app.services.owner.match_processing import (
    ACCEPTED_PARSER_ARTIFACT_STATUSES,
    process_owner_match_after_parser_artifact,
)
from app.services.parsing.demo_parser import import_demo_file

OWNER_COACH_SYNC_RESULT_SCHEMA_VERSION = "owner-coach-sync-result-v1"
OWNER_COACH_SYNC_OPERATION = "owner_coach_sync"
OWNER_COACH_SYNC_LOCK_TTL = timedelta(minutes=30)
DEFAULT_MAX_NEW_MATCHES = 1
MAX_NEW_MATCHES = 50
MAX_NEW_DEMO_ACQUISITIONS_PER_SYNC = 1
MAX_RETRYABLE_ATTEMPTS = 2
RETRY_COOLDOWN = timedelta(minutes=15)
METRIC_SNAPSHOT_SOURCES = frozenset({"core_combat_metrics", "utility_metrics"})
INTERNAL_CLASSIFICATIONS = (
    "fresh_actionable",
    "incomplete_resumable",
    "already_complete",
    "legacy_stale_pending",
    "unavailable_retryable",
    "unavailable_terminal",
    "failed_retryable",
    "failed_terminal",
    "cross_owner_denied",
    "invalid_identity",
)

_DURABLE_ENTITY_KEYS = (
    "import_jobs",
    "matches",
    "parser_artifacts",
    "metric_snapshots",
    "analysis_runs",
    "hypotheses",
    "missions",
    "criteria",
    "progress_evaluations",
)
_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)

logger = logging.getLogger(__name__)


@dataclass
class _OwnerContext:
    user: User
    steam_account: SteamAccount


@dataclass
class _OwnerSyncLock:
    key: str
    token: str
    value: str
    acquired_at: datetime
    expires_at: datetime
    recovered_stale: bool = False


@dataclass
class _Candidate:
    source_match: Match
    demo_match: Match | None
    sharecode: str | None
    classification: str
    reason_code: str
    artifact: DemoParseArtifact | None
    snapshots: list[MetricSnapshot]
    internal_classification: str
    actionable: bool
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    next_eligible_at: datetime | None = None


@dataclass(frozen=True)
class _DiscoveryBoundary:
    source: str
    account_last_sync_at: datetime | None
    cursor: str | None
    accepted_positions: dict[str, int]
    latest_completed_position: int | None


class _MatchPhaseError(RuntimeError):
    def __init__(
        self,
        *,
        phase: str,
        reason_code: str,
        safe_message: str,
        retryable: bool,
        exception_class: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.phase = phase
        self.reason_code = reason_code
        self.safe_message = safe_message
        self.retryable = retryable
        self.exception_class = exception_class


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


def _refresh_remote_discovery(
    db: Session,
    *,
    owner: _OwnerContext,
    result: dict[str, Any],
    specific_sharecode: str | None,
    specific_match_id: int | None,
) -> bool:
    if specific_sharecode or specific_match_id is not None:
        result["remote_discovery"] = {
            "performed": False,
            "reason_code": "specific_persisted_identity_requested",
        }
        return True
    if not owner.steam_account.match_auth_code:
        result["remote_discovery"] = {
            "performed": False,
            "reason_code": "remote_discovery_not_configured_for_owner",
        }
        return True

    before_match_ids = _table_ids(db, Match)
    try:
        job = queue_match_history_sync(db, owner.steam_account.id)
        sync_result = sync_match_history_job(db, job.id)
    except Exception as exc:
        db.rollback()
        result["remote_discovery"] = {
            "performed": True,
            "status": "provider_error",
            "reason_code": "remote_provider_failure",
        }
        result["errors"].append(
            _failure(
                phase="remote_discovery",
                reason_code="remote_provider_failure",
                safe_message="Remote Steam discovery failed.",
                retryable=True,
                exception_class=type(exc).__name__,
            )
        )
        return False

    _mutation_add(result, "created", "import_jobs", job.id)
    after_match_ids = _table_ids(db, Match)
    _account_table_delta(result, "matches", before_match_ids, after_match_ids)
    payload = sync_result.get("result") if isinstance(sync_result, dict) else None
    payload = payload if isinstance(payload, dict) else {}
    if sync_result.get("status") not in {"completed", "succeeded"}:
        result["remote_discovery"] = {
            "performed": True,
            "status": "provider_error",
            "reason_code": "remote_provider_failure",
            "import_job_id": job.id,
        }
        result["errors"].append(
            _failure(
                phase="remote_discovery",
                reason_code="remote_provider_failure",
                safe_message="Remote Steam discovery did not complete successfully.",
                retryable=True,
            )
        )
        _mutation_add(result, "failed", "import_jobs", job.id)
        return False
    result["remote_discovery"] = {
        "performed": True,
        "status": "success",
        "reason_code": "remote_discovery_completed_before_persisted_classification",
        "import_job_id": job.id,
        "collected": int(payload.get("collected", 0)),
        "inserted": int(payload.get("inserted", 0)),
        "duplicates": int(payload.get("duplicates", 0)),
        "cursor_advanced": bool(payload.get("cursor_advanced")),
        "sync_outcome": payload.get("sync_outcome"),
    }
    return True


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


def _process_candidate(
    db: Session,
    *,
    owner: _OwnerContext,
    candidate: _Candidate,
    result: dict[str, Any],
) -> dict[str, Any]:
    match_result = _candidate_result(db, owner, candidate, planned=True, dry_run=False)
    source_match = candidate.source_match
    demo_match = candidate.demo_match
    import_job: ImportJob | None = _candidate_import_job(db, candidate)
    parser_created = False
    import_job_created = False

    if demo_match is None and not source_match.demo_file:
        before_match_ids = _table_ids(db, Match)
        before_job_ids = _table_ids(db, ImportJob)
        try:
            import_job = run_demo_import_orchestration(
                db,
                provider="steam",
                payload={"share_code": candidate.sharecode},
                user_id=owner.user.id,
                steam_account_id=owner.steam_account.id,
                logical_target_key=_match_import_target(owner.user.id, candidate.sharecode),
            )
        except Exception as exc:
            raise _MatchPhaseError(
                phase="acquisition",
                reason_code="acquisition_exception",
                safe_message="Demo acquisition failed before a retained artifact became available.",
                retryable=True,
                exception_class=type(exc).__name__,
            ) from exc
        _account_table_delta(result, "import_jobs", before_job_ids, _table_ids(db, ImportJob))
        import_job_created = import_job.id not in before_job_ids
        _account_table_delta(result, "matches", before_match_ids, _table_ids(db, Match))
        if import_job.status != IMPORT_JOB_COMPLETED:
            source_match.import_job_id = import_job.id
            db.commit()
            db.refresh(source_match)
            raise _import_job_phase_error(import_job)
        db.refresh(source_match)
        if not source_match.demo_file or not Path(source_match.demo_file).is_file():
            raise _MatchPhaseError(
                phase="retention",
                reason_code="retained_demo_missing",
                safe_message="Acquisition completed without an available retained demo artifact.",
                retryable=True,
            )

    if import_job is not None:
        match_result["lineage"]["import_job"] = _import_job_lineage(import_job)
        if not import_job_created:
            _mutation_add(result, "reused", "import_jobs", import_job.id)

    needs_parse = (
        demo_match is None
        or candidate.artifact is None
        or candidate.artifact.status not in ACCEPTED_PARSER_ARTIFACT_STATUSES
    )
    if needs_parse:
        parser_path = _parser_source_path(demo_match) if demo_match is not None else None
        parser_path = parser_path or _parser_source_path(source_match)
        if parser_path is None:
            raise _MatchPhaseError(
                phase="parse",
                reason_code="parser_source_missing",
                safe_message="No retained demo artifact is available for parsing.",
                retryable=True,
            )
        before_match_ids = _table_ids(db, Match)
        before_artifact_ids = _table_ids(db, DemoParseArtifact)
        existing_artifact_id = candidate.artifact.id if candidate.artifact is not None else None
        try:
            import_result = import_demo_file(
                db,
                parser_path,
                original_filename=f"{candidate.sharecode or source_match.external_match_id or source_match.id}.dem",
                player_identifier=owner.steam_account.steam_id,
                acquisition_metadata={
                    "import_job_id": import_job.id if import_job is not None else source_match.import_job_id,
                    "source_match_id": source_match.id,
                    "source_match_external_id": source_match.external_match_id,
                    "share_code": candidate.sharecode,
                    "user_id": owner.user.id,
                    "steam_account_id": owner.steam_account.id,
                    "steam_id": owner.steam_account.steam_id,
                },
                evaluate_recommendations=False,
            )
        except Exception as exc:
            raise _MatchPhaseError(
                phase="parse",
                reason_code="parse_failed",
                safe_message="The retained demo could not be parsed into an accepted artifact.",
                retryable=True,
                exception_class=type(exc).__name__,
            ) from exc
        _account_table_delta(result, "matches", before_match_ids, _table_ids(db, Match))
        _account_table_delta(result, "parser_artifacts", before_artifact_ids, _table_ids(db, DemoParseArtifact))
        demo_match_id = _optional_int(import_result.get("match_id"))
        demo_match = db.get(Match, demo_match_id) if demo_match_id is not None else None
        if demo_match is None:
            raise _MatchPhaseError(
                phase="parse",
                reason_code="parsed_match_missing",
                safe_message="Parsing did not return a durable owner match.",
                retryable=True,
            )
        _require_match_owner(demo_match, owner)
        parser_created = candidate.artifact is None
        _link_source_to_demo_match(db, source_match=source_match, demo_match=demo_match)
        _mutation_add(result, "updated", "matches", source_match.id)
        if existing_artifact_id is not None:
            replacement = _latest_artifact(db, demo_match.id)
            _mutation_add(result, "updated", "parser_artifacts", replacement.id if replacement is not None else None)
    else:
        _require_match_owner(demo_match, owner)
        _mutation_add(result, "reused", "matches", demo_match.id)

    artifact = _latest_artifact(db, demo_match.id)
    if artifact is None or artifact.status not in ACCEPTED_PARSER_ARTIFACT_STATUSES:
        raise _MatchPhaseError(
            phase="parse",
            reason_code="accepted_parser_artifact_missing",
            safe_message="An accepted parser artifact is required before metrics and coach processing.",
            retryable=True,
        )
    if parser_created:
        _mutation_add(result, "created", "parser_artifacts", artifact.id)
    else:
        _mutation_add(result, "reused", "parser_artifacts", artifact.id)

    try:
        processing = process_owner_match_after_parser_artifact(
            db,
            user_id=owner.user.id,
            match_id=demo_match.id,
            parser_artifact_id=artifact.id,
            source_metadata={
                "operation": OWNER_COACH_SYNC_OPERATION,
                "source_match_id": source_match.id,
                "sharecode": candidate.sharecode,
            },
        )
    except Exception as exc:
        raise _MatchPhaseError(
            phase="metrics",
            reason_code="owner_match_processing_exception",
            safe_message="Owner-scoped metric and coach processing failed.",
            retryable=True,
            exception_class=type(exc).__name__,
        ) from exc
    if processing.get("status") != "processed":
        raise _MatchPhaseError(
            phase="metrics",
            reason_code=str(processing.get("issue") or "owner_match_processing_blocked"),
            safe_message="Owner-scoped metric and coach processing did not accept this match.",
            retryable=processing.get("status") != "blocked",
        )

    _account_processing_mutations(result, processing)
    match_result["lineage"] = _processing_lineage(
        source_match=source_match,
        demo_match=demo_match,
        sharecode=candidate.sharecode,
        import_job=import_job,
        artifact=artifact,
        processing=processing,
    )
    match_result["status"] = "created" if _lineage_has_creation(processing, parser_created=parser_created) else "reused"
    match_result["reason_codes"] = ["owner_match_cycle_completed"]
    return match_result


def _resolve_owner_context(
    db: Session,
    *,
    owner_user_id: int,
    steam_account_id: int | None,
) -> _OwnerContext:
    if isinstance(owner_user_id, bool) or int(owner_user_id) <= 0:
        raise ValueError("invalid_owner_user_id")
    user = db.get(User, int(owner_user_id))
    if user is None or not user.is_active:
        raise ValueError("owner_not_found")
    stmt = select(SteamAccount).where(SteamAccount.user_id == user.id).order_by(SteamAccount.id.asc())
    if steam_account_id is not None:
        stmt = stmt.where(SteamAccount.id == int(steam_account_id))
    account = db.scalar(stmt)
    if account is None:
        raise ValueError("owner_steam_account_missing")
    if account.user_id != user.id:
        raise PermissionError("owner_steam_account_mismatch")
    return _OwnerContext(user=user, steam_account=account)


def _discover_candidates(
    db: Session,
    *,
    owner: _OwnerContext,
    specific_sharecode: str | None,
    specific_match_id: int | None,
) -> list[_Candidate]:
    if specific_sharecode and specific_match_id is not None:
        raise ValueError("specific_identity_conflict")
    if specific_match_id is not None:
        match = db.get(Match, specific_match_id)
        if match is None:
            raise ValueError("specific_match_not_found")
        _require_match_owner(match, owner)
        boundary = _build_discovery_boundary(db, owner=owner)
        return [_classify_match(db, owner=owner, source_match=match, boundary=boundary)]
    if specific_sharecode:
        match = db.scalar(
            select(Match)
            .where(Match.source == "steam_history")
            .where(Match.external_match_id == specific_sharecode)
            .order_by(Match.id.desc())
        )
        if match is None:
            raise ValueError("specific_sharecode_not_found")
        _require_match_owner(match, owner)
        boundary = _build_discovery_boundary(db, owner=owner)
        return [
            _classify_match(
                db,
                owner=owner,
                source_match=match,
                boundary=boundary,
                specific_backfill=True,
            )
        ]

    history_rows = list(
        db.scalars(select(Match).where(Match.source == "steam_history").order_by(Match.id.desc())).all()
    )
    owner_history = [match for match in history_rows if _match_belongs_to_owner(match, owner)]
    boundary = _build_discovery_boundary(db, owner=owner, owner_history=owner_history)
    candidates = [
        _classify_match(db, owner=owner, source_match=match, boundary=boundary) for match in owner_history
    ]
    linked_demo_ids = {candidate.demo_match.id for candidate in candidates if candidate.demo_match is not None}
    standalone_demos = [
        match
        for match in db.scalars(select(Match).where(Match.source == "demo").order_by(Match.id.desc())).all()
        if _match_belongs_to_owner(match, owner)
    ]
    for match in standalone_demos:
        if match.id not in linked_demo_ids:
            candidates.append(_classify_match(db, owner=owner, source_match=match, boundary=boundary))
    return candidates


def _classify_match(
    db: Session,
    *,
    owner: _OwnerContext,
    source_match: Match,
    boundary: _DiscoveryBoundary | None = None,
    specific_backfill: bool = False,
) -> _Candidate:
    _require_match_owner(source_match, owner)
    boundary = boundary or _build_discovery_boundary(db, owner=owner)
    raw = _json_mapping(source_match.raw_json)
    sharecode = _optional_text(raw.get("share_code")) or (
        _optional_text(source_match.external_match_id) if source_match.source == "steam_history" else None
    )
    demo_match = source_match if source_match.source == "demo" else _linked_demo_match(db, owner, source_match)
    target = demo_match or source_match
    artifact = _latest_artifact(db, target.id)
    snapshots = [
        snapshot for snapshot in _match_snapshots(db, target.id) if _snapshot_belongs_to_owner(snapshot, owner)
    ]
    accepted_snapshots = {
        snapshot.source
        for snapshot in snapshots
        if artifact is not None
        and snapshot.source_parser_artifact_id == artifact.id
        and bool(snapshot.source_event_set_id)
    }

    if artifact is not None and artifact.status in ACCEPTED_PARSER_ARTIFACT_STATUSES:
        if METRIC_SNAPSHOT_SOURCES.issubset(accepted_snapshots):
            return _candidate(
                source_match,
                demo_match,
                sharecode,
                "already_complete",
                "already_completed_by_durable_lineage",
                artifact,
                snapshots,
            )
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "incomplete_resumable",
            "accepted_parser_lineage_missing_downstream_snapshots",
            artifact,
            snapshots,
        )
    if artifact is not None:
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "incomplete_resumable",
            "parser_artifact_not_accepted",
            artifact,
            snapshots,
        )
    parser_path = _parser_source_path(target) or _parser_source_path(source_match)
    if parser_path is not None:
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "incomplete_resumable",
            "retained_demo_without_parser_artifact",
            artifact,
            snapshots,
        )
    if source_match.source == "demo":
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "failed_terminal",
            "retained_demo_unavailable",
            artifact,
            snapshots,
        )

    if not sharecode:
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "invalid_identity",
            "invalid_external_match_identity",
            artifact,
            snapshots,
        )

    import_job = _source_import_job(db, source_match)
    if import_job is not None and import_job.status in IMPORT_JOB_ACTIVE_STATUSES:
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "incomplete_resumable",
            "active_import_job_resumable",
            artifact,
            snapshots,
        )

    raw_status = str(raw.get("status") or "").lower()
    raw_error = str(raw.get("error") or raw.get("error_message") or "").lower()
    owner_failure = raw.get("owner_coach_sync_failure") if isinstance(raw.get("owner_coach_sync_failure"), dict) else {}
    attempt_count, last_attempt_at, next_eligible_at = _retry_details(raw, import_job=import_job)

    if raw_status in {"ignored_old_history", "demo_download_skipped"}:
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "legacy_stale_pending",
            "superseded_by_accepted_match_time"
            if raw.get("ignored_reason")
            else "legacy_pending_without_resumable_lineage",
            artifact,
            snapshots,
        )
    if raw_status == "demo_unavailable":
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "unavailable_terminal",
            "terminal_demo_unavailable",
            artifact,
            snapshots,
            attempt_count=attempt_count,
            last_attempt_at=last_attempt_at,
            next_eligible_at=next_eligible_at,
        )
    if raw_status == "demo_download_error":
        phase = str(owner_failure.get("phase") or "acquisition").lower()
        retryable = bool(owner_failure.get("retryable", True))
        if attempt_count >= MAX_RETRYABLE_ATTEMPTS:
            internal = "unavailable_terminal" if phase == "acquisition" else "failed_terminal"
            return _candidate(
                source_match,
                demo_match,
                sharecode,
                internal,
                "retry_attempts_exhausted",
                artifact,
                snapshots,
                attempt_count=attempt_count,
                last_attempt_at=last_attempt_at,
                next_eligible_at=next_eligible_at,
            )
        if any(token in raw_error for token in ("expired", "not found", "404", "410")):
            return _candidate(
                source_match,
                demo_match,
                sharecode,
                "unavailable_terminal",
                "terminal_demo_unavailable",
                artifact,
                snapshots,
            )
        if any(token in raw_error for token in ("invalid share", "corrupt", "unsupported")):
            return _candidate(
                source_match,
                demo_match,
                sharecode,
                "failed_terminal",
                "terminal_demo_error",
                artifact,
                snapshots,
            )
        if not retryable:
            internal = "unavailable_terminal" if phase == "acquisition" else "failed_terminal"
            return _candidate(
                source_match,
                demo_match,
                sharecode,
                internal,
                str(owner_failure.get("reason_code") or "terminal_processing_failure"),
                artifact,
                snapshots,
            )
        eligible = next_eligible_at is None or _utcnow() >= next_eligible_at
        temporary_unavailable = phase == "acquisition" and _temporary_unavailable_reason(
            str(owner_failure.get("reason_code") or raw_error)
        )
        internal = "unavailable_retryable" if temporary_unavailable else "failed_retryable"
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            internal,
            "retryable_failure_eligible" if eligible else "retry_not_yet_eligible",
            artifact,
            snapshots,
            actionable=eligible,
            attempt_count=attempt_count,
            last_attempt_at=last_attempt_at,
            next_eligible_at=next_eligible_at,
        )

    if specific_backfill:
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "fresh_actionable",
            "specific_backfill_requested",
            artifact,
            snapshots,
        )
    fresh_reason = _fresh_reason(source_match, sharecode=sharecode, boundary=boundary)
    if fresh_reason is not None:
        return _candidate(
            source_match,
            demo_match,
            sharecode,
            "fresh_actionable",
            fresh_reason,
            artifact,
            snapshots,
        )
    return _candidate(
        source_match,
        demo_match,
        sharecode,
        "legacy_stale_pending",
        "legacy_pending_before_sync_boundary",
        artifact,
        snapshots,
    )


def _candidate(
    source_match: Match,
    demo_match: Match | None,
    sharecode: str | None,
    internal_classification: str,
    reason_code: str,
    artifact: DemoParseArtifact | None,
    snapshots: list[MetricSnapshot],
    *,
    actionable: bool | None = None,
    attempt_count: int = 0,
    last_attempt_at: datetime | None = None,
    next_eligible_at: datetime | None = None,
) -> _Candidate:
    if internal_classification not in INTERNAL_CLASSIFICATIONS:
        raise ValueError(f"unsupported_internal_classification:{internal_classification}")
    if actionable is None:
        actionable = internal_classification in {
            "fresh_actionable",
            "incomplete_resumable",
            "failed_retryable",
            "unavailable_retryable",
        }
    public_classification = {
        "fresh_actionable": "new",
        "incomplete_resumable": "incomplete",
        "already_complete": "already_complete",
        "legacy_stale_pending": "unavailable",
        "unavailable_retryable": "failed_retryable" if actionable else "unavailable",
        "unavailable_terminal": "unavailable",
        "failed_retryable": "failed_retryable",
        "failed_terminal": "failed_terminal",
        "cross_owner_denied": "failed_terminal",
        "invalid_identity": "failed_terminal",
    }[internal_classification]
    return _Candidate(
        source_match=source_match,
        demo_match=demo_match,
        sharecode=sharecode,
        classification=public_classification,
        reason_code=reason_code,
        artifact=artifact,
        snapshots=snapshots,
        internal_classification=internal_classification,
        actionable=actionable,
        attempt_count=attempt_count,
        last_attempt_at=last_attempt_at,
        next_eligible_at=next_eligible_at,
    )


def _build_discovery_boundary(
    db: Session,
    *,
    owner: _OwnerContext,
    owner_history: list[Match] | None = None,
) -> _DiscoveryBoundary:
    accepted_positions: dict[str, int] = {}
    jobs = db.scalars(
        select(ImportJob)
        .where(ImportJob.provider == "steam")
        .where(ImportJob.job_type == "match_history_sync")
        .where(ImportJob.steam_account_id == owner.steam_account.id)
        .where(ImportJob.status.in_(("completed", "succeeded")))
        .order_by(ImportJob.finished_at.asc(), ImportJob.created_at.asc(), ImportJob.id.asc())
    ).all()
    position = 0
    for job in jobs:
        payload = _json_mapping(job.result_json)
        inserted = _optional_int(payload.get("inserted")) or 0
        outcome = str(payload.get("sync_outcome") or "").upper()
        identities = payload.get("collected_share_codes")
        if inserted <= 0 or "NEW_MATCH" not in outcome or not isinstance(identities, list):
            continue
        for identity in identities:
            normalized = _optional_text(identity)
            if normalized is None:
                continue
            position += 1
            accepted_positions[normalized] = position

    if owner_history is None:
        history_rows = db.scalars(
            select(Match).where(Match.source == "steam_history").order_by(Match.id.desc())
        ).all()
        owner_history = [match for match in history_rows if _match_belongs_to_owner(match, owner)]
    latest_completed_position: int | None = None
    for match in owner_history:
        raw = _json_mapping(match.raw_json)
        identity = _optional_text(match.external_match_id) or _optional_text(raw.get("share_code"))
        identity_position = accepted_positions.get(identity or "")
        if identity_position is None or not _has_accepted_processing_lineage(db, owner=owner, source_match=match):
            continue
        latest_completed_position = max(latest_completed_position or 0, identity_position)

    source = "accepted_cursor_and_sync_lineage"
    if not accepted_positions and not owner.steam_account.last_share_code:
        source = "accepted_account_sync_metadata" if owner.steam_account.last_sync_at else "no_prior_accepted_boundary"
    return _DiscoveryBoundary(
        source=source,
        account_last_sync_at=owner.steam_account.last_sync_at,
        cursor=_optional_text(owner.steam_account.last_share_code),
        accepted_positions=accepted_positions,
        latest_completed_position=latest_completed_position,
    )


def _has_accepted_processing_lineage(db: Session, *, owner: _OwnerContext, source_match: Match) -> bool:
    demo_match = _linked_demo_match(db, owner, source_match)
    target = demo_match or source_match
    artifact = _latest_artifact(db, target.id)
    if artifact is None or artifact.status not in ACCEPTED_PARSER_ARTIFACT_STATUSES:
        return False
    accepted_sources = {
        snapshot.source
        for snapshot in _match_snapshots(db, target.id)
        if _snapshot_belongs_to_owner(snapshot, owner)
        and snapshot.source_parser_artifact_id == artifact.id
        and bool(snapshot.source_event_set_id)
    }
    return METRIC_SNAPSHOT_SOURCES.issubset(accepted_sources)


def _fresh_reason(source_match: Match, *, sharecode: str, boundary: _DiscoveryBoundary) -> str | None:
    position = boundary.accepted_positions.get(sharecode)
    if position is not None:
        return "fresh_after_sync_boundary"
    if boundary.cursor == sharecode:
        return "fresh_at_accepted_cursor"
    if boundary.account_last_sync_at is None:
        return "fresh_without_prior_sync_boundary"
    if source_match.created_at and source_match.created_at > boundary.account_last_sync_at:
        return "fresh_after_sync_boundary"
    return None


def _source_import_job(db: Session, source_match: Match) -> ImportJob | None:
    return db.get(ImportJob, source_match.import_job_id) if source_match.import_job_id is not None else None


def _retry_details(
    raw: dict[str, Any],
    *,
    import_job: ImportJob | None,
) -> tuple[int, datetime | None, datetime | None]:
    failure = raw.get("owner_coach_sync_failure") if isinstance(raw.get("owner_coach_sync_failure"), dict) else {}
    raw_status = str(raw.get("status") or "").lower()
    attempt_count = _optional_int(failure.get("attempt_count")) or (
        1 if failure or raw_status == "demo_download_error" else 0
    )
    last_attempt_at = _parse_datetime(failure.get("failed_at") or raw.get("failed_at"))
    if last_attempt_at is None and import_job is not None:
        last_attempt_at = import_job.finished_at or import_job.updated_at or import_job.started_at
    next_eligible_at = _parse_datetime(failure.get("next_eligible_at"))
    if next_eligible_at is None and last_attempt_at is not None and attempt_count:
        next_eligible_at = last_attempt_at + RETRY_COOLDOWN
    return attempt_count, last_attempt_at, next_eligible_at


def _temporary_unavailable_reason(value: str) -> bool:
    normalized = value.lower()
    return any(
        token in normalized
        for token in ("temporary", "timeout", "rate_limit", "steam_unavailable", "502", "503", "504")
    )


def _linked_demo_match(db: Session, owner: _OwnerContext, source_match: Match) -> Match | None:
    raw = _json_mapping(source_match.raw_json)
    raw_id = _optional_int(raw.get("imported_demo_match_id"))
    if raw_id is not None:
        match = db.get(Match, raw_id)
        if match is not None and match.source == "demo" and _match_belongs_to_owner(match, owner):
            return match
    if source_match.import_job_id is not None:
        match = db.scalar(
            select(Match)
            .where(Match.source == "demo")
            .where(Match.import_job_id == source_match.import_job_id)
            .where(or_(Match.user_id == owner.user.id, Match.user_id.is_(None)))
            .where(or_(Match.steam_account_id == owner.steam_account.id, Match.steam_account_id.is_(None)))
            .order_by(Match.id.desc())
        )
        if match is not None and _match_belongs_to_owner(match, owner):
            return match
    storage = raw.get("storage") if isinstance(raw.get("storage"), dict) else {}
    artifact = storage.get("artifact") if isinstance(storage.get("artifact"), dict) else {}
    retained_sha1 = _optional_text(artifact.get("sha1"))
    if retained_sha1:
        match = db.scalar(
            select(Match)
            .join(DemoParseArtifact, DemoParseArtifact.match_id == Match.id)
            .where(Match.source == "demo")
            .where(DemoParseArtifact.demo_sha1 == retained_sha1)
            .where(or_(Match.user_id == owner.user.id, Match.user_id.is_(None)))
            .where(or_(Match.steam_account_id == owner.steam_account.id, Match.steam_account_id.is_(None)))
            .order_by(Match.id.desc())
        )
        if match is not None and _match_belongs_to_owner(match, owner):
            return match
    return None


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


def _selected_candidate_ids(
    candidates: list[_Candidate],
    *,
    max_new_matches: int,
    max_new_acquisitions: int,
) -> set[int]:
    selected: set[int] = set()
    acquisitions = 0
    for candidate in candidates:
        if not _is_actionable(candidate):
            continue
        if len(selected) >= max_new_matches:
            break
        if _requires_acquisition(candidate):
            if acquisitions >= max_new_acquisitions:
                continue
            acquisitions += 1
        selected.add(candidate.source_match.id)
    return selected


def _is_actionable(candidate: _Candidate) -> bool:
    return candidate.actionable


def _requires_acquisition(candidate: _Candidate) -> bool:
    return candidate.demo_match is None and not candidate.source_match.demo_file


def _populate_discovery(
    result: dict[str, Any],
    *,
    candidates: list[_Candidate],
    selected_ids: set[int],
) -> None:
    classifications = {
        key: 0
        for key in ("new", "incomplete", "already_complete", "unavailable", "failed_retryable", "failed_terminal")
    }
    for candidate in candidates:
        classifications[candidate.classification] += 1
    internal_classifications = {key: 0 for key in INTERNAL_CLASSIFICATIONS}
    reason_codes: dict[str, int] = {}
    for candidate in candidates:
        internal_classifications[candidate.internal_classification] += 1
        reason_codes[candidate.reason_code] = reason_codes.get(candidate.reason_code, 0) + 1
    result["discovery"] = {
        "candidate_count": len(candidates),
        "selected_count": len(selected_ids),
        "selected_source_match_ids": sorted(selected_ids),
        "classifications": classifications,
        "internal_classifications": internal_classifications,
        "reason_codes": dict(sorted(reason_codes.items())),
        "legacy_stale_pending_count": internal_classifications["legacy_stale_pending"],
        "actionable_count": sum(candidate.actionable for candidate in candidates),
        "bounded": len([candidate for candidate in candidates if _is_actionable(candidate)]) > len(selected_ids),
        "new_demo_acquisition_cap": MAX_NEW_DEMO_ACQUISITIONS_PER_SYNC,
    }


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


def _existing_lineage(db: Session, owner: _OwnerContext, candidate: _Candidate) -> dict[str, Any]:
    target = candidate.demo_match or candidate.source_match
    import_job = db.get(ImportJob, target.import_job_id) if target.import_job_id is not None else None
    analysis_run, hypotheses, progress_evaluations = _existing_coach_entities(
        db,
        owner=owner,
        match_id=target.id,
    )
    event_set_ids = sorted(
        {snapshot.source_event_set_id for snapshot in candidate.snapshots if snapshot.source_event_set_id}
    )
    return {
        "import_job": _import_job_lineage(import_job),
        "match_id": target.id,
        "source_match_id": candidate.source_match.id,
        "retained_demo": _retained_demo_lineage(target, candidate.artifact),
        "parser_artifact": _artifact_lineage(candidate.artifact),
        "event_set_ids": event_set_ids,
        "metric_snapshot_ids": {
            "all": [snapshot.id for snapshot in candidate.snapshots],
            "created": [],
            "reused": [snapshot.id for snapshot in candidate.snapshots],
        },
        "analysis_run": {
            "id": analysis_run.id if analysis_run is not None else None,
            "created": None,
            "reused": analysis_run.id if analysis_run is not None else None,
        },
        "coach_hypothesis_ids": {
            "all": [item.id for item in hypotheses],
            "created": [],
            "reused": [item.id for item in hypotheses],
        },
        "mission_progress_evaluation_ids": {
            "all": [item.id for item in progress_evaluations],
            "created": [],
            "reused": [item.id for item in progress_evaluations],
        },
    }


def _existing_coach_entities(
    db: Session,
    *,
    owner: _OwnerContext,
    match_id: int,
) -> tuple[AnalysisRun | None, list[CoachHypothesis], list[MissionProgressEvaluation]]:
    analysis_run = None
    runs = db.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.user_id == owner.user.id)
        .where(AnalysisRun.owner_steam_id == owner.steam_account.steam_id)
        .where(AnalysisRun.source == ANALYSIS_RUN_SOURCE)
        .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
    ).all()
    for run in runs:
        source_payload = _json_mapping(run.source_payload_json)
        if source_payload.get("post_metrics_hook") != POST_METRICS_COACH_LOOP_HOOK:
            continue
        if _optional_int(source_payload.get("match_id")) == match_id:
            analysis_run = run
            break
    hypotheses = []
    if analysis_run is not None:
        hypotheses = list(
            db.scalars(
                select(CoachHypothesis)
                .where(CoachHypothesis.user_id == owner.user.id)
                .where(CoachHypothesis.owner_steam_id == owner.steam_account.steam_id)
                .where(CoachHypothesis.analysis_run_id == analysis_run.id)
                .order_by(CoachHypothesis.id.asc())
            ).all()
        )
    progress_evaluations = []
    evaluations = db.scalars(
        select(MissionProgressEvaluation)
        .where(MissionProgressEvaluation.user_id == owner.user.id)
        .where(MissionProgressEvaluation.owner_steam_id == owner.steam_account.steam_id)
        .order_by(MissionProgressEvaluation.id.asc())
    ).all()
    for evaluation in evaluations:
        payload = _json_mapping(evaluation.result_json)
        window = payload.get("evaluation_window_json")
        if not isinstance(window, dict) or window.get("source") != POST_METRICS_COACH_LOOP_SOURCE:
            continue
        if _int_list(window.get("match_ids")) == [match_id]:
            progress_evaluations.append(evaluation)
    return analysis_run, hypotheses, progress_evaluations


def _processing_lineage(
    *,
    source_match: Match,
    demo_match: Match,
    sharecode: str | None,
    import_job: ImportJob | None,
    artifact: DemoParseArtifact,
    processing: dict[str, Any],
) -> dict[str, Any]:
    progress_ids = _int_list(processing.get("mission_progress_evaluation_ids"))
    reused_progress = _int_list(
        (processing.get("idempotency") or {})
        .get("post_metrics_coach_loop", {})
        .get("reused_mission_progress_evaluation_ids")
    )
    return {
        "sharecode": sharecode,
        "import_job": _import_job_lineage(import_job),
        "match_id": demo_match.id,
        "source_match_id": source_match.id,
        "retained_demo": _retained_demo_lineage(demo_match, artifact),
        "parser_artifact": _artifact_lineage(artifact),
        "event_set_ids": [processing.get("source_event_set_id")] if processing.get("source_event_set_id") else [],
        "metric_snapshot_ids": processing.get("metric_snapshot_ids") or {"all": [], "created": [], "reused": []},
        "analysis_run": processing.get("analysis_run") or {"id": None, "created": None, "reused": None},
        "coach_hypothesis_ids": processing.get("coach_hypothesis_ids") or {"all": [], "created": [], "reused": []},
        "active_mission_ids": _int_list(processing.get("active_mission_ids")),
        "mission_progress_evaluation_ids": {
            "all": progress_ids,
            "created": [item for item in progress_ids if item not in reused_progress],
            "reused": reused_progress,
        },
    }


def _retained_demo_lineage(match: Match, artifact: DemoParseArtifact | None) -> dict[str, Any] | None:
    if not match.demo_file and artifact is None:
        return None
    raw = _json_mapping(match.raw_json)
    storage = raw.get("storage") if isinstance(raw.get("storage"), dict) else {}
    storage_artifact = storage.get("artifact") if isinstance(storage.get("artifact"), dict) else {}
    return {
        "path": match.demo_file or (artifact.source_demo_file if artifact is not None else None),
        "sha1": storage_artifact.get("sha1") or (artifact.demo_sha1 if artifact is not None else None),
        "size_bytes": storage_artifact.get("size_bytes"),
        "state": storage_artifact.get("state") or ("available" if match.demo_file else None),
    }


def _artifact_lineage(artifact: DemoParseArtifact | None) -> dict[str, Any] | None:
    if artifact is None:
        return None
    return {
        "id": artifact.id,
        "match_id": artifact.match_id,
        "status": artifact.status,
        "parser_name": artifact.parser_name,
        "parser_version": artifact.parser_version,
        "demo_sha1": artifact.demo_sha1,
    }


def _candidate_import_job(db: Session, candidate: _Candidate) -> ImportJob | None:
    target = candidate.demo_match or candidate.source_match
    job_id = target.import_job_id or candidate.source_match.import_job_id
    return db.get(ImportJob, job_id) if job_id is not None else None


def _import_job_lineage(job: ImportJob | None) -> dict[str, Any]:
    if job is None:
        return {"id": None, "status": None, "job_type": None, "logical_target_key": None}
    return {
        "id": job.id,
        "status": job.status,
        "job_type": job.job_type,
        "logical_target_key": job.logical_target_key,
    }


def _parser_source_path(match: Match) -> Path | None:
    values = [match.demo_file]
    artifact = _json_mapping(match.raw_json).get("parser_handoff")
    if isinstance(artifact, dict):
        values.append(artifact.get("path"))
    for value in values:
        if value and Path(str(value)).is_file():
            return Path(str(value))
    return None


def _link_source_to_demo_match(db: Session, *, source_match: Match, demo_match: Match) -> None:
    if source_match.id == demo_match.id:
        return
    raw = _json_mapping(source_match.raw_json)
    raw.update(
        {
            "status": "demo_parsed",
            "imported_demo_match_id": demo_match.id,
            "parser_artifact_match_id": demo_match.id,
            "next_step": None,
        }
    )
    source_match.raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str)
    db.commit()
    db.refresh(source_match)


def _refresh_coach_output(db: Session, *, owner: _OwnerContext, result: dict[str, Any]) -> None:
    scope = owner_player_metric_snapshot_scope(db, user_id=owner.user.id)
    active_context = active_mission_context_for_owner(
        db,
        user_id=owner.user.id,
        owner_steam_id=owner.steam_account.steam_id,
    )
    payload = build_ai_coach_payload(db, analysis_scope=scope)
    active_missions = list(active_context.get("active_missions") or [])
    result["coach"] = {
        "active_missions": active_missions,
        "latest_progress": [
            mission.get("latest_progress_evaluation")
            for mission in active_missions
            if mission.get("latest_progress_evaluation") is not None
        ],
        "recommendation_suppression": payload.get("mission_recommendation_suppression") or {},
    }
    for mission in active_missions:
        mission_id = _optional_int(mission.get("mission_id"))
        _mutation_add(result, "reused", "missions", mission_id)
        if mission_id is not None:
            for criteria in list_mission_criteria(db, user_id=owner.user.id, mission_id=mission_id):
                _mutation_add(result, "reused", "criteria", criteria.id)
        progress = mission.get("latest_progress_evaluation")
        if isinstance(progress, dict):
            _mutation_add(result, "reused", "progress_evaluations", _optional_int(progress.get("evaluation_id")))


def _safe_refresh_coach_output(db: Session, *, owner: _OwnerContext, result: dict[str, Any]) -> bool:
    try:
        _refresh_coach_output(db, owner=owner, result=result)
    except Exception as exc:  # pragma: no cover - defensive accepted-service boundary
        db.rollback()
        result["errors"].append(
            _failure(
                phase="coach",
                reason_code="coach_result_refresh_failed",
                safe_message="The owner cycle completed match work but could not refresh the final coach result.",
                retryable=True,
                exception_class=type(exc).__name__,
            )
        )
        logger.error(
            "owner_coach_sync coach refresh failed owner_user_id=%s exception_class=%s",
            owner.user.id,
            type(exc).__name__,
        )
        return False
    return True


def _account_processing_mutations(result: dict[str, Any], processing: dict[str, Any]) -> None:
    snapshots = processing.get("metric_snapshot_ids") or {}
    for item in _int_list(snapshots.get("created")):
        _mutation_add(result, "created", "metric_snapshots", item)
    for item in _int_list(snapshots.get("reused")):
        _mutation_add(result, "reused", "metric_snapshots", item)
    analysis = processing.get("analysis_run") or {}
    _mutation_add(result, "created", "analysis_runs", _optional_int(analysis.get("created")))
    _mutation_add(result, "reused", "analysis_runs", _optional_int(analysis.get("reused")))
    hypotheses = processing.get("coach_hypothesis_ids") or {}
    for action in ("created", "reused"):
        for item in _int_list(hypotheses.get(action)):
            _mutation_add(result, action, "hypotheses", item)
    progress_ids = _int_list(processing.get("mission_progress_evaluation_ids"))
    reused_progress = _int_list(
        (processing.get("idempotency") or {})
        .get("post_metrics_coach_loop", {})
        .get("reused_mission_progress_evaluation_ids")
    )
    for item in progress_ids:
        _mutation_add(result, "reused" if item in reused_progress else "created", "progress_evaluations", item)


def _account_existing_lineage(result: dict[str, Any], match_result: dict[str, Any]) -> None:
    lineage = match_result["lineage"]
    _mutation_add(result, "reused", "matches", _optional_int(lineage.get("source_match_id")))
    _mutation_add(result, "reused", "matches", _optional_int(lineage.get("match_id")))
    _mutation_add(result, "reused", "import_jobs", _optional_int((lineage.get("import_job") or {}).get("id")))
    _mutation_add(
        result,
        "reused",
        "parser_artifacts",
        _optional_int((lineage.get("parser_artifact") or {}).get("id")),
    )
    for item in _int_list((lineage.get("metric_snapshot_ids") or {}).get("reused")):
        _mutation_add(result, "reused", "metric_snapshots", item)
    _mutation_add(
        result,
        "reused",
        "analysis_runs",
        _optional_int((lineage.get("analysis_run") or {}).get("reused")),
    )
    for item in _int_list((lineage.get("coach_hypothesis_ids") or {}).get("reused")):
        _mutation_add(result, "reused", "hypotheses", item)
    for item in _int_list((lineage.get("mission_progress_evaluation_ids") or {}).get("reused")):
        _mutation_add(result, "reused", "progress_evaluations", item)


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


def _lineage_has_creation(processing: dict[str, Any], *, parser_created: bool) -> bool:
    return bool(
        parser_created
        or _int_list((processing.get("metric_snapshot_ids") or {}).get("created"))
        or (processing.get("analysis_run") or {}).get("created")
        or _int_list((processing.get("coach_hypothesis_ids") or {}).get("created"))
        or (
            set(_int_list(processing.get("mission_progress_evaluation_ids")))
            - set(
                _int_list(
                    (processing.get("idempotency") or {})
                    .get("post_metrics_coach_loop", {})
                    .get("reused_mission_progress_evaluation_ids")
                )
            )
        )
    )


def _latest_artifact(db: Session, match_id: int) -> DemoParseArtifact | None:
    return db.scalar(
        select(DemoParseArtifact)
        .where(DemoParseArtifact.match_id == match_id)
        .order_by(DemoParseArtifact.parsed_at.desc(), DemoParseArtifact.id.desc())
    )


def _match_snapshots(db: Session, match_id: int) -> list[MetricSnapshot]:
    return list(
        db.scalars(
            select(MetricSnapshot).where(MetricSnapshot.match_id == match_id).order_by(MetricSnapshot.id.asc())
        ).all()
    )


def _table_ids(db: Session, model: Any) -> set[int]:
    return {int(item) for item in db.scalars(select(model.id)).all()}


def _import_job_phase_error(job: ImportJob) -> _MatchPhaseError:
    payload = _json_mapping(job.result_json)
    acquisition = payload.get("acquisition") if isinstance(payload.get("acquisition"), dict) else {}
    outcome = str(acquisition.get("outcome") or payload.get("overall_outcome") or "").lower()
    if any(token in outcome for token in ("not_found", "unavailable", "expired")):
        if any(token in outcome for token in ("steam_unavailable", "temporarily_unavailable")):
            return _MatchPhaseError(
                phase="acquisition",
                reason_code="temporary_demo_unavailable",
                safe_message="Steam replay services are temporarily unavailable.",
                retryable=True,
            )
        return _MatchPhaseError(
            phase="acquisition",
            reason_code="demo_unavailable",
            safe_message="The requested replay is not available from Steam.",
            retryable=False,
        )
    if any(token in outcome for token in ("rate_limited", "timeout")):
        return _MatchPhaseError(
            phase="acquisition",
            reason_code="temporary_demo_timeout_or_rate_limit",
            safe_message="Steam replay acquisition is temporarily rate-limited or timed out.",
            retryable=True,
        )
    if "auth_missing" in outcome:
        return _MatchPhaseError(
            phase="acquisition",
            reason_code="steam_auth_missing",
            safe_message="Steam demo acquisition is not configured for this owner sync.",
            retryable=True,
        )
    return _MatchPhaseError(
        phase="acquisition",
        reason_code="demo_acquisition_failed",
        safe_message="Steam demo acquisition did not complete successfully.",
        retryable=True,
    )


def _persist_candidate_failure(
    db: Session,
    *,
    candidate: _Candidate,
    failure: _MatchPhaseError,
) -> _MatchPhaseError:
    source_match = db.get(Match, candidate.source_match.id)
    if source_match is None:
        return failure
    raw = _json_mapping(source_match.raw_json)
    previous = raw.get("owner_coach_sync_failure")
    previous = previous if isinstance(previous, dict) else {}
    previous_attempts = _optional_int(previous.get("attempt_count")) or 0
    attempt_count = previous_attempts + 1
    effective_failure = failure
    if failure.retryable and attempt_count >= MAX_RETRYABLE_ATTEMPTS:
        effective_failure = _MatchPhaseError(
            phase=failure.phase,
            reason_code="retry_attempts_exhausted",
            safe_message="The bounded retry policy is exhausted for this owner match.",
            retryable=False,
            exception_class=failure.exception_class,
        )
    failed_at = _utcnow()
    next_eligible_at = failed_at + RETRY_COOLDOWN if effective_failure.retryable else None
    terminal_unavailable = effective_failure.phase == "acquisition" and not effective_failure.retryable
    raw.update(
        {
            "status": "demo_unavailable" if terminal_unavailable else "demo_download_error",
            "error": effective_failure.reason_code,
            "owner_coach_sync_failure": {
                "phase": effective_failure.phase,
                "reason_code": effective_failure.reason_code,
                "retryable": effective_failure.retryable,
                "attempt_count": attempt_count,
                "failed_at": _iso(failed_at),
                "next_eligible_at": _iso(next_eligible_at) if next_eligible_at else None,
                "import_job_id": source_match.import_job_id,
            },
        }
    )
    source_match.raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str)
    db.commit()
    db.refresh(source_match)
    return effective_failure


def _acquire_owner_sync_lock(db: Session, *, owner_user_id: int) -> _OwnerSyncLock | None:
    now = _utcnow()
    key = _lock_key(owner_user_id)
    lock = _new_lock(key=key, now=now)
    db.add(AppSetting(key=key, value=lock.value))
    try:
        db.commit()
        return lock
    except IntegrityError:
        db.rollback()

    existing = db.get(AppSetting, key)
    if existing is None:
        return None
    existing_lock = _lock_from_value(key, existing.value)
    if existing_lock is not None and existing_lock.expires_at > now:
        return None
    stale_value = existing.value
    recovered = _new_lock(key=key, now=now, recovered_stale=True)
    changed = db.execute(
        update(AppSetting)
        .where(AppSetting.key == key)
        .where(AppSetting.value == stale_value)
        .values(value=recovered.value)
    )
    db.commit()
    return recovered if changed.rowcount == 1 else None


def _refresh_owner_sync_lock(db: Session, lock: _OwnerSyncLock) -> bool:
    now = _utcnow()
    refreshed = _new_lock(key=lock.key, now=now, token=lock.token, recovered_stale=lock.recovered_stale)
    changed = db.execute(
        update(AppSetting)
        .where(AppSetting.key == lock.key)
        .where(AppSetting.value == lock.value)
        .values(value=refreshed.value)
    )
    db.commit()
    if changed.rowcount != 1:
        return False
    lock.value = refreshed.value
    lock.expires_at = refreshed.expires_at
    return True


def _release_owner_sync_lock(db: Session, lock: _OwnerSyncLock) -> bool:
    changed = db.execute(delete(AppSetting).where(AppSetting.key == lock.key).where(AppSetting.value == lock.value))
    db.commit()
    return changed.rowcount == 1


def _read_active_lock(db: Session, *, owner_user_id: int) -> _OwnerSyncLock | None:
    setting = db.get(AppSetting, _lock_key(owner_user_id))
    if setting is None:
        return None
    lock = _lock_from_value(setting.key, setting.value)
    if lock is None or lock.expires_at <= _utcnow():
        return None
    return lock


def _new_lock(
    *,
    key: str,
    now: datetime,
    token: str | None = None,
    recovered_stale: bool = False,
) -> _OwnerSyncLock:
    token = token or secrets.token_urlsafe(18)
    expires_at = now + OWNER_COACH_SYNC_LOCK_TTL
    value = json.dumps(
        {
            "operation": OWNER_COACH_SYNC_OPERATION,
            "token": token,
            "acquired_at": _iso(now),
            "expires_at": _iso(expires_at),
        },
        sort_keys=True,
    )
    return _OwnerSyncLock(
        key=key,
        token=token,
        value=value,
        acquired_at=now,
        expires_at=expires_at,
        recovered_stale=recovered_stale,
    )


def _lock_from_value(key: str, value: str) -> _OwnerSyncLock | None:
    payload = _json_mapping(value)
    token = _optional_text(payload.get("token"))
    acquired_at = _parse_datetime(payload.get("acquired_at"))
    expires_at = _parse_datetime(payload.get("expires_at"))
    if not token or acquired_at is None or expires_at is None:
        return None
    return _OwnerSyncLock(
        key=key,
        token=token,
        value=value,
        acquired_at=acquired_at,
        expires_at=expires_at,
    )


def _public_lock(lock: _OwnerSyncLock, *, status: str) -> dict[str, Any]:
    return {
        "status": status,
        "operation": OWNER_COACH_SYNC_OPERATION,
        "owner_user_id": _optional_int(lock.key.rsplit(":", 1)[-1]),
        "acquired_at": _iso(lock.acquired_at),
        "expires_at": _iso(lock.expires_at),
        "recovered_stale": lock.recovered_stale,
        "released": False,
    }


def _lock_key(owner_user_id: int) -> str:
    return f"lock:{OWNER_COACH_SYNC_OPERATION}:{owner_user_id}"


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


def _sanitize_message(value: str) -> str:
    return _URL_RE.sub("[redacted-url]", str(value))[:500]


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


def _log_no_mutation_phases(owner_user_id: int) -> None:
    for phase in ("acquisition_complete", "parse_complete", "metrics_complete", "coach_complete"):
        _log_phase(phase, owner_user_id=owner_user_id, dry_run=True)


__all__ = [
    "DEFAULT_MAX_NEW_MATCHES",
    "MAX_NEW_MATCHES",
    "OWNER_COACH_SYNC_RESULT_SCHEMA_VERSION",
    "run_owner_coach_sync",
]
