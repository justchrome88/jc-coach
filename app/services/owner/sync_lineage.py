"""Owner-sync persisted lineage inspection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AnalysisRun,
    CoachHypothesis,
    DemoParseArtifact,
    ImportJob,
    Match,
    MetricSnapshot,
    MissionProgressEvaluation,
)
from app.services.coach.ai import (
    ANALYSIS_RUN_SOURCE,
    POST_METRICS_COACH_LOOP_HOOK,
    POST_METRICS_COACH_LOOP_SOURCE,
)
from app.services.owner.sync_support import (
    _int_list,
    _json_mapping,
    _optional_int,
)
from app.services.owner.sync_types import (
    _Candidate,
    _OwnerContext,
)


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

__all__ = (
)
