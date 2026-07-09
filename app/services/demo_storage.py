from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Match
from app.services.demo_retention import (
    CONSISTENCY_DB_REFERENCES_FILE_EXISTS,
    CONSISTENCY_DB_REFERENCES_FILE_MISSING,
    CONSISTENCY_FILE_WITHOUT_DB_REFERENCE,
    CONSISTENCY_LEGACY_UNKNOWN,
    DEMO_RETENTION_POLICY_RETAIN_RAW,
    current_demo_retention_policy,
    delete_after_success_enabled,
)

SUSPICIOUS_DEMO_BYTES = 1024 * 1024
RETAINED_DEMO_DIRNAME = "retained"
RAW_DEMO_STORAGE_VERSION = "2026-07-09.1"


def demo_storage_report(db: Session, write_manifest: bool = False) -> dict[str, Any]:
    settings = get_settings()
    upload_dir = Path(settings.upload_dir).resolve()
    reports_dir = Path(settings.reports_dir).resolve()
    temp_dir = Path(settings.temp_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    demo_files = _demo_files(upload_dir)
    file_items = [_file_item(path, upload_dir) for path in demo_files]
    file_by_path = {item["path"]: item for item in file_items}
    file_paths = set(file_by_path)

    matches = list(db.scalars(select(Match).where(Match.demo_file.is_not(None)).order_by(Match.id.asc())).all())
    referenced_paths: set[str] = set()
    existing_referenced_paths: set[str] = set()
    deletion_candidate_paths: set[str] = set()
    referenced: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    deletion_candidates: list[dict[str, Any]] = []

    for match in matches:
        resolved = _resolve_demo_path(match.demo_file, upload_dir)
        path_key = str(resolved)
        referenced_paths.add(path_key)
        raw = _json_loads(match.raw_json)
        parsed_payload_available = bool(raw.get("status") == "parsed" and raw.get("match"))
        match_item = {
            "match_id": match.id,
            "external_match_id": match.external_match_id,
            "map_name": match.map_name,
            "played_at": match.played_at.isoformat() if match.played_at else None,
            "demo_file": match.demo_file,
            "path": path_key,
            "parsed_payload_available": parsed_payload_available,
        }
        if path_key in file_paths:
            file_item = file_by_path[path_key]
            existing_referenced_paths.add(path_key)
            referenced.append({**match_item, "size_bytes": file_item["size_bytes"], "size_mb": file_item["size_mb"]})
            if parsed_payload_available:
                deletion_candidate_paths.add(path_key)
                deletion_candidates.append(
                    {
                        **match_item,
                        "size_bytes": file_item["size_bytes"],
                        "size_mb": file_item["size_mb"],
                        "blocked_by": "raw demo delete policy is disabled until metric schema is approved",
                    }
                )
        else:
            missing.append(match_item)

    unreferenced = [item for item in file_items if item["path"] not in referenced_paths]
    suspicious = [item for item in file_items if item["size_bytes"] < SUSPICIOUS_DEMO_BYTES]
    largest = sorted(file_items, key=lambda item: item["size_bytes"], reverse=True)[:20]

    consistency = classify_demo_file_consistency(db, upload_dir=upload_dir)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "policy": {
            "demo_retention_policy": current_demo_retention_policy(),
            "raw_delete_after_parse_enabled": delete_after_success_enabled(),
            "target_lifecycle": "download -> parse -> verify parsed payload -> delete raw .dem",
            "current_mode": f"{DEMO_RETENTION_POLICY_RETAIN_RAW}; raw .dem files are never deleted by this report",
            "retained_demo_path_rule": f"{upload_dir}/{RETAINED_DEMO_DIRNAME}/<sha1[0:2]>/<sha1>.dem",
            "temporary_acquisition_path": str(temp_dir),
            "parser_handoff_field": "Match.demo_file / DemoParseArtifact.source_demo_file",
        },
        "upload_dir": str(upload_dir),
        "manifest_path": str(reports_dir / "demo_storage_manifest.json"),
        "totals": {
            "files": len(file_items),
            "bytes": sum(item["size_bytes"] for item in file_items),
            "mb": _bytes_to_mb(sum(item["size_bytes"] for item in file_items)),
            "gb": round(sum(item["size_bytes"] for item in file_items) / 1024 / 1024 / 1024, 2),
            "matches_with_demo_file": len(matches),
            "referenced_files": len(existing_referenced_paths),
            "referenced_match_rows": len(referenced),
            "missing_files": len(missing),
            "unreferenced_files": len(unreferenced),
            "suspicious_files": len(suspicious),
            "future_deletion_candidates": len(deletion_candidates),
            "future_deletion_candidate_files": len(deletion_candidate_paths),
            "future_reclaimable_bytes": sum(file_by_path[path]["size_bytes"] for path in deletion_candidate_paths),
            "future_reclaimable_mb": _bytes_to_mb(
                sum(file_by_path[path]["size_bytes"] for path in deletion_candidate_paths)
            ),
        },
        "largest_files": largest,
        "unreferenced_files": unreferenced,
        "missing_files": missing,
        "suspicious_files": suspicious,
        "future_deletion_candidates": deletion_candidates,
        "file_db_consistency": consistency,
    }
    if write_manifest:
        manifest_path = Path(report["manifest_path"])
        manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def write_demo_storage_manifest(db: Session) -> dict[str, Any]:
    return demo_storage_report(db, write_manifest=True)


def classify_demo_file_consistency(db: Session, upload_dir: Path | None = None) -> dict[str, Any]:
    if upload_dir is None:
        upload_dir = Path(get_settings().upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    demo_files = _demo_files(upload_dir)
    file_paths = {str(path.resolve()): path for path in demo_files}
    matches = list(db.scalars(select(Match).where(Match.demo_file.is_not(None)).order_by(Match.id.asc())).all())
    referenced_paths: set[str] = set()
    items: list[dict[str, Any]] = []

    for match in matches:
        resolved = _resolve_demo_path(match.demo_file, upload_dir)
        path_key = str(resolved)
        referenced_paths.add(path_key)
        if not match.demo_file:
            status = CONSISTENCY_LEGACY_UNKNOWN
        elif resolved.exists():
            status = CONSISTENCY_DB_REFERENCES_FILE_EXISTS
        else:
            status = CONSISTENCY_DB_REFERENCES_FILE_MISSING
        items.append(
            {
                "status": status,
                "match_id": match.id,
                "demo_file": match.demo_file,
                "path": path_key,
            }
        )

    for path_key in file_paths:
        if path_key in referenced_paths:
            continue
        items.append(
            {
                "status": CONSISTENCY_FILE_WITHOUT_DB_REFERENCE,
                "match_id": None,
                "demo_file": None,
                "path": path_key,
            }
        )

    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {"counts": counts, "items": items}


def _file_item(path: Path, upload_dir: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path.resolve()),
        "relative_path": str(path.resolve().relative_to(upload_dir)),
        "size_bytes": stat.st_size,
        "size_mb": _bytes_to_mb(stat.st_size),
        "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "sha256_short": _sha256_short(path) if stat.st_size < SUSPICIOUS_DEMO_BYTES else None,
    }


def store_demo_file(
    source_path: Path,
    original_filename: str | None,
    *,
    storage_budget: Any | None = None,
) -> dict[str, Any]:
    source = source_path.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Demo source file was not found: {source}")
    if source.suffix.lower() != ".dem":
        raise ValueError("Only decompressed .dem files can be retained for parser input.")

    upload_dir = Path(get_settings().upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    sha1 = _sha1(source)
    destination = deterministic_demo_path(sha1, upload_dir=upload_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_size = source.stat().st_size
    copied = False
    status = "already_stored"

    if destination.exists():
        if _sha1(destination) != sha1:
            raise ValueError(f"Stored demo path collision for sha1 {sha1}.")
    elif source == destination:
        status = "already_stored"
    else:
        if storage_budget is not None:
            storage_budget.ensure_upload_write(source_size, phase="copy_to_retained_demo_storage")
        shutil.copy2(source, destination)
        copied = True
        status = "stored"
        if storage_budget is not None:
            storage_budget.record_stored(destination.stat().st_size)

    return {
        "storage_schema_version": RAW_DEMO_STORAGE_VERSION,
        "storage_kind": "retained_raw_demo",
        "storage_status": status,
        "copied": copied,
        "sha1": sha1,
        "size_bytes": destination.stat().st_size,
        "original_filename": Path(original_filename or source.name).name,
        "source_path": str(source),
        "path": str(destination),
        "relative_path": str(destination.relative_to(upload_dir)),
        "parser_handoff_path": str(destination),
        "retention": {
            "class": "retained",
            "reason": "raw demo retained for parser/metrics/coach reproducibility",
            "delete_allowed": False,
        },
        "temporary_source": {
            "path": str(source),
            "cleanup_owner": "caller" if not source.is_relative_to(upload_dir) else "retained_storage",
        },
    }


def deterministic_demo_path(sha1: str, *, upload_dir: Path | None = None) -> Path:
    digest = sha1.strip().lower()
    if len(digest) != 40 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("sha1 must be a 40-character hexadecimal digest.")
    root = Path(upload_dir or get_settings().upload_dir).resolve()
    return root / RETAINED_DEMO_DIRNAME / digest[:2] / f"{digest}.dem"


def _resolve_demo_path(value: str | None, upload_dir: Path) -> Path:
    if not value:
        return upload_dir / ""
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (upload_dir / path).resolve()


def _demo_files(upload_dir: Path) -> list[Path]:
    return sorted((path for path in upload_dir.rglob("*.dem") if path.is_file()), key=lambda item: str(item))


def _sha256_short(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bytes_to_mb(value: int) -> float:
    return round(value / 1024 / 1024, 2)


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}
