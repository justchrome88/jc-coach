"""Persistence transitions for ingestion jobs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ImportJob

IMPORT_JOB_REQUESTED = "requested"
IMPORT_JOB_QUEUED = "queued"
IMPORT_JOB_IN_PROGRESS = "in_progress"
IMPORT_JOB_COMPLETED = "completed"
IMPORT_JOB_FAILED = "failed"
IMPORT_JOB_SKIPPED_DUPLICATE = "skipped_duplicate"

IMPORT_JOB_ACTIVE_STATUSES = frozenset(
    {
        IMPORT_JOB_REQUESTED,
        IMPORT_JOB_QUEUED,
        IMPORT_JOB_IN_PROGRESS,
        "running",
    }
)
IMPORT_JOB_TERMINAL_STATUSES = frozenset(
    {
        IMPORT_JOB_COMPLETED,
        IMPORT_JOB_FAILED,
        IMPORT_JOB_SKIPPED_DUPLICATE,
        "succeeded",
    }
)
IMPORT_JOB_ALLOWED_TRANSITIONS = {
    IMPORT_JOB_REQUESTED: frozenset(
        {
            IMPORT_JOB_QUEUED,
            IMPORT_JOB_IN_PROGRESS,
            IMPORT_JOB_FAILED,
            IMPORT_JOB_SKIPPED_DUPLICATE,
        }
    ),
    IMPORT_JOB_QUEUED: frozenset(
        {
            IMPORT_JOB_IN_PROGRESS,
            IMPORT_JOB_COMPLETED,
            IMPORT_JOB_FAILED,
            IMPORT_JOB_SKIPPED_DUPLICATE,
        }
    ),
    IMPORT_JOB_IN_PROGRESS: frozenset({IMPORT_JOB_COMPLETED, IMPORT_JOB_FAILED}),
    IMPORT_JOB_COMPLETED: frozenset(),
    IMPORT_JOB_FAILED: frozenset(),
    IMPORT_JOB_SKIPPED_DUPLICATE: frozenset(),
    # Legacy statuses remain readable so old rows can be repaired naturally.
    "running": frozenset({IMPORT_JOB_COMPLETED, IMPORT_JOB_FAILED}),
    "succeeded": frozenset(),
}


def create_import_request(
    db: Session,
    *,
    provider: str,
    job_type: str,
    payload: dict[str, Any] | None = None,
    user_id: int | None = None,
    steam_account_id: int | None = None,
    initial_status: str = IMPORT_JOB_REQUESTED,
    logical_target_key: str | None = None,
    skip_duplicate: bool = True,
) -> ImportJob:
    if initial_status not in IMPORT_JOB_ALLOWED_TRANSITIONS:
        raise ValueError(f"Unsupported import job status: {initial_status}")
    payload = payload or {}
    target_key = logical_target_key or build_import_job_target_key(
        provider=provider,
        job_type=job_type,
        payload=payload,
        user_id=user_id,
        steam_account_id=steam_account_id,
    )
    existing = find_active_import_job(db, provider=provider, logical_target_key=target_key)
    if existing is not None and skip_duplicate:
        return _create_skipped_duplicate_job(
            db,
            provider=provider,
            job_type=job_type,
            payload=payload,
            user_id=user_id,
            steam_account_id=steam_account_id,
            logical_target_key=target_key,
            duplicate_of_job_id=existing.id,
        )
    if existing is not None:
        return existing
    now = _now()
    job = ImportJob(
        provider=provider,
        job_type=job_type,
        status=initial_status,
        user_id=user_id,
        steam_account_id=steam_account_id,
        logical_target_key=target_key,
        requested_payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def queue_import_job(db: Session, job: ImportJob) -> ImportJob:
    return transition_import_job(db, job, IMPORT_JOB_QUEUED)


def start_import_job(db: Session, job: ImportJob) -> ImportJob:
    return transition_import_job(db, job, IMPORT_JOB_IN_PROGRESS, started_at=_now())


def complete_import_job(db: Session, job: ImportJob, result: dict[str, Any] | None = None) -> ImportJob:
    return transition_import_job(
        db,
        job,
        IMPORT_JOB_COMPLETED,
        result=result,
        finished_at=_now(),
        error_message=None,
    )


def fail_import_job(
    db: Session,
    job: ImportJob,
    message: str,
    result: dict[str, Any] | None = None,
) -> ImportJob:
    payload = dict(result or {})
    payload.setdefault("error", {"message": message})
    return transition_import_job(
        db,
        job,
        IMPORT_JOB_FAILED,
        result=payload,
        finished_at=_now(),
        error_message=message,
    )


def transition_import_job(
    db: Session,
    job: ImportJob,
    status: str,
    *,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> ImportJob:
    if status not in IMPORT_JOB_ALLOWED_TRANSITIONS:
        raise ValueError(f"Unsupported import job status: {status}")
    allowed = IMPORT_JOB_ALLOWED_TRANSITIONS.get(job.status, frozenset())
    if status != job.status and status not in allowed:
        raise ValueError(f"Invalid import job transition: {job.status} -> {status}")
    job.status = status
    if started_at is not None and job.started_at is None:
        job.started_at = started_at
    if finished_at is not None:
        job.finished_at = finished_at
    if result is not None:
        job.result_json = json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
    job.error_message = error_message
    job.updated_at = _now()
    db.commit()
    db.refresh(job)
    return job


def find_active_import_job(db: Session, *, provider: str, logical_target_key: str | None) -> ImportJob | None:
    if not logical_target_key:
        return None
    return db.scalar(
        select(ImportJob)
        .where(ImportJob.provider == provider)
        .where(ImportJob.logical_target_key == logical_target_key)
        .where(ImportJob.status.in_(tuple(IMPORT_JOB_ACTIVE_STATUSES)))
        .order_by(ImportJob.created_at.asc(), ImportJob.id.asc())
    )


def build_import_job_target_key(
    *,
    provider: str,
    job_type: str,
    payload: dict[str, Any],
    user_id: int | None = None,
    steam_account_id: int | None = None,
) -> str:
    reference = _first_payload_value(
        payload,
        "share_code",
        "match_share_code",
        "external_match_id",
        "match_id",
        "demo_sha1",
        "demo_file",
        "download_url",
        "steam_id",
    )
    if reference is None and steam_account_id is not None:
        reference = f"steam_account:{steam_account_id}"
    if reference is None and user_id is not None:
        reference = f"user:{user_id}"
    if reference is None:
        reference = "global"
    return f"{provider}:{job_type}:{reference}"


def import_job_result(job: ImportJob) -> dict[str, Any]:
    return _json_loads(job.result_json)


def _create_skipped_duplicate_job(
    db: Session,
    *,
    provider: str,
    job_type: str,
    payload: dict[str, Any],
    user_id: int | None,
    steam_account_id: int | None,
    logical_target_key: str,
    duplicate_of_job_id: int,
) -> ImportJob:
    now = _now()
    result = {
        "overall_outcome": IMPORT_JOB_SKIPPED_DUPLICATE,
        "duplicate_of_job_id": duplicate_of_job_id,
        "logical_target_key": logical_target_key,
        "error": None,
    }
    job = ImportJob(
        provider=provider,
        job_type=job_type,
        status=IMPORT_JOB_SKIPPED_DUPLICATE,
        user_id=user_id,
        steam_account_id=steam_account_id,
        logical_target_key=logical_target_key,
        requested_payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
        result_json=json.dumps(result, ensure_ascii=False, sort_keys=True, default=str),
        created_at=now,
        updated_at=now,
        finished_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _first_payload_value(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
