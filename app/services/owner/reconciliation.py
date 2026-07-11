"""Explicit owner identity reconciliation support."""

from __future__ import annotations

import json
from collections.abc import Iterable
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, inspect, text

DIRECT_OWNER_TABLES = (
    "steam_accounts",
    "import_jobs",
    "matches",
    "analysis_runs",
    "coach_hypotheses",
    "coach_missions",
    "mission_criteria",
    "mission_progress_evaluations",
    "coach_reports",
)
JSON_OWNER_TABLES = {
    "import_jobs": ("requested_payload_json", "result_json"),
    "matches": ("raw_json",),
    "analysis_runs": ("analysis_scope_json", "source_payload_json"),
    "coach_hypotheses": (
        "evidence_json",
        "mission_readiness_json",
        "source_card_json",
    ),
    "coach_missions": ("source_payload_json",),
    "mission_criteria": ("rule_json",),
    "mission_progress_evaluations": ("result_json", "caveats_json"),
    "coach_reports": ("report_json",),
}
ACCEPTED_IDENTITY_EVIDENCE = frozenset(
    {
        "legacy_created_by_pre_auth_steam_bootstrap",
        "canonical_only_active_credentialed_owner",
        "auth_introduced_after_legacy_creation",
        "legacy_has_no_credentials_or_login",
        "no_conflicting_owner_activity",
    }
)
LOCK_PREFIXES = ("lock:owner_coach_sync:", "lock:owner_coach_sync_batch:")
BATCH_PREFIX = "owner_coach_sync_batch:"


class OwnerReconciliationError(ValueError):
    pass


def reconcile_owner_identity(
    engine: Engine,
    *,
    legacy_user_id: int,
    canonical_user_id: int,
    identity_evidence: Iterable[str],
    apply: bool = False,
    confirm_identity_merge: bool = False,
    inject_failure_after: str | None = None,
) -> dict[str, Any]:
    evidence = sorted(set(identity_evidence))
    if legacy_user_id == canonical_user_id:
        raise OwnerReconciliationError("legacy_and_canonical_user_must_differ")
    unknown = sorted(set(evidence) - ACCEPTED_IDENTITY_EVIDENCE)
    if unknown:
        raise OwnerReconciliationError(f"unrecognized_identity_evidence:{','.join(unknown)}")
    if len(evidence) < 3:
        raise OwnerReconciliationError("identity_equivalence_unproven")
    if apply and not confirm_identity_merge:
        raise OwnerReconciliationError("apply_requires_confirm_identity_merge")

    with engine.connect() as connection:
        plan = _build_plan(connection, legacy_user_id, canonical_user_id, evidence)
    if not apply:
        return _public_plan(plan)
    if plan["refusals"]:
        raise OwnerReconciliationError(plan["refusals"][0])

    try:
        with engine.begin() as connection:
            _apply_plan(connection, plan, inject_failure_after=inject_failure_after)
            post = _build_plan(connection, legacy_user_id, canonical_user_id, evidence)
            invariants = _post_invariants(connection, legacy_user_id, canonical_user_id)
            if not all(invariants.values()):
                raise OwnerReconciliationError("post_migration_invariant_failed")
    except Exception:
        raise

    return {
        **_public_plan(post),
        "mode": "apply",
        "applied": True,
        "applied_summary": plan["migration_summary"],
        "post_invariants": invariants,
        "idempotent_noop": post["migration_summary"]["total_direct_rows"] == 0
        and post["migration_summary"]["total_json_rows"] == 0,
    }


def _public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    public = deepcopy(plan)
    for item in public["json_owner_changes"]:
        item.pop("changes", None)
    return public


def _build_plan(connection, legacy_user_id: int, canonical_user_id: int, evidence: list[str]) -> dict[str, Any]:
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    legacy = connection.execute(
        text(
            "SELECT id, email, password_hash, is_active, last_login_at, created_at "
            "FROM users WHERE id=:id"
        ),
        {"id": legacy_user_id},
    ).mappings().one_or_none()
    canonical = connection.execute(
        text(
            "SELECT id, email, password_hash, is_active, last_login_at, created_at "
            "FROM users WHERE id=:id"
        ),
        {"id": canonical_user_id},
    ).mappings().one_or_none()
    refusals: list[str] = []
    if legacy is None or canonical is None:
        refusals.append("owner_user_missing")
    elif not canonical["email"] or not canonical["password_hash"] or not canonical["is_active"]:
        refusals.append("canonical_user_not_active_credentialed_owner")
    elif legacy["email"] or legacy["password_hash"] or legacy["last_login_at"]:
        refusals.append("conflicting_auth_credentials")

    legacy_steam = _steam_rows(connection, legacy_user_id)
    canonical_steam = _steam_rows(connection, canonical_user_id)
    if not legacy_steam:
        if canonical_steam:
            pass  # already applied
        else:
            refusals.append("legacy_steam_account_missing")
    if canonical_steam and legacy_steam:
        if {row["steam_id"] for row in canonical_steam} != {row["steam_id"] for row in legacy_steam}:
            refusals.append("conflicting_steam_identities")
        else:
            refusals.append("duplicate_steam_identity_records")

    active_locks = _owner_locks(connection, legacy_user_id, canonical_user_id) if "app_settings" in tables else []
    if active_locks:
        refusals.append("owner_sync_lock_present")

    inventory: list[dict[str, Any]] = []
    total_direct = 0
    for table_name in DIRECT_OWNER_TABLES:
        if table_name not in tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "user_id" not in columns:
            continue
        rows = connection.execute(
            text(f'SELECT id FROM "{table_name}" WHERE user_id=:legacy ORDER BY id'),
            {"legacy": legacy_user_id},
        ).scalars().all()
        canonical_count = connection.execute(
            text(f'SELECT count(*) FROM "{table_name}" WHERE user_id=:canonical'),
            {"canonical": canonical_user_id},
        ).scalar_one()
        total_direct += len(rows)
        inventory.append(
            {
                "table": table_name,
                "owner_path": "user_id",
                "row_count": len(rows),
                "affected_id_range": [min(rows), max(rows)] if rows else None,
                "canonical_preexisting_count": canonical_count,
                "unique_constraints": _unique_constraints(inspector, table_name),
                "foreign_keys": _foreign_keys(inspector, table_name),
                "collision_risk": "checked" if canonical_count else "none_observed",
                "migration_action": f"set user_id={canonical_user_id}",
                "rollback_action": f"restore user_id={legacy_user_id} from verified backup",
            }
        )

    json_changes = _json_owner_changes(connection, tables, legacy_user_id, canonical_user_id)
    batch_states = _batch_states(connection, legacy_user_id, canonical_user_id) if "app_settings" in tables else []
    return {
        "schema_version": "owner-identity-reconciliation-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "dry_run",
        "applied": False,
        "identity": {
            "equivalence_proven": not refusals,
            "legacy_user_id": legacy_user_id,
            "canonical_user_id": canonical_user_id,
            "evidence": evidence,
            "legacy_has_credentials": bool(legacy and (legacy["email"] or legacy["password_hash"])),
            "canonical_is_active_credentialed": bool(
                canonical and canonical["email"] and canonical["password_hash"] and canonical["is_active"]
            ),
            "legacy_steam_ids_masked": [_mask_steam(row["steam_id"]) for row in legacy_steam],
            "canonical_steam_ids_masked": [_mask_steam(row["steam_id"]) for row in canonical_steam],
        },
        "inventory": inventory,
        "json_owner_changes": json_changes,
        "batch_states": batch_states,
        "active_owner_locks": active_locks,
        "migration_summary": {
            "total_direct_rows": total_direct,
            "total_json_rows": sum(item["row_count"] for item in json_changes),
            "legacy_user_retired": bool(legacy and legacy["is_active"]),
        },
        "refusals": sorted(set(refusals)),
        "rollback": "Stop writers and restore the verified pre-migration database backup.",
        "sanitized": True,
    }


def _apply_plan(connection, plan: dict[str, Any], *, inject_failure_after: str | None) -> None:
    legacy = plan["identity"]["legacy_user_id"]
    canonical = plan["identity"]["canonical_user_id"]
    for item in plan["inventory"]:
        if item["row_count"]:
            connection.execute(
                text(f'UPDATE "{item["table"]}" SET user_id=:canonical WHERE user_id=:legacy'),
                {"canonical": canonical, "legacy": legacy},
            )
        if inject_failure_after == item["table"]:
            raise RuntimeError("injected_owner_reconciliation_failure")
    for item in plan["json_owner_changes"]:
        pk = item["primary_key"]
        for row in item["changes"]:
            connection.execute(
                text(f'UPDATE "{item["table"]}" SET "{item["column"]}"=:value WHERE "{pk}"=:pk'),
                {"value": row["value"], "pk": row["pk"]},
            )
    connection.execute(text("UPDATE users SET is_active=0 WHERE id=:legacy"), {"legacy": legacy})


def _json_owner_changes(connection, tables: set[str], legacy: int, canonical: int) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    inspector = inspect(connection)
    for table_name, candidates in JSON_OWNER_TABLES.items():
        if table_name not in tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        pk_columns = inspector.get_pk_constraint(table_name).get("constrained_columns") or ["id"]
        pk = pk_columns[0]
        for column in candidates:
            if column not in columns:
                continue
            row_changes = []
            for row in connection.execute(
                text(f'SELECT "{pk}", "{column}" FROM "{table_name}" WHERE "{column}" IS NOT NULL')
            ):
                try:
                    payload = json.loads(row[1])
                except (TypeError, json.JSONDecodeError):
                    continue
                updated, changed = _replace_owner_refs(payload, legacy, canonical)
                if changed:
                    row_changes.append({"pk": row[0], "value": json.dumps(updated, ensure_ascii=False, sort_keys=True)})
            if row_changes:
                changes.append(
                    {
                        "table": table_name,
                        "column": column,
                        "primary_key": pk,
                        "row_count": len(row_changes),
                        "affected_id_range": [row_changes[0]["pk"], row_changes[-1]["pk"]],
                        "changes": row_changes,
                    }
                )
    if "app_settings" in tables:
        for key, value in connection.execute(
            text("SELECT key,value FROM app_settings WHERE key LIKE :prefix"), {"prefix": f"{BATCH_PREFIX}%"}
        ):
            try:
                payload = json.loads(value)
            except json.JSONDecodeError:
                continue
            updated, changed = _replace_owner_refs(payload, legacy, canonical)
            if changed:
                changes.append(
                    {
                        "table": "app_settings",
                        "column": "value",
                        "primary_key": "key",
                        "row_count": 1,
                        "affected_id_range": [key, key],
                        "changes": [{"pk": key, "value": json.dumps(updated, ensure_ascii=False, sort_keys=True)}],
                    }
                )
    return changes


def _replace_owner_refs(value: Any, legacy: int, canonical: int) -> tuple[Any, bool]:
    changed = False
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            if key in {"user_id", "owner_user_id"} and child == legacy:
                result[key] = canonical
                changed = True
            else:
                result[key], child_changed = _replace_owner_refs(child, legacy, canonical)
                changed = changed or child_changed
        return result, changed
    if isinstance(value, list):
        result = []
        for child in value:
            updated, child_changed = _replace_owner_refs(child, legacy, canonical)
            result.append(updated)
            changed = changed or child_changed
        return result, changed
    return value, False


def _post_invariants(connection, legacy: int, canonical: int) -> dict[str, bool]:
    inspector = inspect(connection)
    direct_legacy = 0
    for table_name in DIRECT_OWNER_TABLES:
        if table_name in inspector.get_table_names() and "user_id" in {
            column["name"] for column in inspector.get_columns(table_name)
        }:
            direct_legacy += connection.execute(
                text(f'SELECT count(*) FROM "{table_name}" WHERE user_id=:legacy'), {"legacy": legacy}
            ).scalar_one()
    steam_count = connection.execute(
        text("SELECT count(*) FROM steam_accounts WHERE user_id=:canonical"), {"canonical": canonical}
    ).scalar_one()
    fk_ok = not connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    active_locks = _owner_locks(connection, legacy, canonical)
    return {
        "legacy_owner_rows_zero": direct_legacy == 0,
        "canonical_has_one_steam_account": steam_count == 1,
        "legacy_user_inactive": connection.execute(
            text("SELECT is_active=0 FROM users WHERE id=:legacy"), {"legacy": legacy}
        ).scalar_one(),
        "foreign_keys_ok": fk_ok,
        "owner_locks_absent": not active_locks,
    }


def _steam_rows(connection, user_id: int) -> list[dict[str, Any]]:
    return list(
        connection.execute(
            text("SELECT id,steam_id FROM steam_accounts WHERE user_id=:user_id ORDER BY id"), {"user_id": user_id}
        ).mappings()
    )


def _owner_locks(connection, legacy: int, canonical: int) -> list[str]:
    keys = []
    for prefix in LOCK_PREFIXES:
        for user_id in (legacy, canonical):
            key = f"{prefix}{user_id}"
            if connection.execute(text("SELECT 1 FROM app_settings WHERE key=:key"), {"key": key}).first():
                keys.append(key)
    return keys


def _batch_states(connection, legacy: int, canonical: int) -> list[dict[str, Any]]:
    states = []
    for key, value in connection.execute(
        text("SELECT key,value FROM app_settings WHERE key LIKE :prefix ORDER BY key"), {"prefix": f"{BATCH_PREFIX}%"}
    ):
        try:
            batch = json.loads(value).get("batch", {})
        except (AttributeError, json.JSONDecodeError):
            continue
        if batch.get("owner_user_id") in {legacy, canonical}:
            states.append(
                {
                    "key": key,
                    "batch_id": batch.get("batch_id"),
                    "owner_user_id": batch.get("owner_user_id"),
                    "status": batch.get("status"),
                    "stop_reason": batch.get("stop_reason"),
                    "terminal": batch.get("status") not in {"queued", "running"},
                }
            )
    return states


def _unique_constraints(inspector, table_name: str) -> list[list[str]]:
    return [item.get("column_names") or [] for item in inspector.get_unique_constraints(table_name)]


def _foreign_keys(inspector, table_name: str) -> list[str]:
    return [
        f"{','.join(item.get('constrained_columns') or [])}->{item.get('referred_table')}"
        for item in inspector.get_foreign_keys(table_name)
    ]


def _mask_steam(value: str) -> str:
    return f"...{value[-6:]}"
