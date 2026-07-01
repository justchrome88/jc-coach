from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Match

SUSPICIOUS_DEMO_BYTES = 1024 * 1024


def demo_storage_report(db: Session, write_manifest: bool = False) -> dict[str, Any]:
    settings = get_settings()
    upload_dir = Path(settings.upload_dir).resolve()
    reports_dir = Path(settings.reports_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    demo_files = sorted(upload_dir.glob("*.dem"), key=lambda item: item.name)
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

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "policy": {
            "raw_delete_after_parse_enabled": False,
            "target_lifecycle": "download -> parse -> verify parsed payload -> delete raw .dem",
            "current_mode": "observe only; raw .dem files are never deleted by this report",
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
    }
    if write_manifest:
        manifest_path = Path(report["manifest_path"])
        manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def write_demo_storage_manifest(db: Session) -> dict[str, Any]:
    return demo_storage_report(db, write_manifest=True)


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


def _resolve_demo_path(value: str | None, upload_dir: Path) -> Path:
    if not value:
        return upload_dir / ""
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (upload_dir / path.name).resolve()


def _sha256_short(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


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
