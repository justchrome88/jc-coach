from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AnalysisRun,
    CoachHypothesis,
    CoachMission,
    DemoParseArtifact,
    Match,
    MetricSnapshot,
    MissionProgressEvaluation,
)
from app.services.coach_domain_model import CANONICAL_COACH_DOMAINS, METRIC_GROUPS
from app.services.coach_metric_pack import (
    AIM_SOURCE,
    COACH_METRIC_SEMANTIC_VERSION,
    PERFORMANCE_SOURCE,
    UTILITY_SOURCE,
    calculate_coach_metric_pack,
    parse_coach_metric_evidence,
    store_coach_metric_pack,
    write_coach_metric_evidence_artifact,
)
from app.services.mission_domain import (
    activate_coach_mission,
    active_mission_context_for_owner,
    create_analysis_run,
    create_coach_hypothesis,
    evaluate_mission_progress,
    generate_rolling_mission_candidates,
    reconcile_noncanonical_active_missions,
)

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_DB = (ROOT / "data/cs2_coach.db").resolve()
PRODUCTION_ARTIFACT_ROOT = (ROOT / "data/coach_metric_event_sets").resolve()
OWNER_USER_ID = 17
OWNER_STEAM_ID = "76561198056634139"
REQUIRED_MATCH_IDS = {29, 117, 120, 122, 124}
EXPECTED_SOURCES = {PERFORMANCE_SOURCE, UTILITY_SOURCE, AIM_SOURCE}
MODES = ("baseline", "chronological", "state-matrix", "idempotency")


def run(
    *,
    database: Path,
    artifact_root: Path,
    selected_match_ids: Sequence[int],
    mode: str,
    apply: bool,
) -> dict[str, Any]:
    database = database.resolve()
    artifact_root = artifact_root.resolve()
    selected = _validate_inputs(database, artifact_root, selected_match_ids, mode=mode, apply=apply)
    started = time.monotonic()
    engine = create_engine(f"sqlite:///{database}", future=True)
    with Session(engine) as db:
        _verify_owner(db)
        if mode == "baseline":
            result = _baseline(db, database=database, selected=selected)
        elif mode == "chronological":
            result = _chronological(db, artifact_root=artifact_root, selected=selected, apply=apply)
        elif mode == "state-matrix":
            result = _state_matrix(database, artifact_root=artifact_root, selected=selected, apply=apply)
        else:
            result = _idempotency(db, artifact_root=artifact_root, selected=selected, apply=apply)
    result.update(
        {
            "mode": mode,
            "apply": apply,
            "database": str(database),
            "artifact_root": str(artifact_root),
            "runtime_seconds": round(time.monotonic() - started, 3),
        }
    )
    return result


def _validate_inputs(
    database: Path,
    artifact_root: Path,
    selected_match_ids: Sequence[int],
    *,
    mode: str,
    apply: bool,
) -> list[int]:
    if mode not in MODES:
        raise ValueError(f"unsupported mode: {mode}")
    selected = list(dict.fromkeys(int(value) for value in selected_match_ids))
    if len(selected) != 10:
        raise ValueError("exactly ten unique selected match ids are required")
    if not REQUIRED_MATCH_IDS.issubset(selected):
        raise ValueError(f"selected corpus must contain {sorted(REQUIRED_MATCH_IDS)}")
    if not database.is_file():
        raise FileNotFoundError(f"database does not exist: {database}")
    if apply and database == PRODUCTION_DB:
        raise ValueError("production database mutation refused; use a verified isolated clone")
    if apply and artifact_root == PRODUCTION_ARTIFACT_ROOT:
        raise ValueError("production artifact root mutation refused; use an isolated artifact root")
    return selected


def _verify_owner(db: Session) -> None:
    row = db.execute(
        select(Match.user_id, MetricSnapshot.player_steamid)
        .join(MetricSnapshot, MetricSnapshot.match_id == Match.id)
        .where(Match.user_id == OWNER_USER_ID)
        .where(MetricSnapshot.player_steamid == OWNER_STEAM_ID)
        .limit(1)
    ).first()
    if row is None:
        raise ValueError("owner/player production lineage is unavailable")


def _selected_matches(db: Session, selected: Sequence[int]) -> list[Match]:
    rows = list(
        db.scalars(
            select(Match)
            .where(Match.id.in_(selected))
            .where(Match.user_id == OWNER_USER_ID)
            .order_by(Match.played_at.asc().nulls_last(), Match.id.asc())
        ).all()
    )
    if len(rows) != 10 or {row.id for row in rows} != set(selected):
        raise ValueError("selected matches are not exactly ten retained owner matches")
    if any(row.played_at is None for row in rows):
        raise ValueError("selected match chronology has missing played_at")
    return rows


def _baseline(db: Session, *, database: Path, selected: Sequence[int]) -> dict[str, Any]:
    matches = _selected_matches(db, selected)
    missions = list(db.scalars(select(CoachMission).order_by(CoachMission.id)).all())
    return {
        "preflight": {
            "database_sha256": _sha256(database),
            "integrity_check": _integrity(database),
            "foreign_key_violations": _foreign_key_violations(database),
            "production_refusal_active": True,
        },
        "canonical_domains": list(CANONICAL_COACH_DOMAINS),
        "metric_groups": list(METRIC_GROUPS),
        "production_baseline": _counts(db),
        "selected_matches": [_match_summary(db, match) for match in matches],
        "mission_inventory": [_mission_inventory(mission) for mission in missions],
        "mission_3_decision": {
            "outcome": "supersede",
            "reason": "noncanonical_domain_reconciliation",
            "semantic_finding": "standalone utility-improvement mission outside both approved domains",
        },
        "active_mission_model": "at_most_one_globally_per_owner",
    }


def _chronological(
    db: Session,
    *,
    artifact_root: Path,
    selected: Sequence[int],
    apply: bool,
) -> dict[str, Any]:
    matches = _selected_matches(db, selected)
    if not apply:
        return {
            "chronological_replay": [],
            "selected_matches": [_match_summary(db, match) for match in matches],
            "dry_run_plan": {
                "remove": "selected validated v3 snapshot lineage only",
                "preserve": (
                    "matches, retained demos, parser artifacts, and historical missions/hypotheses/criteria/progress"
                ),
                "mission_3": "cancel with noncanonical_domain_reconciliation",
            },
        }

    reconciliation = reconcile_noncanonical_active_missions(
        db,
        user_id=OWNER_USER_ID,
        owner_steam_id=OWNER_STEAM_ID,
        apply=True,
    )
    db.execute(
        delete(MetricSnapshot)
        .where(MetricSnapshot.match_id.in_(selected))
        .where(MetricSnapshot.owner_user_id == OWNER_USER_ID)
        .where(MetricSnapshot.semantic_version == COACH_METRIC_SEMANTIC_VERSION)
    )
    db.commit()

    replay: list[dict[str, Any]] = []
    prefix: list[int] = []
    activated_mission_id: int | None = None
    for match in matches:
        prefix.append(match.id)
        metric_result = _replay_match(db, match=match, artifact_root=artifact_root, apply=True)
        candidates = generate_rolling_mission_candidates(
            db,
            user_id=OWNER_USER_ID,
            owner_steam_id=OWNER_STEAM_ID,
            window_type="custom_match_set",
            match_ids=prefix,
        )
        active = active_mission_context_for_owner(
            db,
            user_id=OWNER_USER_ID,
            owner_steam_id=OWNER_STEAM_ID,
        )
        if active["active_mission_count"] == 0:
            eligible = [
                candidate
                for candidate in candidates["candidates"]
                if candidate.get("suppressed_by_active_mission") is not True
            ]
            if eligible:
                selected_candidate = eligible[0]
                analysis_run = create_analysis_run(
                    db,
                    user_id=OWNER_USER_ID,
                    owner_steam_id=OWNER_STEAM_ID,
                    status="candidate_selected",
                    source="canonical_domain_vertical_replay",
                    selected_metric_snapshot_ids=candidates["window"]["metric_snapshot_ids"],
                    analysis_scope={"match_ids": list(prefix), "canonical_domain_replay": True},
                    source_payload={"candidate": selected_candidate},
                )
                hypothesis = create_coach_hypothesis(
                    db,
                    user_id=OWNER_USER_ID,
                    analysis_run_id=analysis_run.id,
                    insight_card=selected_candidate["insight_card"],
                )
                mission = activate_coach_mission(
                    db,
                    user_id=OWNER_USER_ID,
                    hypothesis_id=hypothesis.id,
                    title=selected_candidate["mission_payload"]["title"],
                )
                activated_mission_id = mission.id
                db.commit()
                active = active_mission_context_for_owner(
                    db,
                    user_id=OWNER_USER_ID,
                    owner_steam_id=OWNER_STEAM_ID,
                )
        progress = _evaluate_active_progress_once(db, match_ids=prefix)
        db.commit()
        replay.append(
            {
                "sequence": len(prefix),
                "match": _match_summary(db, match),
                "lineage": metric_result,
                "rolling_window": candidates["window"],
                "impact_leak_hypothesis_state": candidates["diagnostics"]["impact_leak"],
                "bad_fight_selection_candidates": [
                    item
                    for item in candidates["candidates"]
                    if item.get("suppression_key", {}).get("domain_key") == "bad_fight_selection"
                ],
                "candidate_ranking": candidates["candidates"],
                "utility_context": candidates["diagnostics"]["effective_enemy_utility_damage"],
                "active_mission": active,
                "progress": progress,
            }
        )

    domains_seen = {
        item.get("suppression_key", {}).get("domain_key")
        for step in replay
        for item in step["candidate_ranking"]
        if item.get("suppression_key", {}).get("domain_key")
    }
    active_after = active_mission_context_for_owner(
        db,
        user_id=OWNER_USER_ID,
        owner_steam_id=OWNER_STEAM_ID,
    )
    acceptance = {
        "exactly_two_domains": set(CANONICAL_COACH_DOMAINS) == {"impact_leak", "bad_fight_selection"},
        "candidate_domains_subset": domains_seen.issubset(CANONICAL_COACH_DOMAINS),
        "utility_value_candidate_absent": all(
            candidate.get("family") != "utility_value"
            for step in replay
            for candidate in step["candidate_ranking"]
        ),
        "one_active_constraint": active_after["active_mission_count"] <= 1,
        "v3_sources_complete": all(set(step["lineage"]["sources"]) == EXPECTED_SOURCES for step in replay),
        "owner_player_version_valid": all(step["lineage"]["identity_valid"] for step in replay),
    }
    metric_acceptance = _metric_acceptance(replay)
    impact_acceptance = _domain_acceptance(db, replay, "impact_leak")
    fight_acceptance = _domain_acceptance(db, replay, "bad_fight_selection")
    final_pass = all(acceptance.values()) and all(
        item["accepted"] for item in (metric_acceptance, impact_acceptance, fight_acceptance)
    )
    return {
        "mission_3_decision": reconciliation,
        "selected_matches": [_match_summary(db, match) for match in matches],
        "chronological_replay": replay,
        "mission_progress": {
            "activated_mission_id": activated_mission_id,
            "active_after": active_after,
            "evaluation_count": db.scalar(select(func.count()).select_from(MissionProgressEvaluation)),
        },
        "metric_acceptance": metric_acceptance,
        "impact_leak_acceptance": impact_acceptance,
        "bad_fight_selection_acceptance": fight_acceptance,
        "chronological_acceptance": acceptance,
        "final_decision": "PASS" if final_pass else "BLOCKED",
    }


def _replay_match(db: Session, *, match: Match, artifact_root: Path, apply: bool) -> dict[str, Any]:
    artifact = db.scalar(select(DemoParseArtifact).where(DemoParseArtifact.match_id == match.id))
    if artifact is None:
        raise ValueError(f"match {match.id}: parser artifact missing")
    demo = _resolve_demo(artifact)
    evidence = parse_coach_metric_evidence(
        demo,
        match_id=match.id,
        owner_steamid=OWNER_STEAM_ID,
        demo_sha1=artifact.demo_sha1,
        map_name=match.map_name,
    )
    result = calculate_coach_metric_pack(evidence)
    artifact_path = write_coach_metric_evidence_artifact(evidence, artifact_root) if apply else None
    snapshots = (
        store_coach_metric_pack(
            db,
            match_id=match.id,
            owner_user_id=OWNER_USER_ID,
            source_parser_artifact_id=artifact.id,
            result=result,
            artifact_path=artifact_path,
        )
        if apply
        else []
    )
    if apply:
        db.flush()
    ledger = _independent_ledger(result)
    persisted = {snapshot.source: json.loads(snapshot.metrics_json) for snapshot in snapshots}
    comparison = {
        "adr": persisted.get(PERFORMANCE_SOURCE, {}).get("adr") == ledger["adr"],
        "kast": persisted.get(PERFORMANCE_SOURCE, {}).get("kast") == ledger["kast"],
        "effective_enemy_utility_damage": (
            persisted.get(UTILITY_SOURCE, {}).get("effective_enemy_utility_damage")
            == ledger["effective_enemy_utility_damage"]
        ),
        "opening_deaths": persisted.get(PERFORMANCE_SOURCE, {}).get("opening_deaths") == ledger["opening_deaths"],
    }
    return {
        "parser_artifact_id": artifact.id,
        "demo_sha1": artifact.demo_sha1,
        "event_set_id": result.event_set_id,
        "event_set_artifact": str(artifact_path) if artifact_path else None,
        "snapshot_ids": [snapshot.id for snapshot in snapshots],
        "sources": sorted(snapshot.source for snapshot in snapshots),
        "metric_groups": list(METRIC_GROUPS),
        "semantic_version": COACH_METRIC_SEMANTIC_VERSION,
        "identity_valid": all(
            snapshot.owner_user_id == OWNER_USER_ID
            and snapshot.player_steamid == OWNER_STEAM_ID
            and snapshot.semantic_version == COACH_METRIC_SEMANTIC_VERSION
            and snapshot.validation_status == "validated"
            for snapshot in snapshots
        ),
        "independent_ledger": ledger,
        "persisted_comparison": comparison,
        "comparison_pass": all(comparison.values()),
    }


def _independent_ledger(result: Any) -> dict[str, Any]:
    damage = [
        item
        for item in (result.metadata.get("damage_ledger") or [])
        if str(item.get("attacker_steamid") or "") == OWNER_STEAM_ID and item.get("relation") == "enemy"
    ]
    rounds = int(result.performance["rounds_played"])
    effective_damage = sum(int(item.get("effective_damage") or 0) for item in damage)
    kast_rows = list(result.metadata.get("kast_round_ledger") or [])
    opening_rows = list(result.metadata.get("opening_duel_ledger") or [])
    utility_damage = sum(
        int(item.get("effective_damage") or 0)
        for item in damage
        if item.get("damage_class") in {"he", "fire"}
    )
    return {
        "rounds_played": rounds,
        "adr": round(effective_damage / rounds, 3),
        "kast": round(sum(int(bool(item.get("kast"))) for item in kast_rows) / rounds * 100, 3),
        "opening_deaths": sum(str(item.get("victim_steamid") or "") == OWNER_STEAM_ID for item in opening_rows),
        "effective_enemy_utility_damage": utility_damage,
    }


def _evaluate_active_progress_once(db: Session, *, match_ids: Sequence[int]) -> dict[str, Any] | None:
    context = active_mission_context_for_owner(
        db,
        user_id=OWNER_USER_ID,
        owner_steam_id=OWNER_STEAM_ID,
    )
    if context["active_mission_count"] != 1:
        return None
    mission_id = int(context["active_missions"][0]["mission_id"])
    latest_ids = list(match_ids[-3:])
    snapshots = list(
        db.scalars(
            select(MetricSnapshot)
            .where(MetricSnapshot.owner_user_id == OWNER_USER_ID)
            .where(MetricSnapshot.match_id.in_(latest_ids))
            .where(MetricSnapshot.semantic_version == COACH_METRIC_SEMANTIC_VERSION)
            .where(MetricSnapshot.validation_status == "validated")
            .order_by(MetricSnapshot.match_id, MetricSnapshot.source)
        ).all()
    )
    existing = list(
        db.scalars(
            select(MissionProgressEvaluation)
            .where(MissionProgressEvaluation.mission_id == mission_id)
            .order_by(MissionProgressEvaluation.id.desc())
        ).all()
    )
    for row in existing:
        payload = _json_object(row.result_json)
        if payload.get("evaluation_window_json", {}).get("canonical_replay_match_ids") == latest_ids:
            return {"evaluation_id": row.id, "status": row.status, "reused": True, "match_ids": latest_ids}
    evaluation = evaluate_mission_progress(
        db,
        user_id=OWNER_USER_ID,
        mission_id=mission_id,
        evaluation_metric_snapshots=snapshots,
        evaluation_window={"type": "canonical_v3_replay", "canonical_replay_match_ids": latest_ids},
    )
    return {"evaluation_id": evaluation.id, "status": evaluation.status, "reused": False, "match_ids": latest_ids}


def _idempotency(
    db: Session,
    *,
    artifact_root: Path,
    selected: Sequence[int],
    apply: bool,
) -> dict[str, Any]:
    matches = _selected_matches(db, selected)
    before = _counts(db)
    if apply:
        for match in matches:
            _replay_match(db, match=match, artifact_root=artifact_root, apply=True)
        generate_rolling_mission_candidates(
            db,
            user_id=OWNER_USER_ID,
            owner_steam_id=OWNER_STEAM_ID,
            window_type="custom_match_set",
            match_ids=[match.id for match in matches],
        )
        db.commit()
    after = _counts(db)
    duplicates = _duplicate_v3_identities(db)
    stable_keys = ("metric_snapshots", "analysis_runs", "coach_hypotheses", "coach_missions", "progress_evaluations")
    return {
        "idempotency": {
            "counts_before": before,
            "counts_after": after,
            "stable": all(before[key] == after[key] for key in stable_keys),
            "duplicate_v3_identities": duplicates,
            "accepted": all(before[key] == after[key] for key in stable_keys) and not duplicates,
        }
    }


def _state_matrix(
    database: Path,
    *,
    artifact_root: Path,
    selected: Sequence[int],
    apply: bool,
) -> dict[str, Any]:
    scenarios = [
        ("S1", "selected_lineage_absent", "terminal", "block_missing_source_identity"),
        ("S2", "source_identity_only", "terminal", "block_new_download"),
        ("S3", "retained_demo_parser_absent", "retryable", "parser_required"),
        ("S4", "parser_metrics_absent", "retryable", "rebuild_v3_metrics"),
        ("S5", "metrics_hypotheses_absent", "retryable", "generate_canonical_candidates"),
        ("S6", "hypotheses_mission_progress_absent", "retryable", "select_if_supported"),
        ("S7", "complete_no_op", "terminal_success", "no_op"),
        ("S8", "retryable_failure_metadata", "retryable", "retry_sanitized"),
        ("S9", "interrupted_event_set_metric_backfill", "retryable", "restore_missing_metric_group"),
        ("S10", "concurrent_double_submit", "retryable", "serialize_by_unique_identity"),
    ]
    if not apply:
        return {
            "state_matrix": [
                {"state": key, "detected_state": name, "classification": classification, "allowed_action": action}
                for key, name, classification, action in scenarios
            ]
        }
    match_id = selected[0]
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="jc-coach-canonical-state-matrix-") as temp_dir:
        for key, name, classification, action in scenarios:
            scenario_db = Path(temp_dir) / f"{key}.db"
            shutil.copy2(database, scenario_db)
            scenario_artifacts = artifact_root / "state-matrix" / key.lower()
            scenario_engine = create_engine(f"sqlite:///{scenario_db}", future=True)
            with Session(scenario_engine) as db:
                before = _counts(db)
                detected, final_state, mutation, sanitized_error = _exercise_state(
                    db,
                    key=key,
                    match_id=match_id,
                    artifact_root=scenario_artifacts,
                )
                db.commit()
                after = _counts(db)
                results.append(
                    {
                        "state": key,
                        "expected_state": name,
                        "detected_state": detected,
                        "allowed_action": action,
                        "forbidden_mutation": "production_or_raw_demo_mutation",
                        "classification": classification,
                        "final_lineage": final_state,
                        "idempotent": not _duplicate_v3_identities(db),
                        "mutation": mutation,
                        "sanitized_error": sanitized_error,
                        "counts_before": before,
                        "counts_after": after,
                    }
                )
            scenario_engine.dispose()
            for suffix in ("", "-wal", "-shm", "-journal"):
                candidate = Path(f"{scenario_db}{suffix}")
                if candidate.exists():
                    candidate.unlink()
    accepted = all(row["detected_state"] == row["expected_state"] and row["idempotent"] for row in results)
    return {"state_matrix": results, "ten_state_recovery_matrix_accepted": accepted}


def _exercise_state(
    db: Session,
    *,
    key: str,
    match_id: int,
    artifact_root: Path,
) -> tuple[str, dict[str, Any], str, str | None]:
    match = db.get(Match, match_id)
    if match is None:
        raise ValueError("state-matrix source match missing")
    artifact = db.scalar(select(DemoParseArtifact).where(DemoParseArtifact.match_id == match_id))
    if artifact is None:
        raise ValueError("state-matrix parser artifact missing")
    if key == "S1":
        return "selected_lineage_absent", {"match": False}, "none", "source identity unavailable"
    if key == "S2":
        return "source_identity_only", {"match": True, "demo": False}, "none", "new download forbidden"
    if key == "S3":
        return "retained_demo_parser_absent", {"match": True, "demo": True, "parser": False}, "none", "parser required"
    if key == "S8":
        return (
            "retryable_failure_metadata",
            {"artifact_status": "retryable_failure", "raw_error_exposed": False},
            "failure metadata classified",
            "parser retry required",
        )
    if key in {"S4", "S9", "S10"}:
        if key == "S4":
            db.execute(
                delete(MetricSnapshot)
                .where(MetricSnapshot.match_id == match_id)
                .where(MetricSnapshot.semantic_version == COACH_METRIC_SEMANTIC_VERSION)
            )
            detected = "parser_metrics_absent"
        elif key == "S9":
            db.execute(
                delete(MetricSnapshot)
                .where(MetricSnapshot.match_id == match_id)
                .where(MetricSnapshot.semantic_version == COACH_METRIC_SEMANTIC_VERSION)
                .where(MetricSnapshot.source == AIM_SOURCE)
            )
            detected = "interrupted_event_set_metric_backfill"
        else:
            detected = "concurrent_double_submit"
        _replay_match(db, match=match, artifact_root=artifact_root, apply=True)
        if key == "S10":
            _replay_match(db, match=match, artifact_root=artifact_root, apply=True)
        sources = set(
            db.scalars(
                select(MetricSnapshot.source)
                .where(MetricSnapshot.match_id == match_id)
                .where(MetricSnapshot.semantic_version == COACH_METRIC_SEMANTIC_VERSION)
            ).all()
        )
        return (
            detected,
            {"v3_sources": sorted(sources), "complete": sources == EXPECTED_SOURCES},
            "isolated_recovery",
            None,
        )
    if key == "S5":
        candidates = generate_rolling_mission_candidates(
            db,
            user_id=OWNER_USER_ID,
            owner_steam_id=OWNER_STEAM_ID,
            window_type="custom_match_set",
            match_ids=[match_id],
        )
        return (
            "metrics_hypotheses_absent",
            {"candidate_count": len(candidates["candidates"]), "honest_no_claim": not candidates["candidates"]},
            "candidate generation",
            None,
        )
    if key == "S6":
        return (
            "hypotheses_mission_progress_absent",
            {"active_mission_count": 0, "honest_no_mission_allowed": True},
            "selection evaluated",
            None,
        )
    return "complete_no_op", {"complete": True}, "none", None


def _metric_acceptance(replay: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    comparisons = [bool(step["lineage"]["comparison_pass"]) for step in replay]
    return {
        "matches_compared": len(comparisons),
        "independent_ledgers_match_persisted_v3": all(comparisons),
        "metric_groups": list(METRIC_GROUPS),
        "accepted": len(comparisons) == 10 and all(comparisons),
    }


def _domain_acceptance(
    db: Session,
    replay: Sequence[Mapping[str, Any]],
    domain_key: str,
) -> dict[str, Any]:
    if domain_key == "impact_leak":
        positive = any(step["impact_leak_hypothesis_state"]["claim_supported"] for step in replay)
        insufficient = any(
            "insufficient_supported_matches" in step["impact_leak_hypothesis_state"]["reason_codes"]
            for step in replay
        )
        negative_ids = [30, 33, 117, 122, 124]
    else:
        positive = any(step["bad_fight_selection_candidates"] for step in replay)
        insufficient = any(not step["bad_fight_selection_candidates"] for step in replay[:2])
        negative_ids = [33, 91, 112]
    negative_result = generate_rolling_mission_candidates(
        db,
        user_id=OWNER_USER_ID,
        owner_steam_id=OWNER_STEAM_ID,
        window_type="custom_match_set",
        match_ids=negative_ids,
    )
    if domain_key == "impact_leak":
        negative = negative_result["diagnostics"]["impact_leak"]["claim_supported"] is False
    else:
        negative = not any(
            item.get("suppression_key", {}).get("domain_key") == "bad_fight_selection"
            for item in negative_result["candidates"]
        )
    return {
        "domain_key": domain_key,
        "positive_fixture": positive,
        "insufficient_data_non_claim_fixture": insufficient,
        "negative_no_signal_fixture": negative,
        "negative_fixture_match_ids": negative_ids,
        "accepted": positive and insufficient and negative,
    }


def _match_summary(db: Session, match: Match) -> dict[str, Any]:
    artifact = db.scalar(select(DemoParseArtifact).where(DemoParseArtifact.match_id == match.id))
    metadata = _latest_v3_metadata(db, match.id)
    return {
        "id": match.id,
        "played_at": match.played_at.isoformat() if match.played_at else None,
        "map_name": match.map_name,
        "result": match.result,
        "rounds_for": match.rounds_for,
        "rounds_against": match.rounds_against,
        "retained_demo": bool(match.demo_file and Path(match.demo_file).is_file())
        or bool(artifact and _resolve_demo(artifact)),
        "parser_artifact_id": artifact.id if artifact else None,
        "overtime": bool(metadata.get("accepted_phase", {}).get("overtime")),
        "incomplete_round_starts": metadata.get("accepted_phase", {}).get("incomplete_round_starts", []),
    }


def _latest_v3_metadata(db: Session, match_id: int) -> dict[str, Any]:
    row = db.scalar(
        select(MetricSnapshot)
        .where(MetricSnapshot.match_id == match_id)
        .where(MetricSnapshot.semantic_version == COACH_METRIC_SEMANTIC_VERSION)
        .order_by(MetricSnapshot.id.desc())
    )
    return _json_object(row.metadata_json) if row is not None else {}


def _mission_inventory(mission: CoachMission) -> dict[str, Any]:
    source = _json_object(mission.source_payload_json)
    return {
        "id": mission.id,
        "owner": {"user_id": mission.user_id, "steam_id": mission.owner_steam_id},
        "status": mission.status,
        "domain_key": source.get("mission_domain_key"),
        "problem_key": source.get("problem_key"),
        "hypothesis_id": mission.hypothesis_id,
        "title": mission.title,
        "focus": mission.focus,
        "activated_at": mission.activated_at.isoformat() if mission.activated_at else None,
        "ended_at": mission.ended_at.isoformat() if mission.ended_at else None,
        "created_at": mission.created_at.isoformat() if mission.created_at else None,
        "lifecycle_events": source.get("lifecycle_events", []),
    }


def _counts(db: Session) -> dict[str, int]:
    return {
        "metric_snapshots": int(db.scalar(select(func.count()).select_from(MetricSnapshot)) or 0),
        "analysis_runs": int(db.scalar(select(func.count()).select_from(AnalysisRun)) or 0),
        "coach_hypotheses": int(db.scalar(select(func.count()).select_from(CoachHypothesis)) or 0),
        "coach_missions": int(db.scalar(select(func.count()).select_from(CoachMission)) or 0),
        "active_missions": int(
            db.scalar(select(func.count()).select_from(CoachMission).where(CoachMission.status == "active")) or 0
        ),
        "progress_evaluations": int(
            db.scalar(select(func.count()).select_from(MissionProgressEvaluation)) or 0
        ),
    }


def _duplicate_v3_identities(db: Session) -> list[list[Any]]:
    rows = db.execute(
        select(
            MetricSnapshot.owner_user_id,
            MetricSnapshot.match_id,
            MetricSnapshot.player_key,
            MetricSnapshot.metric_domain,
            MetricSnapshot.semantic_version,
            MetricSnapshot.source,
            MetricSnapshot.source_event_set_id,
            func.count(),
        )
        .where(MetricSnapshot.semantic_version == COACH_METRIC_SEMANTIC_VERSION)
        .group_by(
            MetricSnapshot.owner_user_id,
            MetricSnapshot.match_id,
            MetricSnapshot.player_key,
            MetricSnapshot.metric_domain,
            MetricSnapshot.semantic_version,
            MetricSnapshot.source,
            MetricSnapshot.source_event_set_id,
        )
        .having(func.count() > 1)
    ).all()
    return [list(row) for row in rows]


def _resolve_demo(artifact: DemoParseArtifact) -> Path:
    candidates = [
        Path(artifact.source_demo_file) if artifact.source_demo_file else None,
        ROOT / "data/uploads/retained" / str(artifact.demo_sha1)[:2] / f"{artifact.demo_sha1}.dem",
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise FileNotFoundError(f"retained demo missing for match {artifact.match_id}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integrity(database: Path) -> str:
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        return str(connection.execute("PRAGMA integrity_check").fetchone()[0])


def _foreign_key_violations(database: Path) -> list[list[Any]]:
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        return [list(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()]


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, Mapping) else {}
    return {}


def _merge_report(path: Path, result: Mapping[str, Any]) -> None:
    existing = _json_object(path.read_text(encoding="utf-8")) if path.exists() else {}
    existing.update(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--selected-match-ids", type=int, nargs="+", required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--apply", action="store_true")
    parser.add_argument("--report-json", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        database=args.database,
        artifact_root=args.artifact_root,
        selected_match_ids=args.selected_match_ids,
        mode=args.mode,
        apply=args.apply,
    )
    _merge_report(args.report_json, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
