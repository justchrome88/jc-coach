from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import CoachMission, DemoParseArtifact, Match, MetricSnapshot, MissionProgressEvaluation
from app.services.metrics.coach_pack import (
    AIM_SOURCE,
    COACH_METRIC_SEMANTIC_VERSION,
    PERFORMANCE_SOURCE,
    UTILITY_SOURCE,
    calculate_coach_metric_pack,
    parse_coach_metric_evidence,
    store_coach_metric_pack,
    write_coach_metric_evidence_artifact,
)
from app.services.missions.hypotheses import build_rolling_mission_window, generate_rolling_mission_candidates
from app.services.missions.progress import evaluate_mission_progress
from app.services.missions.repository import add_mission_criteria, list_mission_criteria
from app.services.missions.types import EFFECTIVE_UTILITY_METRIC

OWNER_USER_ID = 17
OWNER_STEAM_ID = "76561198056634139"
MISSION_ID = 3
EXPECTED_SOURCES = {PERFORMANCE_SOURCE, UTILITY_SOURCE, AIM_SOURCE}


def owner_artifacts(db: Session) -> list[tuple[DemoParseArtifact, Match]]:
    match_ids = select(MetricSnapshot.match_id).where(
        MetricSnapshot.owner_user_id == OWNER_USER_ID,
        MetricSnapshot.semantic_version == "2.0.0",
    )
    rows = list(
        db.execute(
            select(DemoParseArtifact, Match)
            .join(Match, Match.id == DemoParseArtifact.match_id)
            .where(DemoParseArtifact.match_id.in_(match_ids))
            .order_by(DemoParseArtifact.match_id)
        ).all()
    )
    deduped: dict[int, tuple[DemoParseArtifact, Match]] = {}
    for artifact, match in rows:
        deduped[artifact.match_id] = (artifact, match)
    return list(deduped.values())


def resolve_demo(root: Path, artifact: DemoParseArtifact) -> Path:
    candidates = [
        Path(artifact.source_demo_file) if artifact.source_demo_file else None,
        root / "data/uploads/retained" / str(artifact.demo_sha1)[:2] / f"{artifact.demo_sha1}.dem",
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise FileNotFoundError(f"retained demo missing for match {artifact.match_id} sha1={artifact.demo_sha1}")


def run(
    database: Path,
    *,
    artifact_root: Path,
    apply: bool,
    rebind_mission: bool,
) -> dict[str, Any]:
    if rebind_mission:
        raise ValueError(
            "H01A-M04 mission rebind is retired by H01B-R01; utility_value is context-only and mission 3 is historical."
        )
    started = time.monotonic()
    engine = create_engine(f"sqlite:///{database.resolve()}", future=True)
    output: dict[str, Any] = {
        "database": str(database.resolve()),
        "mode": "apply" if apply else "dry_run",
        "owner_user_id": OWNER_USER_ID,
        "owner_steam_id": OWNER_STEAM_ID,
        "matches": [],
        "rows_before": 0,
        "rows_after": 0,
        "rows_appended": 0,
        "artifacts_written": 0,
        "mission_rebind": None,
    }
    with Session(engine) as db:
        output["rows_before"] = _snapshot_count(database)
        artifacts = owner_artifacts(db)
        if len(artifacts) != 55:
            raise ValueError(f"expected 55 retained owner parser artifacts, found {len(artifacts)}")
        for parser_artifact, match in artifacts:
            demo = resolve_demo(Path(__file__).resolve().parents[1], parser_artifact)
            evidence = parse_coach_metric_evidence(
                demo,
                match_id=match.id,
                owner_steamid=OWNER_STEAM_ID,
                demo_sha1=parser_artifact.demo_sha1,
                map_name=match.map_name,
            )
            result = calculate_coach_metric_pack(evidence)
            artifact_path = None
            existing_sources = set(
                db.scalars(
                    select(MetricSnapshot.source).where(
                        MetricSnapshot.owner_user_id == OWNER_USER_ID,
                        MetricSnapshot.match_id == match.id,
                        MetricSnapshot.player_key == result.player_key,
                        MetricSnapshot.semantic_version == COACH_METRIC_SEMANTIC_VERSION,
                        MetricSnapshot.source_event_set_id == result.event_set_id,
                    )
                ).all()
            )
            if apply:
                artifact_path = write_coach_metric_evidence_artifact(evidence, artifact_root)
                if existing_sources != EXPECTED_SOURCES:
                    output["artifacts_written"] += 1
                snapshots = store_coach_metric_pack(
                    db,
                    match_id=match.id,
                    owner_user_id=OWNER_USER_ID,
                    source_parser_artifact_id=parser_artifact.id,
                    result=result,
                    artifact_path=artifact_path,
                )
                if {snapshot.source for snapshot in snapshots} != EXPECTED_SOURCES:
                    raise ValueError(f"match {match.id}: incomplete v3 snapshot sources")
            output["matches"].append(
                {
                    "match_id": match.id,
                    "parser_artifact_id": parser_artifact.id,
                    "demo_sha1": parser_artifact.demo_sha1,
                    "event_set_id": result.event_set_id,
                    "existing_sources_before": sorted(existing_sources),
                    "pending_sources": sorted(EXPECTED_SOURCES - existing_sources),
                    "artifact_path": str(artifact_path) if artifact_path else None,
                    "rounds_played": result.performance["rounds_played"],
                    "effective_enemy_utility_damage": result.utility[EFFECTIVE_UTILITY_METRIC],
                    "adr": result.performance["adr"],
                    "kast": result.performance["kast"],
                }
            )
        if apply and rebind_mission:
            output["mission_rebind"] = rebind_active_mission(db)
        output["rows_after"] = _snapshot_count(database)
        output["rows_appended"] = output["rows_after"] - output["rows_before"]
        output["active_missions"] = len(
            list(db.scalars(select(CoachMission).where(CoachMission.status == "active")).all())
        )
        output["duplicate_v3_identities"] = _duplicate_v3_identities(database)
        output["foreign_key_violations"] = _foreign_key_violations(database)
        output["integrity_check"] = _integrity_check(database)
        match_124 = next(item for item in output["matches"] if item["match_id"] == 124)
        output["match_124"] = match_124
        if output["active_missions"] != 1:
            raise ValueError("production invariant failed: expected one active mission")
        if output["duplicate_v3_identities"]:
            raise ValueError("production invariant failed: duplicate v3 metric identities")
        if output["foreign_key_violations"] or output["integrity_check"] != "ok":
            raise ValueError("production invariant failed: SQLite integrity/FK")
    output["runtime_seconds"] = round(time.monotonic() - started, 3)
    return output


def rebind_active_mission(db: Session) -> dict[str, Any]:
    raise ValueError(
        "Retired by H01B-R01: utility_value is context-only and mission 3 must remain historical."
    )
    mission = db.get(CoachMission, MISSION_ID)
    if mission is None or mission.status != "active":
        raise ValueError("mission 3 is not the active mission")
    if mission.user_id != OWNER_USER_ID or mission.owner_steam_id != OWNER_STEAM_ID:
        raise ValueError("mission 3 owner/player mismatch")
    window = build_rolling_mission_window(
        db,
        user_id=OWNER_USER_ID,
        owner_steam_id=OWNER_STEAM_ID,
        window_type="last_30",
    )
    trend = window.utility_trend
    if not trend.evidence_available or trend.recent_value is None or trend.baseline_value is None:
        raise ValueError(f"validated utility trend unavailable: {trend.reason_codes}")
    # Equivalence is based on intended enemy utility health damage behavior. A
    # mission may stay active even when the historical trend no longer clears a
    # fresh-activation materiality gate; progress still compares the same two
    # owner segments under the corrected metric.
    current = list_mission_criteria(
        db,
        user_id=OWNER_USER_ID,
        mission_id=MISSION_ID,
        include_superseded=True,
    )
    active_v3 = [
        row
        for row in current
        if row.metric_name == EFFECTIVE_UTILITY_METRIC
        and _json(row.rule_json).get("metric_assurance", {}).get("semantic_version_required") == "3.0.0"
        and _json(row.rule_json).get("lifecycle", {}).get("state") != "superseded"
    ]
    changed = False
    if len(active_v3) != 2:
        for criteria in current:
            if criteria.metric_name != "utility_damage":
                continue
            rule = _json(criteria.rule_json)
            rule["lifecycle"] = {
                "state": "superseded",
                "superseded_by_metric": EFFECTIVE_UTILITY_METRIC,
                "superseded_by_semantic_version": "3.0.0",
                "task": "H01A-M04",
            }
            criteria.rule_json = json.dumps(rule, ensure_ascii=False, sort_keys=True)
        confidence_required = 0.9
        common_assurance = {
            "metric_key": EFFECTIVE_UTILITY_METRIC,
            "semantic_version_required": "3.0.0",
            "state": "validated",
            "reason_codes": ["explicit_enemy_team", "effective_health_cap", "real_demo_golden_corpus"],
        }
        add_mission_criteria(
            db,
            user_id=OWNER_USER_ID,
            mission_id=MISSION_ID,
            metric_name=EFFECTIVE_UTILITY_METRIC,
            role="primary",
            direction="higher_is_better",
            baseline_value=trend.recent_value,
            target_value=trend.baseline_value,
            min_sample_matches=3,
            confidence_required=confidence_required,
            rule={
                "source": "personal_effective_utility_negative_trend",
                "target_source": "preceding_personal_baseline_segment",
                "metric_assurance": common_assurance,
            },
        )
        add_mission_criteria(
            db,
            user_id=OWNER_USER_ID,
            mission_id=MISSION_ID,
            metric_name=EFFECTIVE_UTILITY_METRIC,
            role="guardrail",
            direction="stay_above",
            baseline_value=trend.recent_value,
            target_value=trend.recent_value,
            confidence_required=confidence_required,
            rule={
                "source": "recent_segment_deterioration_guardrail",
                "baseline_comparison": "do_not_drop_below_recent_personal_segment",
                "metric_assurance": common_assurance,
            },
        )
        changed = True

    source = _json(mission.source_payload_json)
    source["metric_rebind_history"] = {
        "task": "H01A-M04",
        "previous_metric_key": "utility_damage",
        "previous_semantic_state": "quarantined_legacy_ambiguous_enemy_team",
        "replacement_metric_key": EFFECTIVE_UTILITY_METRIC,
        "replacement_semantic_version": "3.0.0",
        "equivalence_decision": "accepted_enemy_utility_health_damage_behavior",
        "historical_criteria_ids": [row.id for row in current if row.metric_name == "utility_damage"],
    }
    source["metric_assurance"] = {
        "state": "validated",
        "hard_assurance_blocked": False,
        "validated_metric_keys": [EFFECTIVE_UTILITY_METRIC],
        "semantic_version_required": "3.0.0",
        "reconciled_by": "H01A-M04",
        "idempotency_key": "mission:3:coach-metric-pack:3.0.0",
    }
    mission_payload = dict(source.get("mission_payload") or {})
    mission_payload["goal"] = (
        f"Recover recent effective enemy utility damage from {trend.recent_value:.3f} toward the player's "
        f"preceding personal baseline of {trend.baseline_value:.3f} using validated v3 owner snapshots."
    )
    mission_payload["success_metric"] = {
        "metric_name": EFFECTIVE_UTILITY_METRIC,
        "direction": "higher_is_better",
        "baseline_value": trend.recent_value,
        "target_value": trend.baseline_value,
        "min_sample_matches": 3,
        "min_sample_rounds": None,
        "confidence_required": 0.9,
        "semantic_version": "3.0.0",
    }
    mission_payload["failure_condition"] = {
        "metric_name": EFFECTIVE_UTILITY_METRIC,
        "direction": "stay_above",
        "threshold_value": trend.recent_value,
        "reason": "Guardrail triggers below the validated recent personal effective-utility segment.",
        "semantic_version": "3.0.0",
    }
    mission_payload["rules"] = [
        "Measure recovery only with validated owner-scoped effective_enemy_utility_damage v3 observations.",
        "Recover toward the preceding personal baseline; do not treat an absolute value as universally good.",
        "Do not infer lineup quality, flash value, or tactical cause from utility health damage.",
    ]
    source["mission_payload"] = mission_payload
    source["legacy_mission_domain_key"] = "utility_value"
    source["mission_domain_key"] = None
    source["problem_key"] = None
    mission.source_payload_json = json.dumps(source, ensure_ascii=False, sort_keys=True)
    db.commit()

    active = list_mission_criteria(db, user_id=OWNER_USER_ID, mission_id=MISSION_ID)
    if len(active) != 2 or {row.metric_name for row in active} != {EFFECTIVE_UTILITY_METRIC}:
        raise ValueError("mission 3 rebind invariant failed")
    candidates = generate_rolling_mission_candidates(
        db,
        user_id=OWNER_USER_ID,
        owner_steam_id=OWNER_STEAM_ID,
        window_type="last_30",
    )
    progress = reconcile_three_match_progress(db)
    return {
        "changed": changed,
        "mission_id": MISSION_ID,
        "historical_criteria_ids": [row.id for row in current if row.metric_name == "utility_damage"],
        "active_criteria_ids": [row.id for row in active],
        "metric_key": EFFECTIVE_UTILITY_METRIC,
        "semantic_version": "3.0.0",
        "recent_value": trend.recent_value,
        "baseline_value": trend.baseline_value,
        "trend_deficiency_detected": trend.deficiency_detected,
        "trend_reason_codes": list(trend.reason_codes),
        "rolling_candidate_count": len(candidates["candidates"]),
        "progress_reconciliation": progress,
    }


def reconcile_three_match_progress(db: Session) -> dict[str, Any]:
    snapshots = list(
        db.scalars(
            select(MetricSnapshot)
            .join(Match, Match.id == MetricSnapshot.match_id)
            .where(
                MetricSnapshot.owner_user_id == OWNER_USER_ID,
                MetricSnapshot.player_steamid == OWNER_STEAM_ID,
                MetricSnapshot.source == UTILITY_SOURCE,
                MetricSnapshot.semantic_version == "3.0.0",
                MetricSnapshot.validation_status == "validated",
            )
            .order_by(Match.played_at.desc().nullslast(), Match.id.desc(), MetricSnapshot.id.desc())
            .limit(3)
        ).all()
    )
    if len(snapshots) != 3 or len({row.match_id for row in snapshots}) != 3:
        raise ValueError("three-match validated mission progress window unavailable")
    snapshot_ids = [row.id for row in snapshots]
    idempotency_key = "mission:3:v3-progress:" + ",".join(str(value) for value in sorted(snapshot_ids))
    existing = list(
        db.scalars(
            select(MissionProgressEvaluation)
            .where(MissionProgressEvaluation.mission_id == MISSION_ID)
            .order_by(MissionProgressEvaluation.id.desc())
        ).all()
    )
    for evaluation in existing:
        result = _json(evaluation.result_json)
        if _json_object(result.get("metric_assurance")).get("idempotency_key") == idempotency_key:
            return {
                "changed": False,
                "evaluation_id": evaluation.id,
                "snapshot_ids": snapshot_ids,
                "match_ids": [row.match_id for row in snapshots],
                "status": evaluation.status,
                "idempotency_key": idempotency_key,
            }
    evaluation = evaluate_mission_progress(
        db,
        user_id=OWNER_USER_ID,
        mission_id=MISSION_ID,
        evaluation_metric_snapshots=snapshots,
        evaluation_window={
            "type": "validated_three_match_v3",
            "match_ids": [row.match_id for row in snapshots],
            "semantic_version": "3.0.0",
        },
    )
    result = _json(evaluation.result_json)
    result["metric_assurance"] = {
        "idempotency_key": idempotency_key,
        "metric_key": EFFECTIVE_UTILITY_METRIC,
        "semantic_version": "3.0.0",
        "validation_status": "validated",
        "snapshot_ids": snapshot_ids,
    }
    evaluation.result_json = json.dumps(result, ensure_ascii=False, sort_keys=True)
    db.commit()
    return {
        "changed": True,
        "evaluation_id": evaluation.id,
        "snapshot_ids": snapshot_ids,
        "match_ids": [row.match_id for row in snapshots],
        "status": evaluation.status,
        "idempotency_key": idempotency_key,
    }


def _snapshot_count(database: Path) -> int:
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        return int(connection.execute("SELECT count(*) FROM metric_snapshots").fetchone()[0])


def _duplicate_v3_identities(database: Path) -> list[tuple[Any, ...]]:
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        return connection.execute(
            """
            SELECT owner_user_id,match_id,player_key,metric_domain,semantic_version,source,source_event_set_id,count(*)
            FROM metric_snapshots WHERE semantic_version='3.0.0'
            GROUP BY owner_user_id,match_id,player_key,metric_domain,semantic_version,source,source_event_set_id
            HAVING count(*) > 1
            """
        ).fetchall()


def _foreign_key_violations(database: Path) -> list[tuple[Any, ...]]:
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        return connection.execute("PRAGMA foreign_key_check").fetchall()


def _integrity_check(database: Path) -> str:
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        return str(connection.execute("PRAGMA integrity_check").fetchone()[0])


def _json(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    return parsed if isinstance(parsed, dict) else {}


def _json_object(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rebind-mission", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.rebind_mission and not args.apply:
        raise SystemExit("--rebind-mission requires --apply")
    result = run(
        args.database,
        artifact_root=args.artifact_root,
        apply=args.apply,
        rebind_mission=args.rebind_mission,
    )
    encoded = json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
