"""Application orchestration for controlled demo ingestion."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import DemoParseArtifact, ImportJob, Match
from app.services.ingestion.artifact_integrity import ARTIFACT_STATE_AVAILABLE, artifact_file_integrity
from app.services.ingestion.demo_acquisition import (
    DEMO_ACQUISITION_SUCCESS_OUTCOMES,
    DEMO_ALREADY_AVAILABLE,
    DEMO_AUTH_MISSING,
    DEMO_DOWNLOAD_QUEUED_OR_READY,
    DEMO_FAILED_WITH_ACTIONABLE_ERROR,
    DEMO_NOT_FOUND,
    acquire_steam_demo_reference,
    validate_steam_demo_acquisition_config,
)
from app.services.ingestion.demo_storage import deterministic_demo_path, store_demo_file
from app.services.ingestion.jobs import (
    IMPORT_JOB_COMPLETED,
    IMPORT_JOB_FAILED,
    IMPORT_JOB_IN_PROGRESS,
    IMPORT_JOB_QUEUED,
    IMPORT_JOB_SKIPPED_DUPLICATE,
    complete_import_job,
    create_import_request,
    fail_import_job,
    import_job_result,
    queue_import_job,
    start_import_job,
)
from app.services.owner.scope import assert_match_owner, attach_match_owner_from_import_job, resolve_owner_ids
from app.services.shared.demo_retention import (
    ARTIFACT_CATEGORY_RAW_DEMO,
    RETENTION_CLASS_RETAINED_RAW,
    artifact_retention_metadata,
)

CANONICAL_IMPORT_JOB_TYPE = "demo_import_orchestration"
CANONICAL_IMPORT_ROUTE = "POST /api/import/jobs"
IMPORT_INSPECTION_ROUTES = ("GET /api/import/jobs/{job_id}", "GET /api/import/jobs")
PARSER_HANDOFF_RESULT_PATH = "result_json.parser_handoff.path"
PARSER_HANDOFF_STORAGE_PATH = "storage.artifact.parser_handoff_path"
PARSER_HANDOFF_MATCH_FIELD = "Match.demo_file"
PARSER_HANDOFF_ARTIFACT_FIELD = "DemoParseArtifact.source_demo_file"
STORAGE_ACCEPTANCE_ACCEPTED = "accepted"
STORAGE_ACCEPTANCE_BLOCKED = "blocked"

STORAGE_ALREADY_AVAILABLE = "already_available"
STORAGE_STORED = "stored"
STORAGE_DUPLICATE = "storage_duplicate"
STORAGE_MISSING_FILE = "storage_missing_file"
STORAGE_FAILED_WITH_ACTIONABLE_ERROR = "failed_with_actionable_error"

AcquisitionAdapter = Callable[[Session, dict[str, Any]], dict[str, Any]]


def import_block_handoff_contract() -> dict[str, Any]:
    return {
        "canonical_import_path": {
            "route": CANONICAL_IMPORT_ROUTE,
            "job_type": CANONICAL_IMPORT_JOB_TYPE,
            "provider": "steam",
            "description": "Acquire a demo source, retain the raw .dem artifact, and persist parser handoff metadata.",
        },
        "inspection_routes": list(IMPORT_INSPECTION_ROUTES),
        "retained_raw_demo_path_rule": "UPLOAD_DIR/retained/<sha1[0:2]>/<sha1>.dem",
        "parser_handoff_fields": {
            "result_path": PARSER_HANDOFF_RESULT_PATH,
            "storage_artifact_path": PARSER_HANDOFF_STORAGE_PATH,
            "match_field": PARSER_HANDOFF_MATCH_FIELD,
            "parser_artifact_field": PARSER_HANDOFF_ARTIFACT_FIELD,
        },
        "legacy_import_paths": [
            {
                "route": "POST /api/import/demo",
                "classification": "tolerated",
                "reason": (
                    "Manual .dem upload path still supports parser development but is not the canonical import "
                    "block entrypoint."
                ),
            },
            {
                "route": "POST /api/import/demo/inbox",
                "classification": "tolerated",
                "reason": "Local inbox parsing remains useful for deterministic development and fixtures.",
            },
            {
                "route": "POST /api/import/csv",
                "classification": "tolerated",
                "reason": "Stats-only import path does not acquire or retain raw demos for parser handoff.",
            },
            {
                "route": "POST /api/import/json",
                "classification": "tolerated",
                "reason": "Stats-only import path does not acquire or retain raw demos for parser handoff.",
            },
            {
                "route": "POST /api/steam/import/share-code",
                "classification": "deprecated",
                "reason": (
                    "Legacy Steam share-code job path is superseded by demo_import_orchestration for new parser "
                    "handoff work."
                ),
            },
            {
                "route": "POST /api/steam/import/jobs/{job_id}/run",
                "classification": "deprecated",
                "reason": "Legacy Steam job runner remains readable but is not the canonical import block entrypoint.",
            },
            {
                "route": "POST /api/steam/import/jobs/run-queued",
                "classification": "deprecated",
                "reason": "Legacy queued Steam job runner remains compatibility-only for this import block.",
            },
            {
                "route": "POST /api/steam/import/all",
                "classification": "blocker",
                "reason": (
                    "Live Steam bulk import requires explicit task authorization and must not be used as the parser "
                    "handoff starting point."
                ),
            },
        ],
    }


def run_demo_import_orchestration(
    db: Session,
    *,
    provider: str = "steam",
    payload: dict[str, Any] | None = None,
    user_id: int | None = None,
    steam_account_id: int | None = None,
    logical_target_key: str | None = None,
    acquisition_adapter: AcquisitionAdapter | None = None,
) -> ImportJob:
    payload = dict(payload or {})
    user_id, steam_account_id = resolve_owner_ids(db, user_id=user_id, steam_account_id=steam_account_id)
    job = create_or_reuse_job(
        db,
        provider=provider,
        payload=payload,
        user_id=user_id,
        steam_account_id=steam_account_id,
        logical_target_key=logical_target_key,
    )
    if job.status == IMPORT_JOB_SKIPPED_DUPLICATE:
        return job
    if job.status in {IMPORT_JOB_COMPLETED, IMPORT_JOB_FAILED}:
        return job
    if job.status not in {IMPORT_JOB_QUEUED, IMPORT_JOB_IN_PROGRESS}:
        job = queue_import_job(db, job)
    if job.status != IMPORT_JOB_IN_PROGRESS:
        job = start_import_job(db, job)

    try:
        acquisition_config = validate_acquisition_config(payload)
        acquisition = run_acquisition_or_fixture_adapter(
            db,
            payload=payload,
            acquisition_config=acquisition_config,
            user_id=job.user_id,
            acquisition_adapter=acquisition_adapter,
        )
        if acquisition["outcome"] not in DEMO_ACQUISITION_SUCCESS_OUTCOMES:
            result = serialize_result(
                job=job,
                payload=payload,
                acquisition=acquisition,
                storage=None,
                error_message=_actionable_message(acquisition),
            )
            return fail_import_job(db, job, str(result["error"]["message"]), result=result)

        storage = store_artifact_metadata(db, job=job, payload=payload, acquisition=acquisition)
        result = serialize_result(job=job, payload=payload, acquisition=acquisition, storage=storage)
        if storage["outcome"] in {STORAGE_ALREADY_AVAILABLE, STORAGE_STORED, STORAGE_DUPLICATE}:
            return complete_import_job(db, job, result=result)

        result["overall_outcome"] = IMPORT_JOB_FAILED
        result["job"]["status"] = IMPORT_JOB_FAILED
        result["error"] = {
            "message": storage.get("actionable_reason") or "Demo storage failed.",
            "type": storage.get("error_type"),
        }
        return fail_import_job(db, job, str(result["error"]["message"]), result=result)
    except Exception as exc:
        result = serialize_result(
            job=job,
            payload=payload,
            acquisition={
                "outcome": DEMO_FAILED_WITH_ACTIONABLE_ERROR,
                "config": None,
                "raw": None,
                "actionable_reason": "Unexpected import orchestration failure.",
            },
            storage=None,
            error_message=str(exc) or type(exc).__name__,
            error_type=type(exc).__name__,
        )
        return fail_import_job(db, job, str(result["error"]["message"]), result=result)


def create_or_reuse_job(
    db: Session,
    *,
    provider: str,
    payload: dict[str, Any],
    user_id: int | None,
    steam_account_id: int | None,
    logical_target_key: str | None,
) -> ImportJob:
    return create_import_request(
        db,
        provider=provider,
        job_type=CANONICAL_IMPORT_JOB_TYPE,
        payload=payload,
        user_id=user_id,
        steam_account_id=steam_account_id,
        logical_target_key=logical_target_key,
    )


def validate_acquisition_config(payload: dict[str, Any]) -> dict[str, Any]:
    if _fixture_source_path(payload) is not None or isinstance(payload.get("acquisition_result"), dict):
        return {
            "configured": True,
            "auth_configured": True,
            "helper_installed": True,
            "credential_mode": "deterministic_fixture",
            "missing": [],
            "timeout_seconds": None,
        }
    return validate_steam_demo_acquisition_config()


def run_acquisition_or_fixture_adapter(
    db: Session,
    *,
    payload: dict[str, Any],
    acquisition_config: dict[str, Any],
    user_id: int | None = None,
    acquisition_adapter: AcquisitionAdapter | None = None,
) -> dict[str, Any]:
    if acquisition_adapter is not None:
        return _normalize_acquisition(acquisition_adapter(db, payload), acquisition_config=acquisition_config)

    share_code = _share_code(payload)
    existing = _existing_available_match(db, share_code, user_id=user_id)
    if existing is not None:
        return {
            "outcome": DEMO_ALREADY_AVAILABLE,
            "share_code": share_code,
            "match_id": existing.id,
            "source_path": existing.demo_file,
            "config": acquisition_config,
            "raw": {
                "overall_outcome": DEMO_ALREADY_AVAILABLE,
                "next_action": "Use the existing stored demo; no Steam acquisition is needed.",
            },
            "actionable_reason": None,
        }

    fixture_path = _fixture_source_path(payload)
    if fixture_path is not None:
        return {
            "outcome": DEMO_DOWNLOAD_QUEUED_OR_READY,
            "share_code": share_code,
            "match_id": None,
            "source_path": str(fixture_path),
            "config": acquisition_config,
            "raw": {
                "overall_outcome": DEMO_DOWNLOAD_QUEUED_OR_READY,
                "acquisition_outcome": DEMO_DOWNLOAD_QUEUED_OR_READY,
                "fixture": True,
                "demo_reference": {"kind": "local_demo_file", "has_path": True},
                "next_action": "Store the deterministic local demo fixture for parser handoff.",
            },
            "actionable_reason": None,
        }

    provided = payload.get("acquisition_result")
    if isinstance(provided, dict):
        return _normalize_acquisition(provided, acquisition_config=acquisition_config)

    if not acquisition_config.get("auth_configured"):
        return {
            "outcome": DEMO_AUTH_MISSING,
            "share_code": share_code,
            "match_id": None,
            "source_path": None,
            "config": acquisition_config,
            "raw": {
                "overall_outcome": DEMO_AUTH_MISSING,
                "acquisition_outcome": DEMO_AUTH_MISSING,
                "config": _public_config(acquisition_config),
                "next_action": "Configure Steam bot credentials or provide a deterministic fixture demo path.",
            },
            "actionable_reason": "Steam bot credentials are missing; provide credentials or a fixture demo path.",
        }

    if not share_code:
        return {
            "outcome": DEMO_FAILED_WITH_ACTIONABLE_ERROR,
            "share_code": None,
            "match_id": None,
            "source_path": None,
            "config": acquisition_config,
            "raw": {
                "overall_outcome": DEMO_FAILED_WITH_ACTIONABLE_ERROR,
                "next_action": "Provide payload.share_code or payload.fixture_demo_path.",
            },
            "actionable_reason": "share_code or fixture_demo_path is required.",
        }

    return _normalize_acquisition(
        acquire_steam_demo_reference(db, share_code=share_code, download=True),
        acquisition_config=acquisition_config,
    )


def store_artifact_metadata(
    db: Session,
    *,
    job: ImportJob,
    payload: dict[str, Any],
    acquisition: dict[str, Any],
) -> dict[str, Any]:
    source_path = _source_path(payload, acquisition)
    match = _match_for_storage(db, job=job, payload=payload, acquisition=acquisition)

    if acquisition["outcome"] == DEMO_ALREADY_AVAILABLE and source_path:
        path = Path(str(source_path))
        if path.is_file():
            integrity = artifact_file_integrity(path, reparse_on_problem=True)
            storage = {
                "outcome": STORAGE_ALREADY_AVAILABLE,
                "artifact": {
                    "path": str(path.resolve()),
                    "state": integrity["state"],
                    "sha1": integrity["sha1"],
                    "size_bytes": integrity["size_bytes"],
                    "parser_handoff_path": str(path.resolve()),
                    "match_demo_file": match.demo_file if match is not None else str(path.resolve()),
                    "retention": artifact_retention_metadata(ARTIFACT_CATEGORY_RAW_DEMO, path=path.resolve()),
                    "integrity": integrity,
                },
                "raw": {"storage_status": STORAGE_ALREADY_AVAILABLE, "path": str(path.resolve())},
                "actionable_reason": None,
            }
            _persist_match_storage(db, match=match, storage=storage, import_job_id=job.id)
            return storage

    if not source_path:
        return {
            "outcome": DEMO_NOT_FOUND,
            "artifact": None,
            "raw": None,
            "actionable_reason": "Acquisition did not provide a local demo file path to store.",
            "error_type": "MissingDemoSource",
        }

    try:
        stored = store_demo_file(Path(str(source_path)), _original_filename(payload, source_path))
    except FileNotFoundError as exc:
        return {
            "outcome": STORAGE_MISSING_FILE,
            "artifact": None,
            "raw": None,
            "actionable_reason": str(exc),
            "error_type": type(exc).__name__,
        }
    except Exception as exc:
        return {
            "outcome": STORAGE_FAILED_WITH_ACTIONABLE_ERROR,
            "artifact": None,
            "raw": None,
            "actionable_reason": str(exc) or type(exc).__name__,
            "error_type": type(exc).__name__,
        }

    storage = {
        "outcome": STORAGE_STORED if stored["storage_status"] == "stored" else STORAGE_DUPLICATE,
        "artifact": {
            "storage_kind": stored["storage_kind"],
            "state": stored["state"],
            "sha1": stored["sha1"],
            "size_bytes": stored["size_bytes"],
            "path": stored["path"],
            "relative_path": stored["relative_path"],
            "parser_handoff_path": stored["parser_handoff_path"],
            "retention": stored["retention"],
            "integrity": stored["integrity"],
        },
        "raw": stored,
        "actionable_reason": None,
    }
    _persist_match_storage(db, match=match, storage=storage, import_job_id=job.id)
    _cleanup_download_temporary_source(payload=payload, stored=stored)
    return storage


def _cleanup_download_temporary_source(*, payload: dict[str, Any], stored: dict[str, Any]) -> None:
    if _fixture_source_path(payload) is not None:
        return
    temporary = stored.get("temporary_source")
    if not isinstance(temporary, dict) or temporary.get("cleanup_owner") != "caller":
        return
    path_value = temporary.get("path")
    if not path_value:
        return
    source = Path(str(path_value)).resolve()
    temp_root = Path(get_settings().temp_dir).resolve()
    parent = source.parent
    if (
        not source.is_relative_to(temp_root)
        or parent.parent != temp_root
        or not parent.name.startswith("jc-steam-demo-")
    ):
        return
    shutil.rmtree(parent)
    temporary["cleanup_status"] = "cleaned"


def serialize_result(
    *,
    job: ImportJob,
    payload: dict[str, Any],
    acquisition: dict[str, Any],
    storage: dict[str, Any] | None,
    error_message: str | None = None,
    error_type: str | None = None,
) -> dict[str, Any]:
    artifact = (storage or {}).get("artifact") if storage else None
    parser_handoff_path = artifact.get("parser_handoff_path") if isinstance(artifact, dict) else None
    result = {
        "overall_outcome": IMPORT_JOB_FAILED if error_message else IMPORT_JOB_COMPLETED,
        "logical_target_key": job.logical_target_key,
        "job": {
            "id": job.id,
            "status": IMPORT_JOB_FAILED if error_message else IMPORT_JOB_COMPLETED,
            "job_type": job.job_type,
        },
        "request": {
            "provider": job.provider,
            "share_code": _share_code(payload),
            "has_fixture_demo_path": _fixture_source_path(payload) is not None,
        },
        "acquisition": {
            "outcome": acquisition["outcome"],
            "share_code": acquisition.get("share_code"),
            "match_id": acquisition.get("match_id"),
            "config": _public_config(acquisition.get("config")),
            "result": acquisition.get("raw"),
        },
        "storage": None
        if storage is None
        else {
            "outcome": storage["outcome"],
            "artifact": artifact,
            "result": storage.get("raw"),
        },
        "parser_handoff": {
            "field": "parser_handoff_path",
            "path": parser_handoff_path,
            "match_demo_file": artifact.get("match_demo_file") if isinstance(artifact, dict) else None,
            "match_field": PARSER_HANDOFF_MATCH_FIELD,
            "parser_artifact_field": PARSER_HANDOFF_ARTIFACT_FIELD,
            "next_step": "run_parser_with_parser_handoff_path" if parser_handoff_path else None,
        },
        "error": {"message": error_message, "type": error_type} if error_message else None,
        "created_at": _now_iso(),
    }
    return result


def serialize_orchestration_job(job: ImportJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "status": job.status,
        "logical_target_key": job.logical_target_key,
        "result": import_job_result(job),
        "error_message": job.error_message,
    }


def storage_acceptance_for_import_job(
    db: Session,
    job_id: int,
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    job = db.get(ImportJob, job_id)
    blockers: list[dict[str, Any]] = []
    if job is None:
        return _storage_acceptance_result(
            job=None,
            blockers=[_blocker("import_job_not_found", f"Import job was not found: {job_id}")],
        )

    result = import_job_result(job)
    artifact = _storage_artifact(result)
    parser_handoff_path = _string_or_none((result.get("parser_handoff") or {}).get("path"))
    storage_handoff_path = _string_or_none(artifact.get("parser_handoff_path"))
    artifact_path = _string_or_none(artifact.get("path"))
    accepted_path = parser_handoff_path or storage_handoff_path or artifact_path

    if job.job_type != CANONICAL_IMPORT_JOB_TYPE:
        blockers.append(_blocker("non_canonical_import_job_type", "Import job is not a demo import orchestration job."))
    if job.status != IMPORT_JOB_COMPLETED:
        blockers.append(_blocker("import_job_not_completed", "Import job has not completed successfully."))
    if user_id is not None and job.user_id != user_id:
        blockers.append(_blocker("import_job_owner_mismatch", "Import job does not belong to the requested user."))
    if not artifact:
        blockers.append(
            _blocker("storage_artifact_missing", "Import result does not include storage.artifact metadata.")
        )
    if not accepted_path:
        blockers.append(
            _blocker("parser_handoff_path_missing", "Import result does not include a parser handoff path.")
        )
    if parser_handoff_path and storage_handoff_path and _resolve_path(parser_handoff_path) != _resolve_path(
        storage_handoff_path
    ):
        blockers.append(
            _blocker("parser_handoff_storage_path_mismatch", "result_json and storage artifact paths disagree.")
        )
    if parser_handoff_path and artifact_path and _resolve_path(parser_handoff_path) != _resolve_path(artifact_path):
        blockers.append(
            _blocker("parser_handoff_artifact_path_mismatch", "Parser handoff and artifact paths disagree.")
        )

    integrity = _storage_acceptance_integrity(accepted_path, artifact)
    if integrity.get("state") != ARTIFACT_STATE_AVAILABLE:
        blockers.append(
            _blocker(
                "raw_demo_integrity_failed",
                "Retained raw demo is not available with the expected integrity metadata.",
                state=integrity.get("state"),
                reason=integrity.get("reason"),
            )
        )

    if integrity.get("sha1") and accepted_path:
        expected_path = deterministic_demo_path(str(integrity["sha1"]))
        if _resolve_path(accepted_path) != expected_path:
            blockers.append(
                _blocker(
                    "retained_raw_path_mismatch",
                    "Retained raw demo is not stored at UPLOAD_DIR/retained/<sha1[0:2]>/<sha1>.dem.",
                    expected_path=str(expected_path),
                    actual_path=str(_resolve_path(accepted_path)),
                )
            )

    retention = artifact.get("retention") if isinstance(artifact.get("retention"), dict) else {}
    if not retention:
        blockers.append(_blocker("retention_metadata_missing", "Storage artifact does not include retention metadata."))
    elif (
        retention.get("category") != ARTIFACT_CATEGORY_RAW_DEMO
        or retention.get("retention_class") != RETENTION_CLASS_RETAINED_RAW
        or retention.get("delete_allowed") is not False
    ):
        blockers.append(
            _blocker("retention_metadata_invalid", "Storage artifact retention metadata is not retained raw demo.")
        )

    match, match_discovery = _storage_acceptance_match(
        db,
        job=job,
        result=result,
        parser_handoff_path=accepted_path,
        user_id=user_id,
    )
    if match is None:
        blockers.append(
            _blocker("owned_match_not_found", "No owned match row references the imported storage artifact.")
        )
        parser_artifacts: list[DemoParseArtifact] = []
    else:
        if match.import_job_id != job.id:
            blockers.append(
                _blocker("match_import_job_link_missing", "Match.import_job_id does not reference the job.")
            )
        if accepted_path and _resolve_path(match.demo_file) != _resolve_path(accepted_path):
            blockers.append(_blocker("match_demo_file_mismatch", "Match.demo_file does not match parser handoff path."))
        raw = _json_loads(match.raw_json)
        raw_handoff_path = _string_or_none((raw.get("parser_handoff") or {}).get("path"))
        if raw_handoff_path and accepted_path and _resolve_path(raw_handoff_path) != _resolve_path(accepted_path):
            blockers.append(
                _blocker("match_raw_parser_handoff_mismatch", "Match.raw_json parser handoff path disagrees.")
            )
        parser_artifacts = list(
            db.scalars(
                select(DemoParseArtifact)
                .where(DemoParseArtifact.match_id == match.id)
                .order_by(DemoParseArtifact.id.asc())
            )
        )

    parser_artifact_items = []
    for parser_artifact in parser_artifacts:
        source_demo_file = parser_artifact.source_demo_file
        parser_artifact_items.append(
            {
                "id": parser_artifact.id,
                "match_id": parser_artifact.match_id,
                "source_demo_file": source_demo_file,
                "status": parser_artifact.status,
            }
        )
        if accepted_path and _resolve_path(source_demo_file) != _resolve_path(accepted_path):
            blockers.append(
                _blocker(
                    "parser_artifact_source_demo_file_mismatch",
                    "DemoParseArtifact.source_demo_file does not match parser handoff path.",
                    artifact_id=parser_artifact.id,
                )
            )

    return _storage_acceptance_result(
        job=job,
        blockers=blockers,
        result=result,
        storage_artifact=artifact,
        parser_handoff_path=accepted_path,
        integrity=integrity,
        match=match,
        match_discovery=match_discovery,
        parser_artifacts=parser_artifact_items,
    )


def _storage_acceptance_result(
    *,
    job: ImportJob | None,
    blockers: list[dict[str, Any]],
    result: dict[str, Any] | None = None,
    storage_artifact: dict[str, Any] | None = None,
    parser_handoff_path: str | None = None,
    integrity: dict[str, Any] | None = None,
    match: Match | None = None,
    match_discovery: str | None = None,
    parser_artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "status": STORAGE_ACCEPTANCE_BLOCKED if blockers else STORAGE_ACCEPTANCE_ACCEPTED,
        "accepted": not blockers,
        "blockers": blockers,
        "job": None
        if job is None
        else {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "user_id": job.user_id,
            "steam_account_id": job.steam_account_id,
            "logical_target_key": job.logical_target_key,
        },
        "storage": {
            "artifact": storage_artifact or {},
            "integrity": integrity or {},
            "retained_raw_path_rule": "UPLOAD_DIR/retained/<sha1[0:2]>/<sha1>.dem",
        },
        "parser_handoff": {
            "path": parser_handoff_path,
            "result_field": PARSER_HANDOFF_RESULT_PATH,
            "storage_artifact_field": PARSER_HANDOFF_STORAGE_PATH,
            "match_field": PARSER_HANDOFF_MATCH_FIELD,
            "parser_artifact_field": PARSER_HANDOFF_ARTIFACT_FIELD,
        },
        "match": None
        if match is None
        else {
            "id": match.id,
            "user_id": match.user_id,
            "steam_account_id": match.steam_account_id,
            "import_job_id": match.import_job_id,
            "demo_file": match.demo_file,
            "discovery": match_discovery,
        },
        "parser_artifacts": parser_artifacts or [],
        "result_summary": {
            "overall_outcome": (result or {}).get("overall_outcome"),
            "storage_outcome": ((result or {}).get("storage") or {}).get("outcome"),
            "acquisition_outcome": ((result or {}).get("acquisition") or {}).get("outcome"),
        },
    }


def _storage_acceptance_match(
    db: Session,
    *,
    job: ImportJob,
    result: dict[str, Any],
    parser_handoff_path: str | None,
    user_id: int | None,
) -> tuple[Match | None, str | None]:
    user_filter = user_id if user_id is not None else job.user_id
    selectors: list[tuple[str, Any]] = [
        ("import_job_id", Match.import_job_id == job.id),
    ]
    acquisition_match_id = ((result.get("acquisition") or {}).get("match_id") if isinstance(result, dict) else None)
    if acquisition_match_id is not None:
        match = db.get(Match, int(acquisition_match_id))
        if _match_is_visible(match, user_filter):
            return match, "acquisition.match_id"
    if parser_handoff_path:
        selectors.append(("demo_file", Match.demo_file == str(parser_handoff_path)))
    share_code = None
    if isinstance(result, dict):
        share_code = _string_or_none((result.get("request") or {}).get("share_code"))
    if share_code:
        selectors.append(("external_match_id", Match.external_match_id == share_code))

    for discovery, condition in selectors:
        stmt = select(Match).where(condition).order_by(Match.id.desc())
        if user_filter is not None:
            stmt = stmt.where(Match.user_id == user_filter)
        match = db.scalar(stmt)
        if match is not None:
            return match, discovery
    return None, None


def _match_is_visible(match: Match | None, user_id: int | None) -> bool:
    return match is not None and (user_id is None or match.user_id == user_id)


def _storage_artifact(result: dict[str, Any]) -> dict[str, Any]:
    storage = result.get("storage") if isinstance(result.get("storage"), dict) else {}
    artifact = storage.get("artifact") if isinstance(storage.get("artifact"), dict) else {}
    return dict(artifact)


def _storage_acceptance_integrity(path: str | None, artifact: dict[str, Any]) -> dict[str, Any]:
    expected_sha1 = _string_or_none(artifact.get("sha1"))
    expected_size = _int_or_none(artifact.get("size_bytes"))
    return artifact_file_integrity(
        path,
        expected_sha1=expected_sha1,
        expected_size_bytes=expected_size,
        reparse_on_problem=True,
    )


def _resolve_path(value: str | Path | None) -> Path | None:
    return Path(str(value)).resolve() if value else None


def _blocker(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def _string_or_none(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_acquisition(result: dict[str, Any], *, acquisition_config: dict[str, Any]) -> dict[str, Any]:
    outcome = str(result.get("outcome") or result.get("acquisition_outcome") or result.get("overall_outcome") or "")
    if not outcome:
        outcome = DEMO_FAILED_WITH_ACTIONABLE_ERROR
    error = result.get("error") if isinstance(result.get("error"), dict) else {}
    return {
        "outcome": outcome,
        "share_code": result.get("share_code"),
        "match_id": result.get("match_id"),
        "source_path": result.get("source_path") or result.get("demo_file") or result.get("artifact_path"),
        "config": acquisition_config,
        "raw": result,
        "actionable_reason": result.get("next_action") or error.get("message"),
    }


def _existing_available_match(db: Session, share_code: str | None, *, user_id: int | None = None) -> Match | None:
    if not share_code:
        return None
    stmt = (
        select(Match)
        .where(Match.source == "steam_history")
        .where(Match.external_match_id == share_code)
        .where(Match.demo_file.is_not(None))
        .order_by(Match.id.desc())
    )
    if user_id is not None:
        stmt = stmt.where(or_(Match.user_id == user_id, Match.user_id.is_(None)))
    match = db.scalar(stmt)
    if match is None or not match.demo_file:
        return None
    return match if Path(match.demo_file).is_file() else None


def _match_for_storage(
    db: Session,
    *,
    job: ImportJob,
    payload: dict[str, Any],
    acquisition: dict[str, Any],
) -> Match | None:
    match_id = acquisition.get("match_id")
    if match_id:
        match = db.get(Match, int(match_id))
        if match is not None:
            assert_match_owner(match, user_id=job.user_id)
            attach_match_owner_from_import_job(db, match, job)
            return match

    share_code = _share_code(payload) or acquisition.get("share_code")
    if share_code:
        base_stmt = (
            select(Match)
            .where(Match.source == "steam_history")
            .where(Match.external_match_id == str(share_code))
            .order_by(Match.id.desc())
        )
        existing_any_owner = db.scalar(base_stmt)
        if existing_any_owner is not None and job.user_id is not None and existing_any_owner.user_id not in (
            None,
            job.user_id,
        ):
            raise PermissionError("Steam match belongs to a different user.")
        stmt = base_stmt
        if job.user_id is not None:
            stmt = stmt.where((Match.user_id == job.user_id) | (Match.user_id.is_(None)))
        match = db.scalar(stmt)
        if match is not None:
            attach_match_owner_from_import_job(db, match, job)
            return match
        match = Match(
            user_id=job.user_id,
            steam_account_id=job.steam_account_id,
            import_job_id=job.id,
            source="steam_history",
            external_match_id=str(share_code),
            raw_json=json.dumps({"share_code": str(share_code), "status": "demo_orchestration_requested"}),
        )
        db.add(match)
        db.commit()
        db.refresh(match)
        return match

    return None


def _persist_match_storage(
    db: Session,
    *,
    match: Match | None,
    storage: dict[str, Any],
    import_job_id: int,
) -> None:
    if match is None or not isinstance(storage.get("artifact"), dict):
        return
    job = db.get(ImportJob, import_job_id)
    if job is not None:
        attach_match_owner_from_import_job(db, match, job)
    artifact = storage["artifact"]
    parser_handoff_path = artifact.get("parser_handoff_path") or artifact.get("path")
    if parser_handoff_path:
        match.demo_file = str(parser_handoff_path)
    raw = _json_loads(match.raw_json)
    raw.update(
        {
            "status": "demo_storage_ready",
            "storage": {
                "outcome": storage["outcome"],
                "artifact": artifact,
                "import_job_id": import_job_id,
            },
            "parser_handoff": {
                "field": "Match.demo_file",
                "path": parser_handoff_path,
            },
            "next_step": "parse_demo_from_match_demo_file",
        }
    )
    match.raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str)
    db.commit()


def _source_path(payload: dict[str, Any], acquisition: dict[str, Any]) -> str | None:
    fixture = _fixture_source_path(payload)
    if fixture is not None:
        return str(fixture)
    value = acquisition.get("source_path")
    return str(value) if value else None


def _fixture_source_path(payload: dict[str, Any]) -> Path | None:
    value = payload.get("fixture_demo_path") or payload.get("source_demo_path") or payload.get("local_demo_path")
    return Path(str(value)) if value else None


def _original_filename(payload: dict[str, Any], source_path: str | Path) -> str:
    return str(payload.get("original_filename") or Path(str(source_path)).name)


def _share_code(payload: dict[str, Any]) -> str | None:
    value = payload.get("share_code") or payload.get("match_share_code")
    normalized = str(value).strip() if value is not None else ""
    return normalized or None


def _actionable_message(acquisition: dict[str, Any]) -> str:
    return str(acquisition.get("actionable_reason") or acquisition.get("outcome") or "Import acquisition failed.")


def _public_config(config: dict[str, Any] | None) -> dict[str, Any] | None:
    if config is None:
        return None
    return {
        "configured": config.get("configured"),
        "auth_configured": config.get("auth_configured"),
        "helper_installed": config.get("helper_installed"),
        "credential_mode": config.get("credential_mode"),
        "missing": config.get("missing") or [],
        "timeout_seconds": config.get("timeout_seconds"),
    }


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _now_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()
