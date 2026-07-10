from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ImportJob, Match, SteamAccount, User
from app.services.steam_integration import preview_match_history_codes

FRESH_DISCOVERY_EVIDENCE_SCHEMA_VERSION = "fresh-match-discovery-evidence-v1"
PERSISTED_DRY_RUN_REASON = "remote_discovery_not_performed_in_persisted_dry_run"


def preview_owner_fresh_matches(
    db: Session,
    *,
    owner_user_id: int,
    steam_account_id: int | None = None,
    collector: Callable[..., list[str]] | None = None,
    db_sha_before: str | None = None,
    db_sha_after: str | None = None,
    discovered_at: datetime | None = None,
) -> dict[str, Any]:
    """Return sanitized, ephemeral owner-scoped remote discovery evidence."""
    timestamp = discovered_at or datetime.now(UTC)
    before = _logical_state(db)
    account: SteamAccount | None = None
    try:
        _, account = _resolve_owner(db, owner_user_id, steam_account_id)
        remote = preview_match_history_codes(db, account.id, collector=collector)
        candidates = [_candidate_evidence(db, account, code) for code in remote["codes"]]
        actionable = [item for item in candidates if item["actionable"]]
        status = "success" if candidates else "success_no_changes"
        warnings: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        cursor = remote["cursor"]
        cursor_summary = {
            "source": cursor["source"],
            "initial_sentinel": cursor["initial_sentinel"],
            **_safe_identity(cursor["known_code"]),
        }
    except (ValueError, PermissionError) as exc:
        candidates = []
        actionable = []
        owner_failure = str(exc).startswith("owner_") or str(exc).startswith("steam_account_")
        status = "blocked" if owner_failure else "provider_error"
        warnings = []
        errors = [{"reason_code": str(exc), "safe_message": _safe_error(str(exc))}]
        cursor_summary = {}
    except Exception as exc:  # provider boundary; never expose raw provider text
        candidates = []
        actionable = []
        status = "provider_error"
        warnings = []
        errors = [{
            "reason_code": "remote_provider_failure",
            "safe_message": "Remote Steam discovery failed.",
            "exception_class": type(exc).__name__,
        }]
        cursor_summary = {}
    after = _logical_state(db)
    primary = actionable[0] if actionable else (candidates[0] if candidates else {})
    return {
        "schema_version": FRESH_DISCOVERY_EVIDENCE_SCHEMA_VERSION,
        "owner_user_id": owner_user_id,
        "steam_account_id": account.id if account is not None and account.user_id == owner_user_id else None,
        "discovery_mode": "remote_preview",
        "status": status,
        "safe_identity_hash": primary.get("safe_identity_hash"),
        "safe_identity_suffix": primary.get("safe_identity_suffix"),
        "discovered_at": timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "persisted": False,
        "actionable": bool(actionable),
        "classification": "fresh_actionable" if actionable else "no_fresh_actionable",
        "reason_codes": ["read_only_remote_identity_after_accepted_cursor"] if actionable else [],
        "source_boundary_summary": cursor_summary,
        "db_sha_before": db_sha_before,
        "db_sha_after": db_sha_after,
        "mutation_count": 0,
        "provider_warnings": warnings,
        "provider_errors": errors,
        "fresh_actionable_count": len(actionable),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "logical_state_before": before,
        "logical_state_after": after,
        "logical_state_unchanged": before == after,
        "invariants": ["non_persisted_remote_evidence_is_not_durable_lineage"],
    }


def persisted_dry_run_evidence(
    *,
    owner_user_id: int,
    steam_account_id: int,
    result: dict[str, Any],
    db_sha_before: str | None = None,
    db_sha_after: str | None = None,
) -> dict[str, Any]:
    discovery = result.get("discovery") or {}
    internal = discovery.get("internal_classifications") or {}
    return {
        "schema_version": FRESH_DISCOVERY_EVIDENCE_SCHEMA_VERSION,
        "owner_user_id": owner_user_id,
        "steam_account_id": steam_account_id,
        "discovery_mode": "persisted_dry_run",
        "status": result.get("run", {}).get("status"),
        "safe_identity_hash": None,
        "safe_identity_suffix": None,
        "discovered_at": result.get("run", {}).get("started_at"),
        "persisted": True,
        "actionable": bool(discovery.get("actionable_count")),
        "classification": "persisted_candidates_only",
        "reason_codes": [PERSISTED_DRY_RUN_REASON],
        "source_boundary_summary": {"remote_discovery_performed": False},
        "db_sha_before": db_sha_before,
        "db_sha_after": db_sha_after,
        "mutation_count": _mutation_count(result),
        "provider_warnings": [],
        "provider_errors": [],
        "already_complete": int(internal.get("already_complete", 0)),
        "legacy_stale_pending": int(internal.get("legacy_stale_pending", 0)),
        "fresh_actionable_count": int(internal.get("fresh_actionable", 0)),
        "invariants": ["persisted_dry_run_does_not_contradict_remote_preview"],
    }


def fresh_match_ready_for_h01a(
    *,
    remote_preview: dict[str, Any],
    persisted_dry_run: dict[str, Any],
    real_sync_proof: dict[str, Any],
) -> dict[str, Any]:
    preview_identity = remote_preview.get("safe_identity_hash")
    ready = bool(
        remote_preview.get("schema_version") == FRESH_DISCOVERY_EVIDENCE_SCHEMA_VERSION
        and remote_preview.get("discovery_mode") == "remote_preview"
        and remote_preview.get("status") == "success"
        and remote_preview.get("actionable")
        and remote_preview.get("persisted") is False
        and remote_preview.get("mutation_count") == 0
        and remote_preview.get("logical_state_unchanged")
        and persisted_dry_run.get("discovery_mode") == "persisted_dry_run"
        and PERSISTED_DRY_RUN_REASON in persisted_dry_run.get("reason_codes", [])
        and persisted_dry_run.get("mutation_count") == 0
        and real_sync_proof.get("preview_identity_hash") == preview_identity
        and real_sync_proof.get("consumed_identity_hash") == preview_identity
        and real_sync_proof.get("processed_exactly_one") is True
        and real_sync_proof.get("duplicate_lineage_created") is False
    )
    return {
        "decision": "FRESH_MATCH_READY_FOR_H01A" if ready else "NOT_READY",
        "ready": ready,
        "safe_identity_hash": preview_identity if ready else None,
        "reason_codes": [] if ready else ["fresh_readiness_evidence_incomplete_or_stale"],
        "invariants": [
            "non_persisted_remote_evidence_is_not_durable_lineage",
            "preview_is_not_processing_success",
            "real_sync_must_rediscover_before_consumption",
        ],
    }


def _resolve_owner(db: Session, owner_user_id: int, steam_account_id: int | None) -> tuple[User, SteamAccount]:
    owner = db.get(User, owner_user_id)
    if owner is None or not owner.is_active:
        raise ValueError("owner_not_found")
    stmt = select(SteamAccount).where(SteamAccount.user_id == owner.id).order_by(SteamAccount.id.asc())
    if steam_account_id is not None:
        account = db.get(SteamAccount, steam_account_id)
        if account is None:
            raise ValueError("steam_account_not_found")
        if account.user_id != owner.id:
            raise PermissionError("owner_steam_account_mismatch")
        stmt = stmt.where(SteamAccount.id == steam_account_id)
    account = db.scalar(stmt)
    if account is None:
        raise ValueError("owner_steam_account_missing")
    return owner, account


def _candidate_evidence(db: Session, account: SteamAccount, code: str) -> dict[str, Any]:
    persisted = db.scalar(
        select(Match.id).where(Match.source == "steam_history", Match.external_match_id == code).limit(1)
    )
    return {
        **_safe_identity(code),
        "persisted": persisted is not None,
        "actionable": persisted is None,
        "classification": "fresh_actionable" if persisted is None else "persisted_existing",
        "reason_codes": [
            "read_only_remote_identity_after_accepted_cursor" if persisted is None else "identity_already_persisted"
        ],
        "owner_user_id": account.user_id,
        "steam_account_id": account.id,
    }


def _safe_identity(value: str) -> dict[str, str]:
    return {
        "safe_identity_hash": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "safe_identity_suffix": f"...{value[-8:]}",
    }


def _logical_state(db: Session) -> dict[str, Any]:
    account_rows = db.execute(
        select(SteamAccount.id, SteamAccount.user_id, SteamAccount.last_share_code, SteamAccount.last_sync_at)
        .order_by(SteamAccount.id)
    ).all()
    payload = {
        "matches": int(db.scalar(select(func.count()).select_from(Match)) or 0),
        "import_jobs": int(db.scalar(select(func.count()).select_from(ImportJob)) or 0),
        "accounts": [
            [row.id, row.user_id, row.last_share_code, str(row.last_sync_at) if row.last_sync_at else None]
            for row in account_rows
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "row_counts": {
            "matches": payload["matches"],
            "import_jobs": payload["import_jobs"],
        },
    }


def _mutation_count(result: dict[str, Any]) -> int:
    total = 0
    for action in ("created", "updated", "failed"):
        for value in (result.get("mutations", {}).get(action) or {}).values():
            total += int(value.get("count", 0)) if isinstance(value, dict) else 0
    return total


def _safe_error(reason: str) -> str:
    return {
        "owner_not_found": "The requested owner was not found.",
        "owner_steam_account_missing": "The requested owner has no linked Steam account.",
        "owner_steam_account_mismatch": "The selected Steam account does not belong to the owner.",
        "steam_account_not_found": "The selected Steam account was not found.",
        "match_auth_code_missing": "Remote Steam discovery is not configured for this account.",
        "steam_web_api_key_missing": "Remote Steam discovery is not configured.",
    }.get(reason, "Remote Steam discovery failed closed.")
