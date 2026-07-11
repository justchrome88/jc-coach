"""Controlled import, Steam, storage, and import-job routes."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Any

from fastapi import BackgroundTasks, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.routes.base import router
from app.api.routes.serializers import (
    _optional_int,
    serialize_import_job,
)
from app.db.models import ImportJob
from app.db.session import get_db
from app.services.ingestion.demo_downloader import steam_demo_downloader_configured
from app.services.ingestion.demo_storage import demo_storage_report, write_demo_storage_manifest
from app.services.ingestion.jobs import (
    IMPORT_JOB_COMPLETED,
    IMPORT_JOB_IN_PROGRESS,
    IMPORT_JOB_QUEUED,
    create_import_request,
)
from app.services.ingestion.orchestration import (
    CANONICAL_IMPORT_JOB_TYPE,
    import_block_handoff_contract,
    run_demo_import_orchestration,
)
from app.services.ingestion.steam import (
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
from app.services.ingestion.structured_import import import_csv, import_json
from app.services.owner.scope import get_owned_import_job
from app.services.parsing.demo_parser import DemoParseError, import_demo_file, import_inbox_demo, list_inbox_demos


def _run_steam_import_all_background(job_id: int) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        run_steam_import_all_job(db, job_id)
    except BaseException as exc:
        job = db.get(ImportJob, job_id)
        if job is not None and job.status == IMPORT_JOB_IN_PROGRESS:
            mark_steam_import_all_job_interrupted(
                db,
                job,
                reason=f"steam_import_all background task was interrupted: {type(exc).__name__}",
            )
        raise
    finally:
        db.close()

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
    return {"ok": result.get("status") == IMPORT_JOB_COMPLETED, **result}

@router.post("/steam/import/jobs/run-queued")
def run_queued_steam_import_jobs_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    results = process_queued_steam_jobs(db)
    return {
        "ok": all(item.get("status") == IMPORT_JOB_COMPLETED for item in results),
        "processed": len(results),
        "results": results,
    }

@router.post("/steam/import/all")
def import_all_steam_matches_endpoint(
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    job = queue_steam_import_all(db)
    if job.status == IMPORT_JOB_QUEUED:
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
def import_jobs_endpoint(db: Annotated[Session, Depends(get_db)], user_id: int | None = None) -> list[dict]:
    if user_id is None:
        return [serialize_import_job(job) for job in list_import_jobs(db)]
    jobs = (
        db.query(ImportJob)
        .filter(ImportJob.user_id == user_id)
        .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
        .limit(20)
        .all()
    )
    return [serialize_import_job(job) for job in jobs]

@router.get("/import/contract")
def import_contract_endpoint() -> dict:
    return import_block_handoff_contract()

@router.get("/import/jobs/{job_id}")
def import_job_endpoint(db: Annotated[Session, Depends(get_db)], job_id: int, user_id: int | None = None) -> dict:
    job = db.get(ImportJob, job_id) if user_id is None else get_owned_import_job(db, user_id=user_id, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Import job was not found.")
    return serialize_import_job(job)

@router.post("/import/jobs")
def create_import_job_endpoint(
    db: Annotated[Session, Depends(get_db)],
    request: Annotated[dict[str, Any], Body()],
) -> dict:
    payload = request.get("payload") if isinstance(request.get("payload"), dict) else {}
    job_type = str(request.get("job_type") or "demo_import_request")
    if job_type == CANONICAL_IMPORT_JOB_TYPE:
        job = run_demo_import_orchestration(
            db,
            provider=str(request.get("provider") or "steam"),
            payload=payload,
            user_id=_optional_int(request.get("user_id")),
            steam_account_id=_optional_int(request.get("steam_account_id")),
            logical_target_key=request.get("logical_target_key"),
        )
        return serialize_import_job(job)

    job = create_import_request(
        db,
        provider=str(request.get("provider") or "manual"),
        job_type=job_type,
        payload=payload,
        user_id=_optional_int(request.get("user_id")),
        steam_account_id=_optional_int(request.get("steam_account_id")),
        initial_status=str(request.get("status") or "requested"),
        logical_target_key=request.get("logical_target_key"),
    )
    return serialize_import_job(job)

__all__ = (
    'create_import_job_endpoint',
    'demo_storage_report_endpoint',
    'import_all_steam_matches_endpoint',
    'import_contract_endpoint',
    'import_csv_endpoint',
    'import_demo_endpoint',
    'import_demo_from_inbox_endpoint',
    'import_job_endpoint',
    'import_jobs_endpoint',
    'import_json_endpoint',
    'list_demo_inbox_endpoint',
    'run_queued_steam_import_jobs_endpoint',
    'run_steam_import_job_endpoint',
    'steam_accounts_endpoint',
    'steam_demo_downloader_status_endpoint',
    'steam_import_overview_endpoint',
    'steam_login_url_endpoint',
    'steam_share_code_job_endpoint',
    'write_demo_storage_manifest_endpoint',
)
