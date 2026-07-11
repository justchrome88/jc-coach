#!/usr/bin/env python3
"""Plan and apply the H01A-M03 owner-only metric v2 backfill.

This command consumes retained parser artifacts only. It never invokes a parser,
imports matches, or runs the coach loop. Production use requires the same explicit
M03 authorization guard as the schema migration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.models import (  # noqa: E402
    AnalysisRun,
    CoachHypothesis,
    CoachMission,
    DemoParseArtifact,
    Match,
    MetricSnapshot,
    MissionCriteria,
    MissionProgressEvaluation,
    SteamAccount,
)
from app.services.core_combat_metrics import (  # noqa: E402
    CORE_COMBAT_METRICS_VERSION,
    CORE_COMBAT_SEMANTIC_VERSION,
    CORE_COMBAT_SNAPSHOT_SOURCE,
    CoreCombatMetricsResult,
    calculate_core_combat_metrics,
)
from app.services.metric_downstream_state import (  # noqa: E402
    MATCH_124_DISPOSITIONS,
    DownstreamDisposition,
    stale_evidence_marker,
)
from app.services.metric_snapshots import upsert_metric_snapshot  # noqa: E402
from app.services.parser_artifact_reader import normalized_events_from_parser_artifact  # noqa: E402
from app.services.utility_metrics import (  # noqa: E402
    UTILITY_METRICS_VERSION,
    UTILITY_SEMANTIC_VERSION,
    UTILITY_SNAPSHOT_SOURCE,
    UtilityMetricsResult,
    calculate_utility_metrics,
)

PRODUCTION_DB = (ROOT / "data/cs2_coach.db").resolve()
OWNER_USER_ID = 17
ACCEPTED_ARTIFACT_STATUSES = {"completed", "accepted", "success", "parsed"}
DOMAIN_SPECS = (
    ("core_combat", CORE_COMBAT_SNAPSHOT_SOURCE, CORE_COMBAT_SEMANTIC_VERSION, CORE_COMBAT_METRICS_VERSION),
    ("utility", UTILITY_SNAPSHOT_SOURCE, UTILITY_SEMANTIC_VERSION, UTILITY_METRICS_VERSION),
)


def _json_load(raw: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError("expected JSON object")
    return value


def _event_set_id(artifact: DemoParseArtifact, events: Sequence[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256(
        json.dumps(list(events), ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return f"parser-artifact:{artifact.id}:events:{digest}"


def _owner_result(results: Sequence[Any], player_key: str) -> Any:
    matches = [result for result in results if result.player_key == player_key]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one owner result for {player_key}; found {len(matches)}")
    return matches[0]


def _validation_sets(result: CoreCombatMetricsResult | UtilityMetricsResult) -> tuple[list[str], list[str]]:
    validation = result.metadata.get("metric_validation")
    if not isinstance(validation, Mapping):
        raise RuntimeError("metric result lacks per-key validation map")
    validated = sorted(
        str(key) for key, record in validation.items()
        if isinstance(record, Mapping) and record.get("status") == "validated"
    )
    quarantined = sorted(
        str(key) for key, record in validation.items()
        if isinstance(record, Mapping) and record.get("status") != "validated"
    )
    return validated, quarantined


def build_plan(db: Session, *, owner_user_id: int) -> dict[str, Any]:
    columns = {row[1] for row in db.connection().exec_driver_sql("PRAGMA table_info(metric_snapshots)")}
    if "semantic_version" not in columns:
        raise RuntimeError("metric snapshot v2 schema migration must be applied before planning")
    account = db.scalar(
        select(SteamAccount).where(SteamAccount.user_id == owner_user_id).order_by(SteamAccount.id)
    )
    if account is None:
        raise RuntimeError(f"owner {owner_user_id} has no linked Steam account")
    player_key = f"steam:{account.steam_id}"
    rows = db.execute(
        select(Match, DemoParseArtifact)
        .join(DemoParseArtifact, DemoParseArtifact.match_id == Match.id)
        .where(Match.user_id == owner_user_id)
        .order_by(Match.id)
    ).all()
    plan_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for match, artifact in rows:
        if artifact.status not in ACCEPTED_ARTIFACT_STATUSES:
            errors.append(f"match {match.id}: parser artifact {artifact.id} status {artifact.status!r} is not accepted")
            continue
        events = normalized_events_from_parser_artifact(artifact)
        normalization_fingerprint = _event_set_id(artifact, events)
        results_by_domain = {
            "core_combat": _owner_result(calculate_core_combat_metrics(events), player_key),
            "utility": _owner_result(calculate_utility_metrics(events), player_key),
        }
        for domain, source, version, implementation in DOMAIN_SPECS:
            legacy = list(db.scalars(
                select(MetricSnapshot)
                .where(MetricSnapshot.match_id == match.id)
                .where(MetricSnapshot.player_key == player_key)
                .where(MetricSnapshot.source == source)
                .where(MetricSnapshot.semantic_version == "1.0.0")
            ).all())
            if len(legacy) != 1:
                errors.append(f"match {match.id}/{domain}: expected one owner legacy snapshot; found {len(legacy)}")
                continue
            old = legacy[0]
            retained_event_set_id = old.source_event_set_id
            if (
                old.source_parser_artifact_id != artifact.id
                or not retained_event_set_id
                or not retained_event_set_id.startswith(f"parser-artifact:{artifact.id}:events:")
            ):
                errors.append(f"match {match.id}/{domain}: retained artifact/event-set lineage mismatch")
                continue
            existing = list(db.scalars(
                select(MetricSnapshot)
                .where(MetricSnapshot.owner_user_id == owner_user_id)
                .where(MetricSnapshot.match_id == match.id)
                .where(MetricSnapshot.player_key == player_key)
                .where(MetricSnapshot.metric_domain == domain)
                .where(MetricSnapshot.semantic_version == version)
                .where(MetricSnapshot.source == source)
                .where(MetricSnapshot.source_event_set_id == retained_event_set_id)
            ).all())
            if len(existing) > 1:
                errors.append(f"match {match.id}/{domain}: duplicate v2 semantic identity")
                continue
            result = results_by_domain[domain]
            validated, quarantined = _validation_sets(result)
            plan_rows.append({
                "owner_user_id": owner_user_id,
                "match_id": match.id,
                "player_key": player_key,
                "player_steamid": account.steam_id,
                "domain": domain,
                "source_parser_artifact_id": artifact.id,
                "source_parser_name": artifact.parser_name,
                "source_parser_version": artifact.parser_version,
                "source_event_set_id": retained_event_set_id,
                "current_normalization_fingerprint": normalization_fingerprint,
                "old_snapshot_id": old.id,
                "old_semantic_version": old.semantic_version,
                "old_validation_status": old.validation_status,
                "planned_semantic_version": version,
                "planned_validation_status": "validated",
                "implementation_version": implementation,
                "validated_keys": validated,
                "quarantined_keys": quarantined,
                "input_event_hash": result.metadata.get("input_event_hash"),
                "normalized_event_count": len(events),
                "idempotency_identity": (
                    f"{owner_user_id}:{match.id}:{player_key}:{domain}:{version}:{source}:{retained_event_set_id}"
                ),
                "existing_v2_snapshot_id": existing[0].id if existing else None,
            })
    identities = [row["idempotency_identity"] for row in plan_rows]
    if len(identities) != len(set(identities)):
        errors.append("duplicate v2 identities in plan")
    match_ids = sorted({int(row["match_id"]) for row in plan_rows})
    for match_id in match_ids:
        event_sets = {row["source_event_set_id"] for row in plan_rows if row["match_id"] == match_id}
        if len(event_sets) != 1:
            errors.append(f"match {match_id}: domain event-set lineage mismatch")
    pending = [row for row in plan_rows if row["existing_v2_snapshot_id"] is None]
    if len(plan_rows) != len(rows) * len(DOMAIN_SPECS):
        errors.append(f"plan row mismatch: expected {len(rows) * len(DOMAIN_SPECS)}, got {len(plan_rows)}")
    return {
        "status": "ready" if not errors else "blocked",
        "owner_user_id": owner_user_id,
        "owner_account_id": account.id,
        "owner_steam_id": account.steam_id,
        "player_key": player_key,
        "owner_match_count": len(rows),
        "planned_row_count": len(plan_rows),
        "pending_row_count": len(pending),
        "existing_v2_row_count": len(plan_rows) - len(pending),
        "parser_rerun_required": False,
        "match_ids": match_ids,
        "rows": plan_rows,
        "errors": errors,
    }


def _result_for_row(artifact: DemoParseArtifact, player_key: str, domain: str) -> Any:
    events = normalized_events_from_parser_artifact(artifact)
    results = calculate_core_combat_metrics(events) if domain == "core_combat" else calculate_utility_metrics(events)
    return _owner_result(results, player_key)


def _append_pending_rows(db: Session, plan: Mapping[str, Any]) -> list[int]:
    created: list[int] = []
    for row in plan["rows"]:
        if row.get("existing_v2_snapshot_id") is not None:
            continue
        artifact = db.get(DemoParseArtifact, int(row["source_parser_artifact_id"]))
        if artifact is None:
            raise RuntimeError(f"parser artifact disappeared: {row['source_parser_artifact_id']}")
        result = _result_for_row(artifact, str(row["player_key"]), str(row["domain"]))
        snapshot = upsert_metric_snapshot(
            db,
            owner_user_id=int(row["owner_user_id"]),
            match_id=int(row["match_id"]),
            player_key=result.player_key,
            player_name=result.player_name,
            player_steamid=result.player_steamid,
            source=(CORE_COMBAT_SNAPSHOT_SOURCE if row["domain"] == "core_combat" else UTILITY_SNAPSHOT_SOURCE),
            metric_domain=str(row["domain"]),
            semantic_version="2.0.0",
            scope="player_match",
            validation_status="validated",
            implementation_version=str(row["implementation_version"]),
            source_parser_artifact_id=artifact.id,
            source_event_set_id=str(row["source_event_set_id"]),
            metrics=result.metrics,
            confidence_baseline=result.confidence_baseline,
            caveats=result.caveats,
            metadata=result.metadata,
            input_event_hash=str(row["input_event_hash"]),
        )
        created.append(snapshot.id)
    return created


def _marked_payload(raw: str, disposition: DownstreamDisposition, **extra: Any) -> str:
    value = stale_evidence_marker(_json_load(raw), disposition)
    value["metric_assurance"].update(extra)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _assign_if_changed(target: Any, field: str, value: str) -> bool:
    if getattr(target, field) == value:
        return False
    setattr(target, field, value)
    return True


def reconcile_downstream(db: Session) -> dict[str, Any]:
    replacements = {
        "core_combat": db.scalar(
            select(MetricSnapshot).where(
                MetricSnapshot.owner_user_id == OWNER_USER_ID,
                MetricSnapshot.match_id == 124,
                MetricSnapshot.player_key == "steam:76561198056634139",
                MetricSnapshot.metric_domain == "core_combat",
                MetricSnapshot.semantic_version == "2.0.0",
            )
        ),
        "utility": db.scalar(
            select(MetricSnapshot).where(
                MetricSnapshot.owner_user_id == OWNER_USER_ID,
                MetricSnapshot.match_id == 124,
                MetricSnapshot.player_key == "steam:76561198056634139",
                MetricSnapshot.metric_domain == "utility",
                MetricSnapshot.semantic_version == "2.0.0",
            )
        ),
    }
    if any(snapshot is None for snapshot in replacements.values()):
        raise RuntimeError("match 124 v2 replacements are missing")
    updated: list[str] = []
    for disposition in MATCH_124_DISPOSITIONS:
        obj: Any
        field: str
        extra: dict[str, Any] = {"reconciled_by": "H01A-M03"}
        if disposition.object_type == "metric_snapshot":
            obj = db.get(MetricSnapshot, disposition.object_id)
            field = "metadata_json"
            domain = "core_combat" if disposition.object_id == 1138 else "utility"
            extra["replacement_snapshot_id"] = replacements[domain].id
        elif disposition.object_type == "analysis_run":
            obj = db.get(AnalysisRun, disposition.object_id)
            field = "source_payload_json"
            extra["replacement_snapshot_ids"] = [replacements["core_combat"].id, replacements["utility"].id]
            extra["replacement_created"] = False
        elif disposition.object_type == "coach_hypothesis":
            obj = db.get(CoachHypothesis, disposition.object_id)
            field = "source_card_json"
            extra["replacement_created"] = False
        elif disposition.object_type == "coach_mission":
            obj = db.get(CoachMission, disposition.object_id)
            field = "source_payload_json"
            extra.update({"hard_assurance_blocked": True, "blocking_metric_keys": ["utility_damage"]})
        else:
            obj = db.get(MissionProgressEvaluation, disposition.object_id)
            field = "result_json"
            extra.update({"replacement_created": False, "reason": "insufficient_validated_metric_data"})
        if obj is None:
            raise RuntimeError(f"missing downstream object {disposition.object_type}/{disposition.object_id}")
        if _assign_if_changed(obj, field, _marked_payload(getattr(obj, field), disposition, **extra)):
            updated.append(f"{disposition.object_type}:{disposition.object_id}")
    for criterion in db.scalars(select(MissionCriteria).where(MissionCriteria.mission_id == 3)).all():
        rule = _json_load(criterion.rule_json)
        marker = dict(rule.get("metric_assurance") or {})
        marker.update({
            "state": "quarantined",
            "semantic_version_required": "2.0.0",
            "metric_key": criterion.metric_name,
            "reason_codes": ["legacy_ambiguous_enemy_team_semantics"],
        })
        rule["metric_assurance"] = marker
        encoded = json.dumps(rule, ensure_ascii=False, sort_keys=True)
        if _assign_if_changed(criterion, "rule_json", encoded):
            updated.append(f"mission_criterion:{criterion.id}")
    if updated:
        db.commit()
    return {
        "updated_objects": updated,
        "updated_count": len(updated),
        "match_124_replacement_snapshot_ids": {
            key: snapshot.id for key, snapshot in replacements.items()
        },
    }


def _post_apply_checks(db: Session, plan: Mapping[str, Any], *, pre_count: int) -> dict[str, Any]:
    post_plan = build_plan(db, owner_user_id=int(plan["owner_user_id"]))
    post_count = db.scalar(select(MetricSnapshot.id).order_by(MetricSnapshot.id.desc()).limit(1))
    total = db.query(MetricSnapshot).count()
    duplicates = db.connection().exec_driver_sql(
        """SELECT COUNT(*) FROM (
        SELECT owner_user_id,match_id,player_key,metric_domain,semantic_version,source,source_event_set_id,COUNT(*) c
        FROM metric_snapshots WHERE semantic_version='2.0.0'
        GROUP BY owner_user_id,match_id,player_key,metric_domain,semantic_version,source,source_event_set_id
        HAVING c > 1)"""
    ).scalar_one()
    active_missions = db.connection().exec_driver_sql(
        "SELECT COUNT(*) FROM coach_missions WHERE status='active'"
    ).scalar_one()
    integrity = db.connection().exec_driver_sql("PRAGMA integrity_check").scalar_one()
    fk_rows = db.connection().exec_driver_sql("PRAGMA foreign_key_check").all()
    expected_total = pre_count + int(plan["pending_row_count"])
    return {
        "snapshot_count": total,
        "max_snapshot_id": post_count,
        "expected_snapshot_count": expected_total,
        "pending_row_count": post_plan["pending_row_count"],
        "duplicate_v2_identity_count": duplicates,
        "active_mission_count": active_missions,
        "integrity_check": integrity,
        "foreign_key_check_rows": len(fk_rows),
        "pass": (
            total == expected_total
            and post_plan["pending_row_count"] == 0
            and duplicates == 0
            and active_missions == 1
            and integrity == "ok"
            and not fk_rows
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--mode", choices=("plan", "apply"), required=True)
    parser.add_argument("--owner-user-id", type=int, default=OWNER_USER_ID)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-production", action="store_true")
    args = parser.parse_args()
    database = args.database.resolve()
    if database == PRODUCTION_DB and not (
        args.allow_production and os.environ.get("H01A_M03_PRODUCTION_AUTHORIZED") == "YES"
    ):
        raise SystemExit("production metric backfill is forbidden without explicit M03 authorization")
    if not database.exists():
        raise SystemExit(f"database does not exist: {database}")
    engine = create_engine(f"sqlite:///{database}", future=True)
    with Session(engine) as db:
        plan = build_plan(db, owner_user_id=args.owner_user_id)
        if plan["status"] != "ready":
            result = {"mode": args.mode, "plan": plan, "status": "blocked"}
        elif args.mode == "plan":
            result = {"mode": "plan", "plan": plan, "status": "ready"}
        else:
            pre_count = db.query(MetricSnapshot).count()
            created = _append_pending_rows(db, plan)
            reconciliation = reconcile_downstream(db)
            checks = _post_apply_checks(db, plan, pre_count=pre_count)
            result = {
                "mode": "apply",
                "plan": plan,
                "created_snapshot_ids": created,
                "created_snapshot_count": len(created),
                "downstream_reconciliation": reconciliation,
                "checks": checks,
                "status": "pass" if checks["pass"] else "failed",
            }
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n")
    print(encoded)
    return 0 if result["status"] in {"ready", "pass"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
