"""Durable, owner-scoped coordinator for bounded G01 sync invocations.

The coordinator deliberately knows nothing about acquisition, parsing, or coach
implementation.  Those remain exclusively inside ``run_owner_coach_sync``.
"""

from __future__ import annotations

import copy
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AppSetting
from app.services.owner.sync import run_owner_coach_sync

OWNER_COACH_SYNC_BATCH_RESULT_SCHEMA_VERSION = "owner-coach-sync-batch-result-v1"
OWNER_COACH_SYNC_BATCH_OPERATION = "owner_coach_sync_batch"
BATCH_LOCK_TTL = timedelta(minutes=30)
MAX_SUCCESSFUL_TARGET = 50
MAX_RETRYABLE_ATTEMPTS = 2
MAX_NO_PROGRESS_ITERATIONS = 3
ACTIVE_STATUSES = frozenset({"queued", "running"})
TERMINAL_STATUSES = frozenset(
    {"success", "success_no_changes", "partial_success", "target_reached", "exhausted", "blocked", "failed"}
)


def start_owner_coach_sync_batch(
    db: Session,
    *,
    owner_user_id: int,
    mode: str = "single",
    target_successful_new_matches: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create or safely reuse this owner's active batch; no G01 work occurs here."""
    mode, target = _validate_request(mode, target_successful_new_matches)
    active = _read_active_lock(db, owner_user_id)
    if active is not None:
        existing = _load_batch(db, active.get("batch_id"))
        if existing is not None:
            return _public_result(existing, already_running=True)
        return _blocked_missing_state(owner_user_id, mode, target)

    stale = _read_lock(db, owner_user_id)
    if stale is not None:
        recovered = _recover_stale_batch(db, owner_user_id=owner_user_id, stale=stale)
        if recovered is not None and recovered["batch"].get("status") in ACTIVE_STATUSES:
            return _public_result(recovered, already_running=True)

    batch_id = uuid.uuid4().hex
    now = _utcnow()
    lock = _new_lock(owner_user_id=owner_user_id, batch_id=batch_id, now=now)
    if not _acquire_lock(db, lock):
        active = _read_active_lock(db, owner_user_id)
        existing = _load_batch(db, active.get("batch_id") if active else None)
        return (
            _public_result(existing, already_running=True)
            if existing
            else _blocked_missing_state(owner_user_id, mode, target)
        )
    batch = _empty_batch(
        batch_id=batch_id,
        owner_user_id=owner_user_id,
        mode=mode,
        requested_target=target,
        dry_run=dry_run,
        started_at=now,
    )
    try:
        _save_batch(db, batch)
    except Exception:
        db.rollback()
        _release_lock(db, lock)
        raise
    return _public_result(batch)


def get_owner_coach_sync_batch(db: Session, *, owner_user_id: int, batch_id: str) -> dict[str, Any] | None:
    """Return only an owner-scoped, presentation-safe durable aggregate."""
    batch = _load_batch(db, batch_id)
    if batch is None or batch["batch"].get("owner_user_id") != owner_user_id:
        return None
    return _public_result(batch)


def latest_owner_coach_sync_batch(db: Session, *, owner_user_id: int) -> dict[str, Any] | None:
    lock = _read_lock(db, owner_user_id)
    if lock is None:
        return None
    batch = _load_batch(db, lock.get("batch_id"))
    return _public_result(batch) if batch is not None else None


def run_owner_coach_sync_batch_step(
    db: Session,
    *,
    owner_user_id: int,
    batch_id: str,
) -> dict[str, Any] | None:
    """Advance one bounded server-side step.  Stop decisions always live here."""
    batch = _load_batch(db, batch_id)
    if batch is None or batch["batch"].get("owner_user_id") != owner_user_id:
        return None
    if batch["batch"].get("status") in TERMINAL_STATUSES:
        return _public_result(batch)
    lock = _read_active_lock(db, owner_user_id)
    if lock is None or lock.get("batch_id") != batch_id:
        _finalize(db, batch, "blocked", "batch_lock_lost")
        return _public_result(batch)
    if not _refresh_lock(db, lock):
        _finalize(db, batch, "blocked", "batch_lock_lost")
        return _public_result(batch)

    batch["batch"]["status"] = "running"
    selection = _next_specific_match_id(batch)
    try:
        g01_result = run_owner_coach_sync(
            db,
            owner_user_id=owner_user_id,
            max_new_matches=1,
            dry_run=bool(batch["runtime"].get("dry_run")),
            continue_on_match_error=True,
            specific_match_id=selection,
        )
    except Exception:  # defensive boundary; no exception/trace is serialized
        batch["errors"].append({"reason_code": "unexpected_failure", "safe_message": "Batch step failed unexpectedly."})
        _finalize(db, batch, "partial_success" if _success_count(batch) else "failed", "unexpected_failure")
        _release_lock(db, lock)
        return _public_result(batch)

    _append_invocation(batch, g01_result)
    _record_result(batch, g01_result)
    batch["batch"]["g01_invocation_count"] += 1
    _decide_after_step(db, batch, g01_result)
    if batch["batch"]["status"] in TERMINAL_STATUSES:
        _release_lock(db, lock)
    else:
        _save_batch(db, batch)
    return _public_result(batch)


def _validate_request(mode: str, target: int | None) -> tuple[str, int | None]:
    if mode not in {"single", "successful_target", "drain_available"}:
        raise ValueError("invalid_batch_mode")
    if mode == "single":
        return mode, 1
    if mode == "drain_available":
        return mode, None
    if isinstance(target, bool) or target is None:
        raise ValueError("target_successful_new_matches_required")
    parsed = int(target)
    if parsed < 1 or parsed > MAX_SUCCESSFUL_TARGET:
        raise ValueError(f"target_successful_new_matches must be between 1 and {MAX_SUCCESSFUL_TARGET}")
    return mode, parsed


def _empty_batch(
    *, batch_id: str, owner_user_id: int, mode: str, requested_target: int | None, dry_run: bool, started_at: datetime
) -> dict[str, Any]:
    return {
        "schema_version": OWNER_COACH_SYNC_BATCH_RESULT_SCHEMA_VERSION,
        "batch": {
            "batch_id": batch_id,
            "owner_user_id": owner_user_id,
            "mode": mode,
            "requested_successful_new_matches": requested_target,
            "successful_new_matches": 0,
            "status": "queued",
            "stop_reason": None,
            "started_at": _iso(started_at),
            "finished_at": None,
            "g01_invocation_count": 0,
        },
        "aggregate_totals": _empty_totals(),
        "invocations": [],
        "matches": [],
        "coach": {"active_missions": [], "latest_progress": [], "recommendation_suppression": {}},
        "mutations": {},
        "warnings": [],
        "errors": [],
        "runtime": {
            "dry_run": dry_run,
            "candidate_order": [],
            "completed_source_match_ids": [],
            "retry_attempts": {},
            "last_selected_source_match_id": None,
            "no_progress_iterations": 0,
        },
    }


def _empty_totals() -> dict[str, int]:
    return {
        "inspected": 0,
        "discovered": 0,
        "new": 0,
        "reused": 0,
        "skipped": 0,
        "failed": 0,
        "unavailable": 0,
        "retryable_failures": 0,
        "terminal_failures": 0,
        "legacy_stale_pending": 0,
    }


def _append_invocation(batch: dict[str, Any], result: dict[str, Any]) -> None:
    batch["invocations"].append(_sanitize_invocation(result, len(batch["invocations"]) + 1))


def _record_result(batch: dict[str, Any], result: dict[str, Any]) -> None:
    known = {item["identity"].get("source_match_id"): item for item in batch["matches"]}
    completed_before = set(batch["runtime"]["completed_source_match_ids"])
    newly_completed = False
    selected_id = None
    for item in result.get("matches", []):
        summary = _sanitize_match(item)
        source_id = summary["identity"].get("source_match_id")
        if source_id is None:
            continue
        if summary.get("selected"):
            selected_id = source_id
        if source_id not in batch["runtime"]["candidate_order"]:
            batch["runtime"]["candidate_order"].append(source_id)
        known[source_id] = summary
        if summary["status"] == "failed_retryable":
            attempts = batch["runtime"]["retry_attempts"]
            attempts[str(source_id)] = int(attempts.get(str(source_id), 0)) + 1
            summary["retry"] = {
                "attempt_count": attempts[str(source_id)],
                "last_reason_code": (summary.get("reason_codes") or ["retryable_failure"])[0],
                "decision": "retry" if attempts[str(source_id)] < MAX_RETRYABLE_ATTEMPTS else "terminal_skip",
            }
        if _is_newly_completed(summary) and source_id not in completed_before:
            batch["runtime"]["completed_source_match_ids"].append(source_id)
            completed_before.add(source_id)
            newly_completed = True
    batch["matches"] = [known[key] for key in batch["runtime"]["candidate_order"] if key in known]
    _refresh_aggregate_totals(batch)
    _merge_mutations(batch, result.get("mutations") or {})
    batch["coach"] = _sanitize_coach(result.get("coach") or {})
    batch["warnings"].extend(_sanitize_messages(result.get("warnings") or []))
    batch["errors"].extend(_sanitize_messages(result.get("errors") or []))
    if newly_completed:
        batch["runtime"]["no_progress_iterations"] = 0
    elif selected_id == batch["runtime"].get("last_selected_source_match_id"):
        batch["runtime"]["no_progress_iterations"] += 1
    else:
        batch["runtime"]["no_progress_iterations"] = 1
    batch["runtime"]["last_selected_source_match_id"] = selected_id
    batch["batch"]["successful_new_matches"] = _success_count(batch)


def _decide_after_step(db: Session, batch: dict[str, Any], result: dict[str, Any]) -> None:
    info = batch["batch"]
    mode = info["mode"]
    if result.get("run", {}).get("status") == "blocked":
        _finalize(db, batch, "blocked", _first_reason(result) or "provider_blocked")
        return
    if mode == "single":
        status = "success" if _success_count(batch) else _single_status(result)
        _finalize(db, batch, status, "single_step_completed")
        return
    if (
        info["requested_successful_new_matches"] is not None
        and _success_count(batch) >= info["requested_successful_new_matches"]
    ):
        _finalize(db, batch, "target_reached", "successful_target_reached")
        return
    if any(
        item.get("selected") and item.get("status") == "created" and not _is_newly_completed(item)
        for item in batch["matches"]
    ):
        _finalize(db, batch, "blocked", "required_completion_lineage_missing")
        return
    if batch["runtime"]["no_progress_iterations"] >= MAX_NO_PROGRESS_ITERATIONS:
        _finalize(db, batch, "partial_success" if _success_count(batch) else "blocked", "no_progress_guard")
        return
    if _next_specific_match_id(batch) is None:
        if _has_retryable_remaining(batch):
            _finalize(db, batch, "partial_success", "retryable_candidates_remaining")
        else:
            _finalize(db, batch, "exhausted", "no_actionable_currently_retrievable_work")
        return


def _next_specific_match_id(batch: dict[str, Any]) -> int | None:
    completed = set(batch["runtime"]["completed_source_match_ids"])
    retries = batch["runtime"]["retry_attempts"]
    by_id = {item["identity"].get("source_match_id"): item for item in batch["matches"]}
    for source_id in batch["runtime"]["candidate_order"]:
        item = by_id.get(source_id)
        if source_id is None or item is None or source_id in completed:
            continue
        if item.get("discovery_classification") not in {"new", "incomplete", "failed_retryable"}:
            continue
        if int(retries.get(str(source_id), 0)) >= MAX_RETRYABLE_ATTEMPTS:
            continue
        return int(source_id)
    return None


def _is_newly_completed(item: dict[str, Any]) -> bool:
    lineage = item.get("lineage") or {}
    artifact = lineage.get("parser_artifact") or {}
    snapshots = lineage.get("metric_snapshot_ids") or {}
    analysis = lineage.get("analysis_run") or {}
    return bool(
        item.get("selected")
        and item.get("status") == "created"
        and item.get("identity", {}).get("source_match_id")
        and artifact.get("id")
        and lineage.get("event_set_ids")
        and snapshots.get("all")
        and analysis.get("id")
        and "owner_match_cycle_completed" in item.get("reason_codes", [])
    )


def _refresh_aggregate_totals(batch: dict[str, Any]) -> None:
    matches = batch["matches"]
    classifications = [item.get("discovery_classification") for item in matches]
    statuses = [item.get("status") for item in matches]
    batch["aggregate_totals"] = {
        "inspected": len(matches),
        "discovered": len(matches),
        "new": classifications.count("new"),
        "reused": statuses.count("reused"),
        "skipped": statuses.count("skipped"),
        "failed": sum(status in {"failed_retryable", "failed_terminal"} for status in statuses),
        "unavailable": classifications.count("unavailable"),
        "retryable_failures": statuses.count("failed_retryable"),
        "terminal_failures": statuses.count("failed_terminal"),
        "legacy_stale_pending": sum(
            item.get("internal_classification") == "legacy_stale_pending" for item in matches
        ),
    }


def _merge_mutations(batch: dict[str, Any], mutations: dict[str, Any]) -> None:
    for action, entities in mutations.items():
        if not isinstance(entities, dict):
            continue
        target = batch["mutations"].setdefault(action, {})
        for entity, payload in entities.items():
            ids = payload.get("ids", []) if isinstance(payload, dict) else []
            bucket = target.setdefault(entity, {"count": 0, "ids": []})
            bucket["ids"] = sorted(set(bucket["ids"]) | {int(item) for item in ids if isinstance(item, int)})
            bucket["count"] = len(bucket["ids"])


def _has_retryable_remaining(batch: dict[str, Any]) -> bool:
    if any(item.get("status") == "failed_retryable" for item in batch["matches"]):
        return True
    if any(
        item.get("internal_classification") in {"unavailable_retryable", "failed_retryable"}
        for item in batch["matches"]
    ):
        return True
    return any(isinstance(error, dict) and error.get("retryable") for error in batch["errors"])


def _success_count(batch: dict[str, Any]) -> int:
    return len(batch["runtime"]["completed_source_match_ids"])


def _single_status(result: dict[str, Any]) -> str:
    status = result.get("run", {}).get("status")
    if status == "success_no_changes":
        return "success_no_changes"
    if status in {"partial_success", "success"}:
        return "partial_success"
    return "failed"


def _first_reason(result: dict[str, Any]) -> str | None:
    errors = result.get("errors") or []
    return errors[0].get("reason_code") if errors and isinstance(errors[0], dict) else None


def _finalize(db: Session, batch: dict[str, Any], status: str, reason: str) -> None:
    batch["batch"]["status"] = status
    batch["batch"]["stop_reason"] = reason
    batch["batch"]["finished_at"] = _iso(_utcnow())
    _save_batch(db, batch)


def _sanitize_invocation(result: dict[str, Any], invocation_number: int) -> dict[str, Any]:
    run = result.get("run") or {}
    discovery = result.get("discovery") or {}
    return {
        "invocation_number": invocation_number,
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "duration_ms": run.get("duration_ms"),
        "discovery": {
            key: discovery.get(key)
            for key in (
                "candidate_count",
                "selected_count",
                "classifications",
                "internal_classifications",
                "reason_codes",
                "legacy_stale_pending_count",
                "actionable_count",
                "bounded",
            )
        },
        "totals": copy.deepcopy(result.get("totals") or {}),
        "matches": [_sanitize_match(item) for item in result.get("matches", [])],
        "warnings": _sanitize_messages(result.get("warnings") or []),
        "errors": _sanitize_messages(result.get("errors") or []),
    }


def _sanitize_match(item: dict[str, Any]) -> dict[str, Any]:
    lineage = copy.deepcopy(item.get("lineage") or {})
    retained = lineage.get("retained_demo")
    if isinstance(retained, dict):
        retained.pop("path", None)
    return {
        "identity": copy.deepcopy(item.get("identity") or {}),
        "discovery_classification": item.get("discovery_classification"),
        "internal_classification": item.get("internal_classification"),
        "selected": bool(item.get("selected")),
        "status": item.get("status"),
        "reason_codes": list(item.get("reason_codes") or []),
        "retry": copy.deepcopy(item.get("retry") or {}),
        "lineage": lineage,
        "failure": _sanitize_messages([item.get("failure")])[0] if item.get("failure") else None,
    }


def _sanitize_coach(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "active_missions": copy.deepcopy(value.get("active_missions") or []),
        "latest_progress": copy.deepcopy(value.get("latest_progress") or []),
        "recommendation_suppression": copy.deepcopy(value.get("recommendation_suppression") or {}),
    }


def _sanitize_messages(items: list[Any]) -> list[Any]:
    output: list[Any] = []
    for item in items:
        if isinstance(item, dict):
            output.append(
                {
                    key: value
                    for key, value in item.items()
                    if key not in {"traceback", "raw_payload", "payload", "path"}
                }
            )
        elif isinstance(item, str):
            output.append(item[:500])
    return output


def _public_result(batch: dict[str, Any] | None, *, already_running: bool = False) -> dict[str, Any]:
    if batch is None:
        return {}
    result = copy.deepcopy(batch)
    result.pop("runtime", None)
    result["batch"].pop("owner_user_id", None)
    if already_running and result["batch"].get("status") in ACTIVE_STATUSES:
        result["batch"]["status"] = "already_running"
    return result


def _blocked_missing_state(owner_user_id: int, mode: str, target: int | None) -> dict[str, Any]:
    batch = _empty_batch(
        batch_id="unavailable",
        owner_user_id=owner_user_id,
        mode=mode,
        requested_target=target,
        dry_run=False,
        started_at=_utcnow(),
    )
    batch["batch"].update(
        {"status": "blocked", "stop_reason": "batch_state_unavailable", "finished_at": _iso(_utcnow())}
    )
    return _public_result(batch)


def _batch_key(batch_id: str) -> str:
    return f"owner_coach_sync_batch:{batch_id}"


def _lock_key(owner_user_id: int) -> str:
    return f"lock:{OWNER_COACH_SYNC_BATCH_OPERATION}:{owner_user_id}"


def _save_batch(db: Session, batch: dict[str, Any]) -> None:
    key = _batch_key(batch["batch"]["batch_id"])
    value = json.dumps(batch, sort_keys=True, default=str)
    setting = db.get(AppSetting, key)
    if setting is None:
        db.add(AppSetting(key=key, value=value))
    else:
        setting.value = value
    db.commit()


def _load_batch(db: Session, batch_id: Any) -> dict[str, Any] | None:
    if not isinstance(batch_id, str) or not batch_id:
        return None
    setting = db.get(AppSetting, _batch_key(batch_id))
    if setting is None:
        return None
    try:
        value = json.loads(setting.value)
    except json.JSONDecodeError:
        return None
    return (
        value
        if isinstance(value, dict) and value.get("schema_version") == OWNER_COACH_SYNC_BATCH_RESULT_SCHEMA_VERSION
        else None
    )


def _new_lock(*, owner_user_id: int, batch_id: str, now: datetime) -> dict[str, Any]:
    return {
        "key": _lock_key(owner_user_id),
        "operation": OWNER_COACH_SYNC_BATCH_OPERATION,
        "batch_id": batch_id,
        "token": secrets.token_urlsafe(18),
        "acquired_at": _iso(now),
        "expires_at": _iso(now + BATCH_LOCK_TTL),
    }


def _read_lock(db: Session, owner_user_id: int) -> dict[str, Any] | None:
    setting = db.get(AppSetting, _lock_key(owner_user_id))
    if setting is None:
        return None
    try:
        lock = json.loads(setting.value)
    except json.JSONDecodeError:
        return None
    return lock if isinstance(lock, dict) and lock.get("operation") == OWNER_COACH_SYNC_BATCH_OPERATION else None


def _read_active_lock(db: Session, owner_user_id: int) -> dict[str, Any] | None:
    lock = _read_lock(db, owner_user_id)
    return lock if lock is not None and _parse_datetime(lock.get("expires_at")) > _utcnow() else None


def _acquire_lock(db: Session, lock: dict[str, Any]) -> bool:
    db.add(AppSetting(key=lock["key"], value=json.dumps(lock, sort_keys=True)))
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def _refresh_lock(db: Session, lock: dict[str, Any]) -> bool:
    original = json.dumps(lock, sort_keys=True)
    refreshed = dict(lock)
    refreshed["expires_at"] = _iso(_utcnow() + BATCH_LOCK_TTL)
    changed = db.execute(
        update(AppSetting)
        .where(AppSetting.key == lock["key"])
        .where(AppSetting.value == original)
        .values(value=json.dumps(refreshed, sort_keys=True))
    )
    db.commit()
    if changed.rowcount != 1:
        return False
    lock.clear()
    lock.update(refreshed)
    return True


def _release_lock(db: Session, lock: dict[str, Any]) -> None:
    db.execute(
        delete(AppSetting)
        .where(AppSetting.key == lock["key"])
        .where(AppSetting.value == json.dumps(lock, sort_keys=True))
    )
    db.commit()


def _recover_stale_batch(db: Session, *, owner_user_id: int, stale: dict[str, Any]) -> dict[str, Any] | None:
    batch = _load_batch(db, stale.get("batch_id"))
    if batch is None or batch["batch"].get("owner_user_id") != owner_user_id:
        return None
    if batch["batch"].get("status") in TERMINAL_STATUSES:
        db.execute(delete(AppSetting).where(AppSetting.key == stale["key"]))
        db.commit()
        return batch
    replacement = _new_lock(owner_user_id=owner_user_id, batch_id=batch["batch"]["batch_id"], now=_utcnow())
    changed = db.execute(
        update(AppSetting)
        .where(AppSetting.key == stale["key"])
        .where(AppSetting.value == json.dumps(stale, sort_keys=True))
        .values(value=json.dumps(replacement, sort_keys=True))
    )
    db.commit()
    if changed.rowcount != 1:
        return None
    batch["batch"]["status"] = "running"
    batch["warnings"].append(
        {"reason_code": "stale_batch_lock_recovered", "safe_message": "A stale batch lease was recovered."}
    )
    _save_batch(db, batch)
    return batch


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_datetime(value: Any) -> datetime:
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=None)
    except (TypeError, ValueError):
        return datetime.min


__all__ = [
    "MAX_SUCCESSFUL_TARGET",
    "OWNER_COACH_SYNC_BATCH_RESULT_SCHEMA_VERSION",
    "get_owner_coach_sync_batch",
    "latest_owner_coach_sync_batch",
    "run_owner_coach_sync_batch_step",
    "start_owner_coach_sync_batch",
]
