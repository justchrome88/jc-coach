from __future__ import annotations

from pathlib import Path
from typing import Any

DEMO_RETENTION_POLICY_RETAIN_RAW = "retain_raw_for_parser_development"
DEMO_RETENTION_POLICY_DELETE_AFTER_SUCCESS = "delete_after_success"

DEMO_RETENTION_STATUS_RETAINED_FOR_DEV = "retained_for_parser_dev"
DEMO_RETENTION_STATUS_RETAINED_AFTER_FAILURE = "retained_after_failure"
DEMO_RETENTION_STATUS_CLEANUP_NEEDED = "cleanup_needed"
DEMO_RETENTION_STATUS_UNKNOWN_LEGACY = "unknown_legacy"
DEMO_RETENTION_STATUS_NOT_APPLICABLE = "not_applicable"

CONSISTENCY_DB_REFERENCES_FILE_EXISTS = "db_references_file_and_file_exists"
CONSISTENCY_DB_REFERENCES_FILE_MISSING = "db_references_file_but_file_missing"
CONSISTENCY_FILE_WITHOUT_DB_REFERENCE = "file_exists_without_clear_db_reference"
CONSISTENCY_LEGACY_UNKNOWN = "legacy_unknown"


def current_demo_retention_policy() -> str:
    return DEMO_RETENTION_POLICY_RETAIN_RAW


def delete_after_success_enabled() -> bool:
    return False


def raw_demo_file_metadata(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {"raw_demo_path": None, "raw_demo_size_bytes": None}
    demo_path = Path(path)
    if not demo_path.exists():
        return {"raw_demo_path": str(demo_path), "raw_demo_size_bytes": None}
    return {"raw_demo_path": str(demo_path), "raw_demo_size_bytes": demo_path.stat().st_size}


def retention_metadata(
    *,
    raw_demo_path: str | Path | None,
    parser_success: bool,
    status: str | None = None,
) -> dict[str, Any]:
    if status is None:
        status = (
            DEMO_RETENTION_STATUS_RETAINED_FOR_DEV
            if parser_success
            else DEMO_RETENTION_STATUS_RETAINED_AFTER_FAILURE
        )
    return {
        "demo_retention_policy": current_demo_retention_policy(),
        "demo_retention_status": status,
        "parser_success": parser_success,
        **raw_demo_file_metadata(raw_demo_path),
    }


def delete_raw_demo_after_success(path: str | Path, *, enabled: bool = False) -> dict[str, Any]:
    if not enabled:
        return {
            "deleted": False,
            "demo_retention_policy": current_demo_retention_policy(),
            "demo_retention_status": DEMO_RETENTION_STATUS_RETAINED_FOR_DEV,
            "reason": "delete_after_success disabled",
            **raw_demo_file_metadata(path),
        }
    demo_path = Path(path)
    if demo_path.exists():
        size = demo_path.stat().st_size
        demo_path.unlink()
        return {
            "deleted": True,
            "demo_retention_policy": DEMO_RETENTION_POLICY_DELETE_AFTER_SUCCESS,
            "demo_retention_status": "raw_demo_deleted",
            "raw_demo_path": str(demo_path),
            "raw_demo_size_bytes": size,
        }
    return {
        "deleted": False,
        "demo_retention_policy": DEMO_RETENTION_POLICY_DELETE_AFTER_SUCCESS,
        "demo_retention_status": DEMO_RETENTION_STATUS_NOT_APPLICABLE,
        "reason": "raw demo file missing",
        "raw_demo_path": str(demo_path),
        "raw_demo_size_bytes": None,
    }
