"""Owner-sync discovery and candidate classification."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    DemoParseArtifact,
    ImportJob,
    Match,
    MetricSnapshot,
    SteamAccount,
    User,
)
from app.services.ingestion.jobs import IMPORT_JOB_ACTIVE_STATUSES
from app.services.ingestion.steam import queue_match_history_sync, sync_match_history_job
from app.services.owner.match_processing import (
    ACCEPTED_PARSER_ARTIFACT_STATUSES,
)
from app.services.owner.sync_lineage import (
    _latest_artifact,
    _match_snapshots,
    _parser_source_path,
    _table_ids,
)
from app.services.owner.sync_support import (
    _account_table_delta,
    _failure,
    _json_mapping,
    _match_belongs_to_owner,
    _mutation_add,
    _optional_int,
    _optional_text,
    _parse_datetime,
    _require_match_owner,
    _snapshot_belongs_to_owner,
    _utcnow,
)
from app.services.owner.sync_types import (
    INTERNAL_CLASSIFICATIONS,
    MAX_NEW_DEMO_ACQUISITIONS_PER_SYNC,
    MAX_RETRYABLE_ATTEMPTS,
    METRIC_SNAPSHOT_SOURCES,
    RETRY_COOLDOWN,
    _Candidate,
    _DiscoveryBoundary,
    _OwnerContext,
)


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

__all__ = (
)
