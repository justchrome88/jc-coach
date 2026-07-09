from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DemoParseArtifact

ARTIFACT_INTEGRITY_SCHEMA_VERSION = "artifact-integrity-v1"

ARTIFACT_STATE_AVAILABLE = "available"
ARTIFACT_STATE_MISSING = "missing_file"
ARTIFACT_STATE_CHECKSUM_MISMATCH = "checksum_mismatch"
ARTIFACT_STATE_SIZE_MISMATCH = "size_mismatch"
ARTIFACT_STATE_STALE = "stale"


def artifact_file_integrity(
    path: str | Path | None,
    *,
    expected_sha1: str | None = None,
    expected_size_bytes: int | None = None,
    reparse_on_problem: bool = True,
) -> dict[str, Any]:
    artifact_path = Path(path).resolve() if path else None
    if artifact_path is None:
        return _problem_metadata(
            path=None,
            state=ARTIFACT_STATE_MISSING,
            expected_sha1=expected_sha1,
            expected_size_bytes=expected_size_bytes,
            reparse_on_problem=reparse_on_problem,
            reason="Artifact path is missing.",
        )
    if not artifact_path.is_file():
        return _problem_metadata(
            path=str(artifact_path),
            state=ARTIFACT_STATE_MISSING,
            expected_sha1=expected_sha1,
            expected_size_bytes=expected_size_bytes,
            reparse_on_problem=reparse_on_problem,
            reason="Artifact file is missing.",
        )

    size_bytes = artifact_path.stat().st_size
    sha1 = file_sha1(artifact_path)
    checksum_matches = _normalize_sha1(expected_sha1) == sha1 if expected_sha1 else None
    size_matches = int(expected_size_bytes) == size_bytes if expected_size_bytes is not None else None
    state = ARTIFACT_STATE_AVAILABLE
    reason = None
    if checksum_matches is False:
        state = ARTIFACT_STATE_CHECKSUM_MISMATCH
        reason = "Artifact checksum changed."
    elif size_matches is False:
        state = ARTIFACT_STATE_SIZE_MISMATCH
        reason = "Artifact size changed."

    rebuild_needed = state != ARTIFACT_STATE_AVAILABLE
    return {
        "schema_version": ARTIFACT_INTEGRITY_SCHEMA_VERSION,
        "path": str(artifact_path),
        "state": state,
        "exists": True,
        "sha1": sha1,
        "size_bytes": size_bytes,
        "expected_sha1": _normalize_sha1(expected_sha1),
        "expected_size_bytes": expected_size_bytes,
        "checksum_matches": checksum_matches,
        "size_matches": size_matches,
        "rebuild_needed": rebuild_needed,
        "reparse_needed": bool(rebuild_needed and reparse_on_problem),
        "action": "reparse_from_retained_raw_demo" if rebuild_needed and reparse_on_problem else None,
        "reason": reason,
    }


def stale_derived_artifact_metadata(
    *,
    source_integrity: dict[str, Any],
    derived_kind: str,
) -> dict[str, Any]:
    stale = source_integrity.get("state") != ARTIFACT_STATE_AVAILABLE
    return {
        "schema_version": ARTIFACT_INTEGRITY_SCHEMA_VERSION,
        "derived_kind": derived_kind,
        "state": ARTIFACT_STATE_STALE if stale else ARTIFACT_STATE_AVAILABLE,
        "source_artifact": source_integrity,
        "rebuild_needed": stale,
        "reparse_needed": stale if derived_kind == "parser_artifact" else bool(source_integrity.get("reparse_needed")),
        "action": _derived_action(derived_kind, source_integrity) if stale else None,
    }


def parser_artifact_integrity_report(db: Session) -> dict[str, Any]:
    artifacts = list(db.scalars(select(DemoParseArtifact).order_by(DemoParseArtifact.id.asc())).all())
    items = []
    counts: dict[str, int] = {}
    for artifact in artifacts:
        payload = _json_loads(artifact.payload_json)
        source_artifact = payload.get("source_artifact") if isinstance(payload.get("source_artifact"), dict) else {}
        expected_size = _int_or_none(source_artifact.get("size_bytes") or source_artifact.get("expected_size_bytes"))
        integrity = artifact_file_integrity(
            artifact.source_demo_file,
            expected_sha1=artifact.demo_sha1,
            expected_size_bytes=expected_size,
            reparse_on_problem=True,
        )
        derived = stale_derived_artifact_metadata(source_integrity=integrity, derived_kind="parser_artifact")
        counts[derived["state"]] = counts.get(derived["state"], 0) + 1
        items.append(
            {
                "artifact_id": artifact.id,
                "match_id": artifact.match_id,
                "source_demo_file": artifact.source_demo_file,
                "demo_sha1": artifact.demo_sha1,
                "state": derived["state"],
                "rebuild_needed": derived["rebuild_needed"],
                "reparse_needed": derived["reparse_needed"],
                "action": derived["action"],
                "source_artifact": integrity,
            }
        )
    return {"counts": counts, "items": items}


def file_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _problem_metadata(
    *,
    path: str | None,
    state: str,
    expected_sha1: str | None,
    expected_size_bytes: int | None,
    reparse_on_problem: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "schema_version": ARTIFACT_INTEGRITY_SCHEMA_VERSION,
        "path": path,
        "state": state,
        "exists": False,
        "sha1": None,
        "size_bytes": None,
        "expected_sha1": _normalize_sha1(expected_sha1),
        "expected_size_bytes": expected_size_bytes,
        "checksum_matches": False if expected_sha1 else None,
        "size_matches": False if expected_size_bytes is not None else None,
        "rebuild_needed": True,
        "reparse_needed": reparse_on_problem,
        "action": "restore_or_reacquire_artifact_then_reparse" if reparse_on_problem else "rebuild_artifact",
        "reason": reason,
    }


def _derived_action(derived_kind: str, source_integrity: dict[str, Any]) -> str:
    if source_integrity.get("state") == ARTIFACT_STATE_MISSING:
        return f"restore_or_reacquire_source_then_rebuild_{derived_kind}"
    return f"rebuild_{derived_kind}_from_current_source"


def _normalize_sha1(value: str | None) -> str | None:
    text = str(value).strip().lower() if value is not None else ""
    return text if text else None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}
