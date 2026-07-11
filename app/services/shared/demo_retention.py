"""Immutable retention policy shared by ingestion, parsing, metrics, and coach."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ARTIFACT_RETENTION_SCHEMA_VERSION = "artifact-retention-v1"

ARTIFACT_CATEGORY_RAW_DEMO = "raw_demo"
ARTIFACT_CATEGORY_PARSER_ARTIFACT = "parser_artifact"
ARTIFACT_CATEGORY_NORMALIZED_EVENT_STORE = "normalized_event_store"
ARTIFACT_CATEGORY_METRIC_SNAPSHOT = "metric_snapshot"
ARTIFACT_CATEGORY_COACH_OUTPUT = "coach_output"
ARTIFACT_CATEGORY_TEMPORARY_FILE = "temporary_file"

RETENTION_CLASS_RETAINED_RAW = "retained_raw"
RETENTION_CLASS_DERIVED_REBUILDABLE = "derived_rebuildable"
RETENTION_CLASS_TEMPORARY = "temporary"
RETENTION_CLASS_FINAL_OUTPUT = "final_output"

ARTIFACT_RETENTION_CLASSES = {
    ARTIFACT_CATEGORY_RAW_DEMO: RETENTION_CLASS_RETAINED_RAW,
    ARTIFACT_CATEGORY_PARSER_ARTIFACT: RETENTION_CLASS_DERIVED_REBUILDABLE,
    ARTIFACT_CATEGORY_NORMALIZED_EVENT_STORE: RETENTION_CLASS_DERIVED_REBUILDABLE,
    ARTIFACT_CATEGORY_METRIC_SNAPSHOT: RETENTION_CLASS_DERIVED_REBUILDABLE,
    ARTIFACT_CATEGORY_COACH_OUTPUT: RETENTION_CLASS_FINAL_OUTPUT,
    ARTIFACT_CATEGORY_TEMPORARY_FILE: RETENTION_CLASS_TEMPORARY,
}

_RETENTION_REASONS = {
    ARTIFACT_CATEGORY_RAW_DEMO: "Raw demo evidence is retained for parser, metric, and coach reproducibility.",
    ARTIFACT_CATEGORY_PARSER_ARTIFACT: "Parser artifact can be rebuilt from retained raw demo evidence.",
    ARTIFACT_CATEGORY_NORMALIZED_EVENT_STORE: (
        "Normalized event store can be rebuilt from parser artifact and raw demo evidence."
    ),
    ARTIFACT_CATEGORY_METRIC_SNAPSHOT: "Metric snapshot can be rebuilt from normalized events and parser artifacts.",
    ARTIFACT_CATEGORY_COACH_OUTPUT: "Coach output is a final user-facing artifact, not temporary cleanup data.",
    ARTIFACT_CATEGORY_TEMPORARY_FILE: "Temporary task artifact may be cleaned by its owner.",
}

DEMO_RETENTION_POLICY_RETAIN_RAW = "retain_raw_for_parser_development"
DEMO_RETENTION_POLICY_DELETE_AFTER_SUCCESS = "delete_after_success"

DEMO_RETENTION_STATUS_RETAINED_FOR_DEV = "retained_for_parser_dev"
DEMO_RETENTION_STATUS_RETAINED_AFTER_FAILURE = "retained_after_failure"
DEMO_RETENTION_STATUS_CLEANUP_NEEDED = "cleanup_needed"
DEMO_RETENTION_STATUS_UNKNOWN_LEGACY = "unknown_legacy"
DEMO_RETENTION_STATUS_NOT_APPLICABLE = "not_applicable"

CONSISTENCY_DB_REFERENCES_FILE_EXISTS = "db_references_file_and_file_exists"
CONSISTENCY_DB_REFERENCES_FILE_MISSING = "db_references_file_but_file_missing"
CONSISTENCY_DB_REFERENCES_FILE_CHANGED = "db_references_file_but_integrity_changed"
CONSISTENCY_FILE_WITHOUT_DB_REFERENCE = "file_exists_without_clear_db_reference"
CONSISTENCY_LEGACY_UNKNOWN = "legacy_unknown"


def current_demo_retention_policy() -> str:
    return DEMO_RETENTION_POLICY_RETAIN_RAW


def delete_after_success_enabled() -> bool:
    return False


def retention_class_for_artifact(category: str) -> str:
    normalized = str(category).strip()
    try:
        return ARTIFACT_RETENTION_CLASSES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown artifact retention category: {category}") from exc


def artifact_retention_metadata(
    category: str,
    *,
    path: str | Path | None = None,
    reason: str | None = None,
    cleanup_owner: str | None = None,
) -> dict[str, Any]:
    retention_class = retention_class_for_artifact(category)
    is_temporary = retention_class == RETENTION_CLASS_TEMPORARY
    is_retained_raw = retention_class == RETENTION_CLASS_RETAINED_RAW
    metadata = {
        "schema_version": ARTIFACT_RETENTION_SCHEMA_VERSION,
        "category": category,
        "class": retention_class,
        "retention_class": retention_class,
        "reason": reason or _RETENTION_REASONS[category],
        "delete_allowed": is_temporary,
        "temporary_cleanup_allowed": is_temporary,
        "requires_explicit_backup_or_list_for_delete": is_retained_raw,
    }
    if path is not None:
        metadata["path"] = str(Path(path))
    if cleanup_owner is not None:
        metadata["cleanup_owner"] = cleanup_owner
    return metadata


def artifact_retention_from_metadata(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return artifact_retention_metadata(ARTIFACT_CATEGORY_TEMPORARY_FILE, reason="Missing artifact metadata.")
    retention = metadata.get("artifact_retention") or metadata.get("retention") or metadata
    if not isinstance(retention, dict):
        return artifact_retention_metadata(ARTIFACT_CATEGORY_TEMPORARY_FILE, reason="Invalid artifact metadata.")
    category = retention.get("category")
    retention_class = retention.get("retention_class") or retention.get("class")
    if category in ARTIFACT_RETENTION_CLASSES and retention_class in set(ARTIFACT_RETENTION_CLASSES.values()):
        return dict(retention)
    if category in ARTIFACT_RETENTION_CLASSES:
        return artifact_retention_metadata(str(category))
    raise ValueError("Artifact metadata does not include a known retention category.")


def is_temporary_artifact(metadata: Any) -> bool:
    return artifact_retention_from_metadata(metadata).get("retention_class") == RETENTION_CLASS_TEMPORARY


def is_retained_raw_artifact(metadata: Any) -> bool:
    return artifact_retention_from_metadata(metadata).get("retention_class") == RETENTION_CLASS_RETAINED_RAW


def cleanup_temporary_artifacts(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    deleted: list[str] = []
    skipped: list[dict[str, Any]] = []
    for artifact in artifacts:
        path_value = artifact.get("path")
        retention = artifact_retention_from_metadata(artifact)
        if retention.get("retention_class") != RETENTION_CLASS_TEMPORARY:
            skipped.append(
                {
                    "path": path_value,
                    "reason": "not_temporary",
                    "retention_class": retention["retention_class"],
                }
            )
            continue
        if retention.get("cleanup_owner") != "task":
            skipped.append({"path": path_value, "reason": "cleanup_owner_not_task"})
            continue
        if not path_value:
            skipped.append({"path": None, "reason": "missing_path"})
            continue
        path = Path(str(path_value))
        if path.exists():
            path.unlink()
            deleted.append(str(path))
        else:
            skipped.append({"path": str(path), "reason": "missing_file"})
    return {"deleted": deleted, "skipped": skipped}


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
        "artifact_retention": artifact_retention_metadata(ARTIFACT_CATEGORY_RAW_DEMO, path=raw_demo_path),
        "parser_success": parser_success,
        **raw_demo_file_metadata(raw_demo_path),
    }


def delete_raw_demo_after_success(
    path: str | Path,
    *,
    enabled: bool = False,
    explicit_backup_or_list: bool = False,
) -> dict[str, Any]:
    if not enabled:
        return {
            "deleted": False,
            "demo_retention_policy": current_demo_retention_policy(),
            "demo_retention_status": DEMO_RETENTION_STATUS_RETAINED_FOR_DEV,
            "reason": "delete_after_success disabled",
            "artifact_retention": artifact_retention_metadata(ARTIFACT_CATEGORY_RAW_DEMO, path=path),
            **raw_demo_file_metadata(path),
        }
    if not explicit_backup_or_list:
        return {
            "deleted": False,
            "demo_retention_policy": current_demo_retention_policy(),
            "demo_retention_status": DEMO_RETENTION_STATUS_RETAINED_FOR_DEV,
            "reason": "retained raw demo delete requires explicit backup or delete list",
            "artifact_retention": artifact_retention_metadata(ARTIFACT_CATEGORY_RAW_DEMO, path=path),
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
            "artifact_retention": artifact_retention_metadata(ARTIFACT_CATEGORY_RAW_DEMO, path=demo_path),
            "raw_demo_path": str(demo_path),
            "raw_demo_size_bytes": size,
        }
    return {
        "deleted": False,
        "demo_retention_policy": DEMO_RETENTION_POLICY_DELETE_AFTER_SUCCESS,
        "demo_retention_status": DEMO_RETENTION_STATUS_NOT_APPLICABLE,
        "reason": "raw demo file missing",
        "artifact_retention": artifact_retention_metadata(ARTIFACT_CATEGORY_RAW_DEMO, path=demo_path),
        "raw_demo_path": str(demo_path),
        "raw_demo_size_bytes": None,
    }
