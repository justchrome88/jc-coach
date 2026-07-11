"""Owner-sync candidate execution and persistence orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    DemoParseArtifact,
    ImportJob,
    Match,
)
from app.services.coach.ai import (
    build_ai_coach_payload,
)
from app.services.ingestion.demo_import import import_demo_file
from app.services.ingestion.jobs import IMPORT_JOB_COMPLETED
from app.services.ingestion.orchestration import run_demo_import_orchestration
from app.services.metrics.snapshots import owner_player_metric_snapshot_scope
from app.services.missions.presentation import active_mission_context_for_owner
from app.services.missions.repository import list_mission_criteria
from app.services.owner.match_processing import (
    ACCEPTED_PARSER_ARTIFACT_STATUSES,
    process_owner_match_after_parser_artifact,
)
from app.services.owner.sync_lineage import (
    _candidate_import_job,
    _import_job_lineage,
    _latest_artifact,
    _lineage_has_creation,
    _parser_source_path,
    _processing_lineage,
    _table_ids,
)
from app.services.owner.sync_serialization import (
    _candidate_result,
    _match_import_target,
)
from app.services.owner.sync_support import (
    _account_table_delta,
    _failure,
    _int_list,
    _iso,
    _json_mapping,
    _mutation_add,
    _optional_int,
    _require_match_owner,
    _utcnow,
)
from app.services.owner.sync_types import (
    MAX_RETRYABLE_ATTEMPTS,
    OWNER_COACH_SYNC_OPERATION,
    RETRY_COOLDOWN,
    _Candidate,
    _MatchPhaseError,
    _OwnerContext,
    logger,
)


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

__all__ = (
)
