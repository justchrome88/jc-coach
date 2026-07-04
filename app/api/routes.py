from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models import ImportJob, Match
from app.db.session import get_db
from app.services.ai_coach import (
    ai_provider_health,
    build_ai_coach_payload,
    generate_ai_coach_with_provider,
    latest_ai_coach_report,
    latest_ai_handoff,
    list_ai_coach_reports,
    prepare_ai_coach_handoff,
    save_ai_coach_result,
    serialize_ai_coach_report,
)
from app.services.aim_stats import get_aim_profile
from app.services.analytics import compare_periods, get_map_stats, get_summary
from app.services.demo_parser import DemoParseError, import_demo_file, import_inbox_demo, list_inbox_demos
from app.services.demo_storage import demo_storage_report, write_demo_storage_manifest
from app.services.importer import import_csv, import_json
from app.services.match_queries import playable_match_select
from app.services.recommendation_tracking import (
    extend_recommendation_target,
    get_active_recommendation_progress,
    get_all_recommendation_progress,
    list_recommendation_history,
    recommendation_category_summary,
    restart_recommendation_category,
    update_recommendation_status,
)
from app.services.report_generator import generate_report, latest_report
from app.services.steam_demo_downloader import steam_demo_downloader_configured
from app.services.steam_integration import (
    create_steam_import_job,
    list_import_jobs,
    list_steam_accounts,
    mark_steam_import_all_job_interrupted,
    parse_share_code_input,
    process_queued_steam_jobs,
    queue_steam_import_all,
    run_steam_import_all_job,
    steam_import_overview,
    steam_login_url,
    sync_match_history_job,
)

router = APIRouter(prefix="/api")


def _run_steam_import_all_background(job_id: int) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        run_steam_import_all_job(db, job_id)
    except BaseException as exc:
        job = db.get(ImportJob, job_id)
        if job is not None and job.status == "running":
            mark_steam_import_all_job_interrupted(
                db,
                job,
                reason=f"steam_import_all background task was interrupted: {type(exc).__name__}",
            )
        raise
    finally:
        db.close()


@router.get("/matches")
def list_matches(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    matches = db.scalars(playable_match_select().order_by(Match.played_at.desc().nulls_last(), Match.id.desc())).all()
    return [serialize_match(match) for match in matches]


@router.post("/import/csv")
async def import_csv_endpoint(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    result = import_csv(db, await file.read(), source="csv")
    return {"ok": True, **result}


@router.post("/import/json")
async def import_json_endpoint(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    try:
        result = import_json(db, await file.read(), source="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.post("/import/demo")
async def import_demo_endpoint(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    player_identifier: str | None = None,
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".dem"):
        raise HTTPException(status_code=400, detail="Upload a .dem file")
    with NamedTemporaryFile(suffix=".dem", delete=True) as temporary:
        temporary.write(await file.read())
        temporary.flush()
        try:
            result = import_demo_file(
                db,
                Path(temporary.name),
                original_filename=file.filename,
                player_identifier=player_identifier,
            )
        except DemoParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.get("/import/demo/inbox")
def list_demo_inbox_endpoint() -> dict:
    return {"files": list_inbox_demos()}


@router.post("/import/demo/inbox")
def import_demo_from_inbox_endpoint(
    db: Annotated[Session, Depends(get_db)],
    filename: str,
    player_identifier: str | None = None,
) -> dict:
    try:
        result = import_inbox_demo(db, filename, player_identifier=player_identifier)
    except DemoParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.get("/analytics/summary")
def analytics_summary(db: Annotated[Session, Depends(get_db)]) -> dict:
    matches = db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    summary = get_summary(matches)
    comparison = compare_periods(matches)
    map_stats = get_map_stats(matches)
    return {"summary": summary, "comparison": comparison, "map_stats": map_stats}


@router.get("/analytics/aim")
def analytics_aim_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    matches = db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    return get_aim_profile(matches)


@router.get("/recommendations/active")
def active_recommendation(db: Annotated[Session, Depends(get_db)]) -> dict:
    progress = get_active_recommendation_progress(db)
    if not progress:
        raise HTTPException(status_code=404, detail="No active recommendation yet")
    recommendation = progress["recommendation"]
    return {
        "id": recommendation.id,
        "title": recommendation.title,
        "status": recommendation.status,
        "baseline": progress["baseline"],
        "target": progress["target"],
        "counts": progress["counts"],
        "progress_score": progress["progress_score"],
        "completed_matches": progress["completed_matches"],
        "target_matches": progress["target_matches"],
        "summary": progress["summary"],
    }


@router.get("/recommendations")
def all_recommendations(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    progress_items = get_all_recommendation_progress(db)
    return [
        {
            "id": item["recommendation"].id,
            "title": item["recommendation"].title,
            "category": item["recommendation"].category,
            "status": item["recommendation"].status,
            "baseline": item["baseline"],
            "target": item["target"],
            "counts": item["counts"],
            "progress_score": item["progress_score"],
            "completed_matches": item["completed_matches"],
            "target_matches": item["target_matches"],
            "summary": item["summary"],
        }
        for item in progress_items
    ]


@router.get("/recommendations/history")
def recommendation_history_endpoint(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    return [
        {
            "id": item.id,
            "category": item.category,
            "title": item.title,
            "status": item.status,
            "priority": item.priority,
            "started_at": item.started_at,
            "ended_at": item.ended_at,
            "target_period_matches": item.target_period_matches,
            "baseline_period_matches": item.baseline_period_matches,
        }
        for item in list_recommendation_history(db)
    ]


@router.get("/recommendations/categories")
def recommendation_categories_endpoint(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    return recommendation_category_summary(db)


@router.post("/recommendations/{recommendation_id}/status")
def update_recommendation_status_endpoint(
    db: Annotated[Session, Depends(get_db)],
    recommendation_id: int,
    status: str,
) -> dict:
    try:
        recommendation = update_recommendation_status(db, recommendation_id, status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "id": recommendation.id, "status": recommendation.status}


@router.post("/recommendations/{recommendation_id}/extend")
def extend_recommendation_endpoint(
    db: Annotated[Session, Depends(get_db)],
    recommendation_id: int,
    additional_matches: int = 5,
) -> dict:
    try:
        recommendation = extend_recommendation_target(db, recommendation_id, additional_matches)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "id": recommendation.id,
        "target_period_matches": recommendation.target_period_matches,
    }


@router.post("/recommendations/categories/{category}/restart")
def restart_recommendation_category_endpoint(db: Annotated[Session, Depends(get_db)], category: str) -> dict:
    try:
        recommendation = restart_recommendation_category(db, category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "id": recommendation.id, "category": recommendation.category, "status": recommendation.status}


@router.post("/reports/generate")
def generate_report_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    report = generate_report(db)
    return {"ok": True, "id": report.id, "matches_count": report.matches_count, "created_at": report.created_at}


@router.get("/reports/latest")
def latest_report_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    report = latest_report(db)
    if report is None:
        raise HTTPException(status_code=404, detail="No reports generated yet")
    return {
        "id": report.id,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "matches_count": report.matches_count,
        "report_markdown": report.report_markdown,
        "created_at": report.created_at,
    }


@router.get("/coach/ai/payload")
def ai_coach_payload_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    return build_ai_coach_payload(db)


@router.post("/coach/ai/handoff")
def ai_coach_handoff_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"ok": True, **prepare_ai_coach_handoff(db)}


@router.get("/coach/ai/handoff/latest")
def latest_ai_coach_handoff_endpoint() -> dict:
    handoff = latest_ai_handoff()
    if handoff is None:
        raise HTTPException(status_code=404, detail="No AI coach handoff generated yet")
    return handoff


@router.get("/coach/ai/provider/health")
def ai_provider_health_endpoint() -> dict:
    return ai_provider_health()


@router.post("/coach/ai/generate")
def generate_ai_coach_with_provider_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    try:
        report = generate_ai_coach_with_provider(db)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "id": report.id, "created_at": report.created_at, "source_ref": report.source_ref}


@router.post("/coach/ai/result")
def save_ai_coach_result_endpoint(
    db: Annotated[Session, Depends(get_db)],
    report_markdown: str,
    source_ref: str | None = None,
) -> dict:
    try:
        report = save_ai_coach_result(db, report_markdown, source_ref=source_ref)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "id": report.id, "created_at": report.created_at}


@router.get("/coach/ai/result/latest")
def latest_ai_coach_result_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    report = latest_ai_coach_report(db)
    if report is None:
        raise HTTPException(status_code=404, detail="No AI coach report saved yet")
    return serialize_ai_coach_report(report)


@router.get("/coach/ai/results")
def ai_coach_results_endpoint(db: Annotated[Session, Depends(get_db)], limit: int = 10) -> list[dict]:
    return [serialize_ai_coach_report(report) for report in list_ai_coach_reports(db, limit=max(1, min(limit, 50)))]


@router.get("/steam/login-url")
def steam_login_url_endpoint() -> dict:
    return {"url": steam_login_url()}


@router.get("/steam/accounts")
def steam_accounts_endpoint(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    return [
        {
            "id": account.id,
            "steam_id": account.steam_id,
            "persona_name": account.persona_name,
            "sync_enabled": bool(account.sync_enabled),
            "last_sync_at": account.last_sync_at,
            "has_match_auth_code": bool(account.match_auth_code),
        }
        for account in list_steam_accounts(db)
    ]


@router.post("/steam/import/share-code")
def steam_share_code_job_endpoint(db: Annotated[Session, Depends(get_db)], share_code: str) -> dict:
    try:
        payload = parse_share_code_input(share_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = create_steam_import_job(db, None, "share_code_import", payload)
    return {"ok": True, "job_id": job.id, "status": job.status}


@router.post("/steam/import/jobs/{job_id}/run")
def run_steam_import_job_endpoint(db: Annotated[Session, Depends(get_db)], job_id: int) -> dict:
    try:
        result = sync_match_history_job(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": result.get("status") == "succeeded", **result}


@router.post("/steam/import/jobs/run-queued")
def run_queued_steam_import_jobs_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    results = process_queued_steam_jobs(db)
    return {
        "ok": all(item.get("status") == "succeeded" for item in results),
        "processed": len(results),
        "results": results,
    }


@router.post("/steam/import/all")
def import_all_steam_matches_endpoint(
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    job = queue_steam_import_all(db)
    if job.status == "queued":
        background_tasks.add_task(_run_steam_import_all_background, job.id)
    return {
        "ok": True,
        "job_id": job.id,
        "status": job.status,
        "message": "Steam import job started. Poll /api/steam/import/overview for progress.",
    }


@router.get("/steam/import/overview")
def steam_import_overview_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    overview = steam_import_overview(db)
    current_job = overview.pop("current_job")
    return {
        **overview,
        "current_job": serialize_import_job(current_job) if current_job else None,
    }


@router.get("/steam/demo-downloader/status")
def steam_demo_downloader_status_endpoint() -> dict:
    return {"configured": steam_demo_downloader_configured()}


@router.get("/storage/demos")
def demo_storage_report_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    return demo_storage_report(db)


@router.post("/storage/demos/manifest")
def write_demo_storage_manifest_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    report = write_demo_storage_manifest(db)
    return {"ok": True, "manifest_path": report["manifest_path"], "totals": report["totals"]}


@router.get("/import/jobs")
def import_jobs_endpoint(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    return [serialize_import_job(job) for job in list_import_jobs(db)]


def serialize_import_job(job: ImportJob) -> dict:
    return {
        "id": job.id,
        "provider": job.provider,
        "job_type": job.job_type,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_message": job.error_message,
    }


def serialize_match(match: Match) -> dict:
    raw = _match_raw(match)
    return {
        "id": match.id,
        "source": match.source,
        "external_match_id": match.external_match_id,
        "played_at": match.played_at.isoformat() if match.played_at else None,
        "played_at_source": raw.get("played_at_source"),
        "map_name": match.map_name,
        "mode": match.mode,
        "result": match.result,
        "rounds_for": match.rounds_for,
        "rounds_against": match.rounds_against,
        "kills": match.kills,
        "deaths": match.deaths,
        "assists": match.assists,
        "kd": match.kd,
        "adr": match.adr,
        "kast": match.kast,
        "rating": match.rating,
        "swing_score": match.swing_score,
        "headshot_percent": match.headshot_percent,
        "entry_kills": match.entry_kills,
        "entry_deaths": match.entry_deaths,
        "early_deaths": match.early_deaths,
        "flash_assists": match.flash_assists,
        "utility_damage": match.utility_damage,
        "enemies_flashed": match.enemies_flashed,
        "clutches_won": match.clutches_won,
        "clutches_lost": match.clutches_lost,
    }


def _match_raw(match: Match) -> dict:
    try:
        raw = json.loads(match.raw_json or "{}")
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}
