from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.db.models import (
    AnalysisRun,
    CoachHypothesis,
    CoachMission,
    DemoDamageEvent,
    DemoDuel,
    DemoGrenadeEvent,
    DemoParseArtifact,
    DemoPlayerRound,
    DemoRound,
    DemoWeaponStat,
    ImportJob,
    Match,
    MetricSnapshot,
    MissionCriteria,
    MissionProgressEvaluation,
    SteamAccount,
)
from app.db.session import SessionLocal
from app.services.ingestion.demo_acquisition import DEMO_ALREADY_AVAILABLE
from app.services.ingestion.demo_import import import_demo_file
from app.services.ingestion.jobs import IMPORT_JOB_COMPLETED, import_job_result
from app.services.ingestion.orchestration import CANONICAL_IMPORT_JOB_TYPE, run_demo_import_orchestration
from app.services.ingestion.steam import (
    decode_match_share_code,
    mark_steam_history_demo_download_status,
    queue_match_history_sync,
    sync_match_history_job,
)
from app.services.missions.lifecycle import cancel_coach_mission
from app.services.owner.match_processing import process_owner_match_after_parser_artifact
from app.services.parsing.demo_parser import DemoParseError

BASE_DIR = Path(__file__).resolve().parents[1]
PM_DIR = Path("/opt/jc-coach-pm")
DB_PATH = BASE_DIR / "data" / "cs2_coach.db"
BACKUP_DIR = BASE_DIR / "data" / "backups"
REPORT_PATH = PM_DIR / "reports" / "M09_clean_test_data_and_backfill_real_steam_matches_report.md"
ARTIFACT_PATH = PM_DIR / "reports" / "artifacts" / "M09_clean_test_data_and_backfill_real_steam_matches_output.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="M09 cleanup and real Steam backfill.")
    parser.add_argument("--max-targets", type=int, default=0, help="Optional cap for debugging; 0 means all.")
    args = parser.parse_args()

    started_at = _now()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    pre_sha = _sha256(DB_PATH)
    backup_path = BACKUP_DIR / f"M09_clean_test_data_pre_mutation_{started_at.strftime('%Y%m%dT%H%M%SZ')}.db"
    shutil.copy2(DB_PATH, backup_path)
    backup_sha = _sha256(backup_path)
    if backup_sha != pre_sha:
        raise RuntimeError("Backup SHA does not match pre-cleanup DB SHA.")

    with SessionLocal() as db:
        pre_counts = _normal_counts(db)
        cleanup = _cleanup_controlled_rows(db)
        post_cleanup_sha = _sha256(DB_PATH)
        targets = _discover_real_targets(db)
        if args.max_targets > 0:
            targets = targets[: args.max_targets]
        backfill = _backfill_targets(db, targets)
        final_counts = _normal_counts(db)
        final_state = _final_state(db)
        artifact = {
            "task": "M09_clean_test_data_and_backfill_real_steam_matches",
            "result": "PASS_WITH_WARNINGS" if backfill["skipped_targets"] else "PASS",
            "started_at": started_at.isoformat(),
            "finished_at": _now().isoformat(),
            "db": {
                "path": str(DB_PATH),
                "pre_cleanup_sha256": pre_sha,
                "backup_path": str(backup_path),
                "backup_sha256": backup_sha,
                "post_cleanup_pre_backfill_sha256": post_cleanup_sha,
                "final_post_backfill_sha256": _sha256(DB_PATH),
            },
            "pre_counts": pre_counts,
            "cleanup": cleanup,
            "real_targets_discovered": targets,
            "backfill": backfill,
            "final_counts": final_counts,
            "final_match_list_state": final_state,
        }

    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(_report_markdown(artifact), encoding="utf-8")


def _cleanup_controlled_rows(db: Session) -> dict[str, Any]:
    controlled_match_ids = [
        row[0]
        for row in db.execute(
            text(
                """
                select id from matches
                where source = 'controlled_fixture'
                   or demo_file like 'fixture://%'
                   or external_match_id like '%fixture%'
                order by id
                """
            )
        ).all()
    ]
    controlled_job_ids = [
        row[0]
        for row in db.execute(
            text(
                """
                select id from import_jobs
                where provider = 'controlled_fixture'
                   or job_type like '%fixture%'
                   or job_type like '%m06%'
                   or logical_target_key like '%fixture%'
                order by id
                """
            )
        ).all()
    ]
    controlled_artifact_ids = [
        row[0]
        for row in db.execute(
            text(
                """
                select id from demo_parse_artifacts
                where parser_name like '%fixture%'
                   or source_demo_file like 'fixture://%'
                   or match_id in (select value from json_each(:match_ids))
                order by id
                """
            ),
            {"match_ids": json.dumps(controlled_match_ids)},
        ).all()
    ]
    controlled_snapshot_ids = [
        row[0]
        for row in db.execute(
            text(
                """
                select id from metric_snapshots
                where match_id in (select value from json_each(:match_ids))
                   or source_parser_artifact_id in (select value from json_each(:artifact_ids))
                order by id
                """
            ),
            {"match_ids": json.dumps(controlled_match_ids), "artifact_ids": json.dumps(controlled_artifact_ids)},
        ).all()
    ]
    affected_analysis_ids = _analysis_ids_for_snapshots(db, controlled_snapshot_ids)
    affected_hypothesis_ids = _hypothesis_ids_for_analysis_runs(db, affected_analysis_ids)
    fixture_mission_ids = _mission_ids_for_hypotheses_or_fixture_payload(db, affected_hypothesis_ids)

    active_mission_actions = []
    for mission in db.scalars(select(CoachMission).where(CoachMission.status == "active").order_by(CoachMission.id)):
        controlled_named = "controlled" in mission.title.lower() or "m04" in mission.title.lower()
        fixture_backed = mission.id in fixture_mission_ids
        if controlled_named or fixture_backed:
            before = {"id": mission.id, "status": mission.status, "title": mission.title}
            cancel_coach_mission(db, user_id=int(mission.user_id), mission_id=mission.id, ended_at=_now())
            db.commit()
            db.refresh(mission)
            active_mission_actions.append(
                {
                    "mission_id": mission.id,
                    "title": mission.title,
                    "before": before,
                    "after": {
                        "status": mission.status,
                        "ended_at": mission.ended_at.isoformat() if mission.ended_at else None,
                    },
                    "reason": "controlled utility follow-through mission should not evaluate future real matches",
                }
            )

    deleted = {
        "mission_progress_evaluations": _delete_by_ids(
            db,
            MissionProgressEvaluation,
            MissionProgressEvaluation.mission_id,
            fixture_mission_ids,
        ),
        "mission_criteria": _delete_by_ids(db, MissionCriteria, MissionCriteria.mission_id, fixture_mission_ids),
        "coach_missions": _delete_by_ids(db, CoachMission, CoachMission.id, fixture_mission_ids),
        "coach_hypotheses": _delete_by_ids(db, CoachHypothesis, CoachHypothesis.id, affected_hypothesis_ids),
        "analysis_runs": _delete_by_ids(db, AnalysisRun, AnalysisRun.id, affected_analysis_ids),
        "metric_snapshots": _delete_by_ids(db, MetricSnapshot, MetricSnapshot.id, controlled_snapshot_ids),
        "demo_grenade_events": _delete_by_ids(db, DemoGrenadeEvent, DemoGrenadeEvent.match_id, controlled_match_ids),
        "demo_duels": _delete_by_ids(db, DemoDuel, DemoDuel.match_id, controlled_match_ids),
        "demo_damage_events": _delete_by_ids(db, DemoDamageEvent, DemoDamageEvent.match_id, controlled_match_ids),
        "demo_weapon_stats": _delete_by_ids(db, DemoWeaponStat, DemoWeaponStat.match_id, controlled_match_ids),
        "demo_player_rounds": _delete_by_ids(db, DemoPlayerRound, DemoPlayerRound.match_id, controlled_match_ids),
        "demo_rounds": _delete_by_ids(db, DemoRound, DemoRound.match_id, controlled_match_ids),
        "demo_parse_artifacts": _delete_by_ids(db, DemoParseArtifact, DemoParseArtifact.id, controlled_artifact_ids),
        "matches": _delete_by_ids(db, Match, Match.id, controlled_match_ids),
        "import_jobs": _delete_by_ids(db, ImportJob, ImportJob.id, controlled_job_ids),
    }
    db.commit()
    return {
        "strategy": "delete isolated controlled_fixture rows; cancel controlled active mission before deletion checks",
        "identified": {
            "match_ids": controlled_match_ids,
            "import_job_ids": controlled_job_ids,
            "parser_artifact_ids": controlled_artifact_ids,
            "metric_snapshot_ids": controlled_snapshot_ids,
            "analysis_run_ids": affected_analysis_ids,
            "coach_hypothesis_ids": affected_hypothesis_ids,
            "fixture_mission_ids": fixture_mission_ids,
        },
        "active_mission_actions": active_mission_actions,
        "deleted_rows": deleted,
        "remaining_controlled_rows": _remaining_controlled_rows(db),
    }


def _discover_real_targets(db: Session) -> list[dict[str, Any]]:
    sync_results = []
    for account in db.scalars(select(SteamAccount).where(SteamAccount.user_id == 1).where(SteamAccount.id == 1)):
        if account.match_auth_code and account.last_share_code:
            try:
                job = queue_match_history_sync(db, account.id)
                result = sync_match_history_job(db, job.id)
                sync_results.append(
                    {
                        "job_id": job.id,
                        "status": result.get("status"),
                        "sync_outcome": (result.get("result") or {}).get("sync_outcome"),
                        "collected": (result.get("result") or {}).get("collected"),
                        "inserted": (result.get("result") or {}).get("inserted"),
                        "duplicates": (result.get("result") or {}).get("duplicates"),
                    }
                )
            except Exception as exc:
                sync_results.append({"status": "failed", "reason": _safe_reason(exc)})
    mark_result = mark_steam_history_demo_download_status(db)
    targets = []
    for match in db.scalars(select(Match).where(Match.source == "steam_history").order_by(Match.id.desc())):
        share_code = str(match.external_match_id or "").strip()
        if not share_code:
            continue
        try:
            decode_match_share_code(share_code)
            valid = True
            invalid_reason = None
        except ValueError as exc:
            valid = False
            invalid_reason = str(exc)
        demo_match = _demo_match_for_steam_history(db, match)
        targets.append(
            {
                "steam_history_match_id": match.id,
                "share_code": share_code,
                "valid_share_code": valid,
                "invalid_reason": invalid_reason,
                "has_retained_demo": bool(match.demo_file),
                "demo_match_id": demo_match.id if demo_match is not None else None,
                "sync_discovery": sync_results,
                "demo_download_mark": mark_result,
            }
        )
    return targets


def _backfill_targets(db: Session, targets: list[dict[str, Any]]) -> dict[str, Any]:
    imported_targets = []
    skipped_targets = []
    processed_match_ids: list[int] = []
    parser_artifact_ids: list[int] = []
    orchestrator_summaries = []
    metric_snapshot_ids: list[int] = []

    for target in targets:
        share_code = target["share_code"]
        if not target["valid_share_code"]:
            skipped_targets.append({**target, "reason": target["invalid_reason"] or "invalid_share_code"})
            continue

        job = _completed_canonical_job_for_share_code(db, share_code)
        if job is None:
            try:
                job = run_demo_import_orchestration(
                    db,
                    provider="steam",
                    payload={"share_code": share_code},
                    user_id=1,
                    steam_account_id=1,
                    logical_target_key=f"steam:{CANONICAL_IMPORT_JOB_TYPE}:{share_code}",
                )
            except Exception as exc:
                skipped_targets.append({**target, "reason": _safe_reason(exc), "stage": "canonical_import"})
                continue

        result = import_job_result(job)
        cleaned_temporary_sources = _cleanup_unreferenced_temporary_sources(db, result)
        acquisition = result.get("acquisition") if isinstance(result.get("acquisition"), dict) else {}
        if job.status != IMPORT_JOB_COMPLETED:
            skipped_targets.append(
                {
                    **target,
                    "job_id": job.id,
                    "job_status": job.status,
                    "reason": _sanitized_job_error(job, result),
                    "stage": "canonical_import",
                }
            )
            continue

        parser_path = _parser_handoff_path(result)
        if not parser_path:
            skipped_targets.append({**target, "job_id": job.id, "reason": "parser_handoff_path_missing"})
            continue
        path = Path(parser_path)
        if not path.is_file():
            skipped_targets.append({**target, "job_id": job.id, "reason": "retained_demo_file_missing"})
            continue

        demo_match = _demo_match_for_path_or_job(db, path, job.id)
        parse_result = None
        if demo_match is None:
            try:
                parse_result = import_demo_file(
                    db,
                    path,
                    original_filename=f"{share_code}.dem",
                    player_identifier=None,
                    acquisition_metadata={
                        "import_job_id": job.id,
                        "share_code": share_code,
                        "user_id": 1,
                        "steam_account_id": 1,
                    },
                    evaluate_recommendations=False,
                )
                demo_match = db.get(Match, int(parse_result["match_id"]))
            except DemoParseError as exc:
                skipped_targets.append(
                    {**target, "job_id": job.id, "reason": _safe_reason(exc), "stage": "parser"}
                )
                continue
            except Exception as exc:
                skipped_targets.append(
                    {**target, "job_id": job.id, "reason": _safe_reason(exc), "stage": "parser"}
                )
                continue

        if demo_match is None:
            skipped_targets.append({**target, "job_id": job.id, "reason": "demo_match_missing_after_parse"})
            continue
        _attach_owner_and_job(db, demo_match, job.id)
        artifact = _artifact_for_match(db, demo_match.id)
        if artifact is None:
            skipped_targets.append(
                {**target, "job_id": job.id, "demo_match_id": demo_match.id, "reason": "parser_artifact_missing"}
            )
            continue
        try:
            summary = process_owner_match_after_parser_artifact(
                db,
                user_id=1,
                match_id=demo_match.id,
                parser_artifact_id=artifact.id,
                source_metadata={"task": "M09", "share_code": share_code, "import_job_id": job.id},
            )
            db.commit()
        except Exception as exc:
            skipped_targets.append(
                {
                    **target,
                    "job_id": job.id,
                    "demo_match_id": demo_match.id,
                    "parser_artifact_id": artifact.id,
                    "reason": _safe_reason(exc),
                    "stage": "orchestrator",
                }
            )
            continue

        ids = summary.get("metric_snapshot_ids") if isinstance(summary.get("metric_snapshot_ids"), dict) else {}
        all_snapshot_ids = [int(value) for value in ids.get("all") or []]
        metric_snapshot_ids.extend(all_snapshot_ids)
        processed_match_ids.append(demo_match.id)
        parser_artifact_ids.append(artifact.id)
        imported_targets.append(
            {
                **target,
                "job_id": job.id,
                "job_status": job.status,
                "acquisition_outcome": acquisition.get("outcome"),
                "reused_existing_demo": acquisition.get("outcome") == DEMO_ALREADY_AVAILABLE,
                "demo_match_id": demo_match.id,
                "parser_artifact_id": artifact.id,
                "cleaned_temporary_sources": cleaned_temporary_sources,
                "parse_result": _compact_parse_result(parse_result),
                "metric_snapshot_ids": all_snapshot_ids,
                "orchestrator_status": summary.get("status"),
                "analysis_run": summary.get("analysis_run"),
                "coach_hypothesis_ids": summary.get("coach_hypothesis_ids"),
                "mission_progress_evaluation_ids": summary.get("mission_progress_evaluation_ids"),
            }
        )
        orchestrator_summaries.append(_compact_orchestrator_summary(summary))

    return {
        "imported_targets": imported_targets,
        "skipped_targets": skipped_targets,
        "processed_match_ids": sorted(set(processed_match_ids)),
        "parser_artifact_ids": sorted(set(parser_artifact_ids)),
        "metric_snapshot_id_ranges": _id_ranges(metric_snapshot_ids),
        "orchestrator_summaries": orchestrator_summaries,
        "active_mission_evaluation_status": _active_mission_status(db),
    }


def _analysis_ids_for_snapshots(db: Session, snapshot_ids: list[int]) -> list[int]:
    if not snapshot_ids:
        return []
    ids: list[int] = []
    for run in db.scalars(select(AnalysisRun)):
        selected = _json_loads(run.selected_metric_snapshot_ids_json, [])
        if any(int(snapshot_id) in selected for snapshot_id in snapshot_ids):
            ids.append(run.id)
    return sorted(set(ids))


def _hypothesis_ids_for_analysis_runs(db: Session, analysis_ids: list[int]) -> list[int]:
    if not analysis_ids:
        return []
    return [
        row[0]
        for row in db.execute(select(CoachHypothesis.id).where(CoachHypothesis.analysis_run_id.in_(analysis_ids))).all()
    ]


def _mission_ids_for_hypotheses_or_fixture_payload(db: Session, hypothesis_ids: list[int]) -> list[int]:
    ids = []
    stmt = select(CoachMission)
    if hypothesis_ids:
        stmt = stmt.where(
            (CoachMission.hypothesis_id.in_(hypothesis_ids)) | (CoachMission.source_payload_json.like("%fixture%"))
        )
    else:
        stmt = stmt.where(CoachMission.source_payload_json.like("%fixture%"))
    for mission in db.scalars(stmt):
        ids.append(mission.id)
    return sorted(set(ids))


def _delete_by_ids(db: Session, model: Any, column: Any, ids: list[int]) -> int:
    if not ids:
        return 0
    result = db.execute(delete(model).where(column.in_(ids)))
    return int(result.rowcount or 0)


def _remaining_controlled_rows(db: Session) -> dict[str, int]:
    return {
        "matches": int(
            db.scalar(
                select(func.count())
                .select_from(Match)
                .where(
                    (Match.source == "controlled_fixture")
                    | (Match.demo_file.like("fixture://%"))
                    | (Match.external_match_id.like("%fixture%"))
                )
            )
            or 0
        ),
        "import_jobs": int(
            db.scalar(
                select(func.count())
                .select_from(ImportJob)
                .where(
                    (ImportJob.provider == "controlled_fixture")
                    | (ImportJob.job_type.like("%fixture%"))
                    | (ImportJob.job_type.like("%m06%"))
                    | (ImportJob.logical_target_key.like("%fixture%"))
                )
            )
            or 0
        ),
        "demo_parse_artifacts": int(
            db.scalar(
                select(func.count())
                .select_from(DemoParseArtifact)
                .where(
                    (DemoParseArtifact.parser_name.like("%fixture%"))
                    | (DemoParseArtifact.source_demo_file.like("fixture://%"))
                )
            )
            or 0
        ),
    }


def _completed_canonical_job_for_share_code(db: Session, share_code: str) -> ImportJob | None:
    target_key = f"steam:{CANONICAL_IMPORT_JOB_TYPE}:{share_code}"
    return db.scalar(
        select(ImportJob)
        .where(ImportJob.provider == "steam")
        .where(ImportJob.job_type == CANONICAL_IMPORT_JOB_TYPE)
        .where(ImportJob.logical_target_key == target_key)
        .where(ImportJob.status == IMPORT_JOB_COMPLETED)
        .order_by(ImportJob.id.asc())
    )


def _parser_handoff_path(result: dict[str, Any]) -> str | None:
    parser_handoff = result.get("parser_handoff") if isinstance(result.get("parser_handoff"), dict) else {}
    path = parser_handoff.get("path")
    if path:
        return str(path)
    storage = result.get("storage") if isinstance(result.get("storage"), dict) else {}
    artifact = storage.get("artifact") if isinstance(storage.get("artifact"), dict) else {}
    path = artifact.get("parser_handoff_path") or artifact.get("path")
    return str(path) if path else None


def _cleanup_unreferenced_temporary_sources(db: Session, result: dict[str, Any]) -> list[str]:
    paths = []
    acquisition = result.get("acquisition") if isinstance(result.get("acquisition"), dict) else {}
    acquisition_result = acquisition.get("result") if isinstance(acquisition.get("result"), dict) else {}
    source_path = acquisition_result.get("source_path")
    if source_path:
        paths.append(str(source_path))
    cleaned = []
    for path_text in sorted(set(paths)):
        path = Path(path_text)
        if not _is_steam_temp_source(path):
            continue
        if _path_referenced_by_retained_data(db, path):
            continue
        if path.exists():
            shutil.rmtree(path.parent, ignore_errors=True)
            cleaned.append(str(path.parent))
    return cleaned


def _is_steam_temp_source(path: Path) -> bool:
    try:
        resolved = path.resolve()
        temp_root = (BASE_DIR / "data" / "tmp").resolve()
    except OSError:
        return False
    return temp_root in resolved.parents and resolved.parent.name.startswith("jc-steam-demo-")


def _path_referenced_by_retained_data(db: Session, path: Path) -> bool:
    text_path = str(path.resolve())
    match_refs = int(
        db.scalar(select(func.count()).select_from(Match).where(Match.demo_file == text_path)) or 0
    )
    artifact_refs = int(
        db.scalar(
            select(func.count()).select_from(DemoParseArtifact).where(DemoParseArtifact.source_demo_file == text_path)
        )
        or 0
    )
    return bool(match_refs or artifact_refs)


def _demo_match_for_steam_history(db: Session, history_match: Match) -> Match | None:
    if not history_match.demo_file:
        return None
    return _demo_match_for_path_or_job(db, Path(history_match.demo_file), history_match.import_job_id)


def _demo_match_for_path_or_job(db: Session, path: Path, import_job_id: int | None) -> Match | None:
    resolved = str(path.resolve())
    stmt = select(Match).where(Match.source == "demo").where(Match.demo_file == resolved).order_by(Match.id.desc())
    match = db.scalar(stmt)
    if match is not None:
        return match
    if import_job_id is not None:
        return db.scalar(
            select(Match)
            .where(Match.source == "demo")
            .where(Match.import_job_id == import_job_id)
            .order_by(Match.id.desc())
        )
    return None


def _attach_owner_and_job(db: Session, match: Match, import_job_id: int) -> None:
    changed = False
    if match.user_id != 1:
        match.user_id = 1
        changed = True
    if match.steam_account_id != 1:
        match.steam_account_id = 1
        changed = True
    if match.import_job_id is None:
        match.import_job_id = import_job_id
        changed = True
    if changed:
        db.commit()
        db.refresh(match)


def _artifact_for_match(db: Session, match_id: int) -> DemoParseArtifact | None:
    return db.scalar(
        select(DemoParseArtifact)
        .where(DemoParseArtifact.match_id == match_id)
        .order_by(DemoParseArtifact.id.desc())
    )


def _sanitized_job_error(job: ImportJob, result: dict[str, Any]) -> str:
    error = result.get("error") if isinstance(result.get("error"), dict) else {}
    message = str(error.get("message") or job.error_message or job.status)
    return _sanitize_text(message)


def _compact_parse_result(parse_result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not parse_result:
        return None
    return {
        "imported": parse_result.get("imported"),
        "skipped_duplicates": parse_result.get("skipped_duplicates"),
        "match_id": parse_result.get("match_id"),
        "parser_success": parse_result.get("parser_success"),
        "stored_path": parse_result.get("stored_path"),
        "event_counts": parse_result.get("event_counts"),
    }


def _compact_orchestrator_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": summary.get("status"),
        "match_id": summary.get("match_id"),
        "parser_artifact": summary.get("parser_artifact"),
        "normalized_event_count": summary.get("normalized_event_count"),
        "metric_snapshot_ids": summary.get("metric_snapshot_ids"),
        "analysis_run": summary.get("analysis_run"),
        "coach_hypothesis_ids": summary.get("coach_hypothesis_ids"),
        "active_mission_ids": summary.get("active_mission_ids"),
        "mission_progress_evaluation_ids": summary.get("mission_progress_evaluation_ids"),
        "mission_progress_statuses": summary.get("mission_progress_statuses"),
        "idempotency": summary.get("idempotency"),
        "caveats": summary.get("caveats"),
    }


def _active_mission_status(db: Session) -> list[dict[str, Any]]:
    rows = []
    for mission in db.scalars(select(CoachMission).order_by(CoachMission.id)):
        evaluations = list(
            db.scalars(
                select(MissionProgressEvaluation)
                .where(MissionProgressEvaluation.mission_id == mission.id)
                .order_by(MissionProgressEvaluation.id)
            )
        )
        rows.append(
            {
                "mission_id": mission.id,
                "status": mission.status,
                "title": mission.title,
                "evaluation_ids": [evaluation.id for evaluation in evaluations],
                "evaluation_statuses": [evaluation.status for evaluation in evaluations],
            }
        )
    return rows


def _normal_counts(db: Session) -> dict[str, Any]:
    return {
        "matches_by_source": _group_count(db, "matches", "source"),
        "import_jobs_by_provider_type_status": [
            {"provider": row[0], "job_type": row[1], "status": row[2], "count": row[3]}
            for row in db.execute(
                text(
                    """
                    select provider, job_type, status, count(*)
                    from import_jobs
                    group by provider, job_type, status
                    order by provider, job_type, status
                    """
                )
            ).all()
        ],
        "parser_artifacts_by_parser_status": [
            {"parser_name": row[0], "status": row[1], "count": row[2]}
            for row in db.execute(
                text(
                    """
                    select parser_name, status, count(*)
                    from demo_parse_artifacts
                    group by parser_name, status
                    order by parser_name, status
                    """
                )
            ).all()
        ],
        "metric_snapshots_by_source": _group_count(db, "metric_snapshots", "source"),
        "missions_by_status": _group_count(db, "coach_missions", "status"),
    }


def _group_count(db: Session, table: str, column: str) -> list[dict[str, Any]]:
    return [
        {column: row[0], "count": row[1]}
        for row in db.execute(text(f"select {column}, count(*) from {table} group by {column} order by {column}")).all()
    ]


def _final_state(db: Session) -> dict[str, Any]:
    real_demo_rows = [
        {
            "id": row[0],
            "played_at": row[1],
            "map_name": row[2],
            "rounds_for": row[3],
            "rounds_against": row[4],
            "kills": row[5],
            "deaths": row[6],
            "kd": row[7],
            "adr": row[8],
            "kast": row[9],
            "utility_damage": row[10],
            "flash_assists": row[11],
            "enemies_flashed": row[12],
        }
        for row in db.execute(
            text(
                """
                select id, played_at, map_name, rounds_for, rounds_against, kills, deaths, kd, adr, kast,
                       utility_damage, flash_assists, enemies_flashed
                from matches
                where source = 'demo'
                order by played_at desc, id desc
                """
            )
        ).all()
    ]
    return {
        "normal_match_count": int(db.scalar(select(func.count()).select_from(Match)) or 0),
        "controlled_fixture_match_count": _remaining_controlled_rows(db)["matches"],
        "real_demo_match_count": len(real_demo_rows),
        "steam_history_match_count": int(
            db.scalar(select(func.count()).select_from(Match).where(Match.source == "steam_history")) or 0
        ),
        "real_demo_rows_with_metrics": real_demo_rows,
    }


def _id_ranges(ids: list[int]) -> list[dict[str, int]]:
    values = sorted(set(int(value) for value in ids))
    if not values:
        return []
    ranges = []
    start = prev = values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
            continue
        ranges.append({"start": start, "end": prev})
        start = prev = value
    ranges.append({"start": start, "end": prev})
    return ranges


def _json_loads(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback


def _safe_reason(exc: Exception) -> str:
    return _sanitize_text(str(exc) or type(exc).__name__)


def _sanitize_text(value: str) -> str:
    redactions = ("password", "token", "secret", "auth", "cookie", "key=")
    text_value = str(value)
    lowered = text_value.lower()
    if any(marker in lowered for marker in redactions):
        return "sanitized_sensitive_error"
    return text_value[:500]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _report_markdown(artifact: dict[str, Any]) -> str:
    db = artifact["db"]
    cleanup = artifact["cleanup"]
    backfill = artifact["backfill"]
    final = artifact["final_match_list_state"]
    deleted = cleanup["deleted_rows"]
    imported = backfill["imported_targets"]
    skipped = backfill["skipped_targets"]
    lines = [
        "# M09 Clean Test Data And Backfill Real Steam Matches Report",
        "",
        "## Result",
        "",
        artifact["result"],
        "",
        "## DB backup/SHA evidence",
        "",
        f"- Pre-cleanup DB SHA256: `{db['pre_cleanup_sha256']}`",
        f"- Backup path: `{db['backup_path']}`",
        f"- Backup SHA256: `{db['backup_sha256']}`",
        f"- Post-cleanup/pre-backfill DB SHA256: `{db['post_cleanup_pre_backfill_sha256']}`",
        f"- Final post-backfill DB SHA256: `{db['final_post_backfill_sha256']}`",
        "",
        "## Cleanup actions",
        "",
        cleanup["strategy"],
        "",
        "## Rows deleted/quarantined",
        "",
        f"- Deleted rows: `{json.dumps(deleted, sort_keys=True)}`",
        f"- Remaining controlled rows: `{json.dumps(cleanup['remaining_controlled_rows'], sort_keys=True)}`",
        "",
        "## Active mission cleanup/deactivation",
        "",
        json.dumps(cleanup["active_mission_actions"], indent=2, sort_keys=True, default=str),
        "",
        "## Real Steam targets discovered",
        "",
        f"- Targets: `{len(artifact['real_targets_discovered'])}`",
        "",
        "## Backfill/import results",
        "",
        f"- Imported/reused targets: `{len(imported)}`",
        f"- Processed match ids: `{backfill['processed_match_ids']}`",
        "",
        "## Parser/metric/orchestrator results",
        "",
        f"- Parser artifact ids: `{backfill['parser_artifact_ids']}`",
        f"- Metric snapshot id ranges: `{backfill['metric_snapshot_id_ranges']}`",
        f"- Orchestrator summaries: see `{ARTIFACT_PATH}`",
        "",
        "## Skipped/unavailable targets",
        "",
        f"- Skipped targets: `{len(skipped)}`",
        f"- Reasons: `{json.dumps(_reason_counts(skipped), sort_keys=True)}`",
        "",
        "## Final match list state",
        "",
        f"- Normal match count: `{final['normal_match_count']}`",
        f"- Steam history rows: `{final['steam_history_match_count']}`",
        f"- Real demo rows: `{final['real_demo_match_count']}`",
        f"- Controlled fixture rows: `{final['controlled_fixture_match_count']}`",
        "",
        "## Normal UI/API data expectation",
        "",
        "The normal match data no longer contains `source=controlled_fixture` rows or `fixture://` demo paths.",
        "",
        "## Code changes if any",
        "",
        "Added one focused operational script: `scripts/cleanup_real_data.py`.",
        "",
        "## Tests/checks run",
        "",
        "See final task response for command results.",
        "",
        "## Files changed",
        "",
        f"- `{ARTIFACT_PATH}`",
        f"- `{REPORT_PATH}`",
        "- `scripts/cleanup_real_data.py`",
        "",
        "## Blockers/warnings",
        "",
        "Some Steam history targets may be skipped/unavailable if Valve no longer provides a demo or "
        "auth/download fails.",
        "",
        "## Next recommended task",
        "",
        "Review `/matches` against the cleaned DB and decide whether stale `steam_history` rows should be hidden "
        "from normal user history separately.",
        "",
        "## Token usage if available",
        "",
        "Unavailable to script.",
        "",
    ]
    return "\n".join(lines)


def _reason_counts(skipped: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in skipped:
        reason = str(item.get("reason") or "unknown")
        counts[reason] = counts.get(reason, 0) + 1
    return counts


if __name__ == "__main__":
    main()
