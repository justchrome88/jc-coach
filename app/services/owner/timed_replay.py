"""Clone-only timed integration replay of the accepted owner-to-coach lineage."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AIDomainAnalysis,
    CoachEvidenceBaseline,
    CoachMission,
    CoachMissionProposal,
    DemoParseArtifact,
    ImportJob,
    Match,
    MetricSnapshot,
    MissionProgressEvaluation,
    SteamAccount,
    User,
)
from app.services.coach.domain_analysis import (
    activate_domain_proposal,
    build_domain_evidence,
    coach_domain_slots_payload,
    digest,
    validate_domain_output,
)
from app.services.coach.semantic_distinctness import two_card_semantic_distinctness
from app.services.ingestion.artifact_integrity import artifact_file_integrity
from app.services.missions.presentation import serialize_mission_progress_evaluation
from app.services.parsing.evidence import source_date_provenance
from app.services.shared.stage_observer import observed_stage

OWNER_USER_ID = 17
STEAM_ACCOUNT_ID = 1
SOURCE_MATCH_ID = 128
TARGET_MATCH_ID = 129
IMPORT_JOB_ID = 105
PARSER_ARTIFACT_ID = 92
METRIC_SNAPSHOT_IDS = (1484, 1485, 1486, 1487)
BASELINE_ID = 1
ANALYSIS_IDS = {"impact_leak": 6, "bad_fight_selection": 7}
PROPOSAL_IDS = {"impact_leak": 3, "bad_fight_selection": 4}
MISSION_IDS = {"impact_leak": 4, "bad_fight_selection": 5}
EVALUATION_IDS = {"impact_leak": 12, "bad_fight_selection": 11}
EXPECTED_DEMO_SHA1 = "1172031e2a4831cd6c98d12ff5c24d6e23ad7bf8"
EXPECTED_DEMO_SHA256 = "bb49ee41870654e2c3509bdd96210efd032b424632b74466ee90944cedc40415"
EXPECTED_DEMO_SIZE = 200_832_909
REPLAY_IMPLEMENTATION_VERSION = "owner-timed-integration-replay-v1"

T = TypeVar("T")


def run_timed_integration_replay(
    db: Session,
    *,
    database: Path,
    run_root: Path,
    accepted_source_root: Path,
) -> dict[str, Any]:
    """Execute read/validate/reuse boundaries without external calls or new computation."""
    database = database.resolve()
    run_root = run_root.resolve()
    accepted_source_root = accepted_source_root.resolve()
    state: dict[str, Any] = {}

    state["preflight"] = _boundary("preflight", "success", lambda: _preflight(database, run_root, accepted_source_root))
    state["owner_resolution"] = _boundary("owner_resolution", "reused", lambda: _owner_resolution(db))
    state["target_discovery"] = _boundary("target_discovery", "reused", lambda: _target_discovery(db, run_root))
    state["steam_history"] = _boundary("steam_history", "reused", lambda: _steam_history(db))
    state["demo_acquisition"] = _boundary("demo_acquisition", "reused", lambda: _demo_acquisition(db, run_root))
    state["storage_integrity"] = _boundary(
        "storage_integrity", "success", lambda: _storage_integrity(run_root)
    )
    state["import_identity"] = _boundary("import_identity", "reused", lambda: _import_identity(db))
    state["parser"] = _boundary("parser", "reused", lambda: _parser(db))
    state["normalized_event_set"] = _boundary(
        "normalized_event_set", "reused", lambda: _normalized_event_set(run_root)
    )
    state["metric_computation"] = _boundary(
        "metric_computation", "reused", lambda: _metric_computation(db)
    )
    state["metric_validation"] = _boundary(
        "metric_validation", "success", lambda: _metric_validation(db)
    )
    baseline = _boundary("baseline_resolution", "reused", lambda: _baseline_resolution(db))
    state["baseline_resolution"] = _baseline_summary(baseline)

    bundles: dict[str, dict[str, Any]] = {}
    analyses: dict[str, AIDomainAnalysis] = {}
    outputs: dict[str, dict[str, Any]] = {}
    proposals: dict[str, CoachMissionProposal] = {}
    for domain in ("impact_leak", "bad_fight_selection"):
        bundles[domain] = _boundary(
            f"{domain}_evidence",
            "success",
            lambda domain=domain: build_domain_evidence(db, baseline=baseline, domain_key=domain),
        )
        analysis, output = _boundary(
            f"{domain}_provider",
            "reused",
            lambda domain=domain: _provider_reuse(db, domain),
            attempt=2 if domain == "impact_leak" else 1,
        )
        analyses[domain] = analysis
        outputs[domain] = output
        state[f"{domain}_provider"] = {
            "analysis_id": analysis.id,
            "attempt": analysis.attempt_number,
            "structured_output_hash": digest(output),
        }
        state[f"{domain}_validation"] = _boundary(
            f"{domain}_validation",
            "success",
            lambda domain=domain: _structured_validation(outputs[domain], bundles[domain]),
        )
        proposals[domain] = _boundary(
            f"{domain}_proposal",
            "reused",
            lambda domain=domain: _proposal_reuse(db, domain, analyses[domain]),
        )
        state[f"{domain}_evidence"] = {
            "evidence_hash": digest(bundles[domain]),
            "domain": domain,
        }
        state[f"{domain}_proposal"] = {
            "proposal_id": proposals[domain].id,
            "proposal_hash": proposals[domain].proposal_hash,
        }

    activations: dict[str, dict[str, Any]] = {}
    for domain in ("impact_leak", "bad_fight_selection"):
        activations[domain] = _boundary(
            f"{domain}_activation",
            "reused",
            lambda domain=domain: _activation_reuse(db, domain),
        )
    state["activations"] = activations
    state["subsequent_match_evaluation"] = _boundary(
        "subsequent_match_evaluation", "reused", lambda: _evaluation_reuse(db)
    )
    state["mission_progress"] = _boundary(
        "mission_progress", "reused", lambda: _mission_progress(db)
    )
    cards_payload = _boundary(
        "api_serialization", "success", lambda: _api_serialization(db)
    )
    state["api_serialization"] = {
        "schema_version": cards_payload["schema_version"],
        "card_count": len(cards_payload["cards"]),
        "domains": [card["domain"]["key"] for card in cards_payload["cards"]],
        "payload_hash": digest(cards_payload),
    }
    state["idempotent_repeat"] = _boundary(
        "idempotent_repeat", "reused", lambda: _idempotent_repeat(db)
    )
    state["concurrency"] = _boundary("concurrency", "reused", lambda: _concurrency_reuse(db))
    state["failure_smoke"] = _boundary(
        "failure_smoke", "success", lambda: _failure_smoke(run_root)
    )
    semantic_cards = [_semantic_card(domain, outputs[domain], proposals[domain]) for domain in ANALYSIS_IDS]
    semantic = two_card_semantic_distinctness(semantic_cards)
    state["final_acceptance"] = _boundary(
        "final_acceptance",
        "success",
        lambda: _final_acceptance(database, state["preflight"], semantic),
    )
    return {
        "schema_version": "timed-integration-replay-summary-v1",
        "accepted_source_run_id": "20260711T181221Z",
        "external_steam_calls": 0,
        "configured_model_calls": 0,
        "ids": {
            "source_match": SOURCE_MATCH_ID,
            "target_match": TARGET_MATCH_ID,
            "parser_artifact": PARSER_ARTIFACT_ID,
            "metric_snapshots": list(METRIC_SNAPSHOT_IDS),
            "analyses": ANALYSIS_IDS,
            "proposals": PROPOSAL_IDS,
            "missions": MISSION_IDS,
            "evaluations": EVALUATION_IDS,
        },
        "source_date_provenance": state["target_discovery"]["source_date_provenance"],
        "two_card_semantic_distinctness": semantic,
        "stage_results": state,
    }


def _boundary(
    stage: str,
    status: str,
    operation: Callable[[], T],
    *,
    attempt: int = 1,
) -> T:
    with observed_stage(
        stage,
        event="completed",
        status=status,
        attempt=attempt,
        implementation_version=REPLAY_IMPLEMENTATION_VERSION,
    ):
        return operation()


def _preflight(database: Path, run_root: Path, accepted_source_root: Path) -> dict[str, Any]:
    required = [run_root / name for name in ("db", "demo_storage", "artifacts", "provider_work", "logs")]
    if not all(path.is_dir() for path in required):
        raise ValueError("timed_replay_required_directories_missing")
    if run_root == accepted_source_root or not str(accepted_source_root).startswith("/var/tmp/jc-coach-r02a4/"):
        raise ValueError("invalid_accepted_source_root")
    if run_root not in database.parents:
        raise ValueError("timed_replay_database_outside_run_root")
    source_database = accepted_source_root / "db" / "cs2_coach.db"
    source_hash = _sha256(source_database)
    clone_hash = _sha256(database)
    if source_hash != clone_hash:
        raise ValueError("timed_replay_clone_not_byte_identical")
    integrity, foreign_keys = _sqlite_checks(database)
    if integrity != "ok" or foreign_keys:
        raise ValueError("timed_replay_database_integrity_failed")
    return {
        "source_db_sha256": source_hash,
        "clone_db_sha256_before": clone_hash,
        "integrity_check": integrity,
        "foreign_key_violations": len(foreign_keys),
        "required_directories": [path.name for path in required],
    }


def _owner_resolution(db: Session) -> dict[str, Any]:
    owner = db.get(User, OWNER_USER_ID)
    account = db.get(SteamAccount, STEAM_ACCOUNT_ID)
    if owner is None or not owner.is_active or account is None or account.user_id != owner.id:
        raise ValueError("accepted_owner_lineage_unavailable")
    safe_id = hashlib.sha256(f"owner:{owner.id}:account:{account.id}".encode()).hexdigest()
    return {"owner_user_id": owner.id, "steam_account_id": account.id, "owner_safe_id": safe_id}


def _target_discovery(db: Session, run_root: Path) -> dict[str, Any]:
    source = db.get(Match, SOURCE_MATCH_ID)
    target = db.get(Match, TARGET_MATCH_ID)
    if source is None or source.source != "steam_history" or target is None or target.source != "demo":
        raise ValueError("accepted_target_lineage_unavailable")
    raw = _mapping(target.raw_json)
    accepted = _safe_vertical_summary(run_root)["target"]
    identity_hash = hashlib.sha256(str(source.external_match_id).encode()).hexdigest()
    if accepted.get("safe_identity_hash") != identity_hash:
        raise ValueError("accepted_target_identity_hash_mismatch")
    provenance = source_date_provenance(raw, date_value_present=target.played_at is not None)
    if not provenance:
        raise ValueError("empty_source_date_provenance")
    return {
        "source_match_id": source.id,
        "target_match_id": target.id,
        "safe_identity_hash": identity_hash,
        "played_at": target.played_at.isoformat() if target.played_at else None,
        "source_date_provenance": provenance,
    }


def _steam_history(db: Session) -> dict[str, Any]:
    source = db.get(Match, SOURCE_MATCH_ID)
    if source is None or source.import_job_id != IMPORT_JOB_ID or source.user_id != OWNER_USER_ID:
        raise ValueError("steam_history_lineage_mismatch")
    return {"source_match_id": source.id, "status": "reused", "external_calls": 0}


def _demo_acquisition(db: Session, run_root: Path) -> dict[str, Any]:
    job = db.get(ImportJob, IMPORT_JOB_ID)
    target = db.get(Match, TARGET_MATCH_ID)
    demo = _demo_path(run_root)
    if job is None or target is None or target.import_job_id != job.id or not demo.is_file():
        raise ValueError("demo_acquisition_lineage_mismatch")
    return {"import_job_id": job.id, "target_match_id": target.id, "status": "reused", "external_calls": 0}


def _storage_integrity(run_root: Path) -> dict[str, Any]:
    demo = _demo_path(run_root)
    integrity = artifact_file_integrity(
        demo,
        expected_sha1=EXPECTED_DEMO_SHA1,
        expected_size_bytes=EXPECTED_DEMO_SIZE,
        reparse_on_problem=False,
    )
    sha256 = _sha256(demo)
    if integrity["state"] != "available" or sha256 != EXPECTED_DEMO_SHA256:
        raise ValueError("accepted_demo_integrity_mismatch")
    return {
        "state": integrity["state"],
        "size_bytes": integrity["size_bytes"],
        "sha1": integrity["sha1"],
        "sha256": sha256,
    }


def _import_identity(db: Session) -> dict[str, Any]:
    job = db.get(ImportJob, IMPORT_JOB_ID)
    rows = list(db.scalars(select(Match).where(Match.import_job_id == IMPORT_JOB_ID)).all())
    ids = {row.id for row in rows}
    if job is None or {SOURCE_MATCH_ID, TARGET_MATCH_ID} - ids:
        raise ValueError("stable_import_identity_mismatch")
    return {"import_job_id": job.id, "linked_match_ids": sorted(ids), "status": "reused"}


def _parser(db: Session) -> dict[str, Any]:
    artifact = db.get(DemoParseArtifact, PARSER_ARTIFACT_ID)
    if artifact is None or artifact.match_id != TARGET_MATCH_ID or artifact.status != "parsed":
        raise ValueError("accepted_parser_artifact_unavailable")
    payload = _mapping(artifact.payload_json)
    if not payload:
        raise ValueError("accepted_parser_payload_unreadable")
    return {
        "artifact_id": artifact.id,
        "parser_name": artifact.parser_name,
        "parser_version": artifact.parser_version,
        "payload_hash": digest(payload),
        "status": "reused",
    }


def _normalized_event_set(run_root: Path) -> dict[str, Any]:
    summary = _safe_vertical_summary(run_root)["normalized_event_set"]
    event_files = list((run_root / "artifacts" / "coach_metric_event_sets").glob("*/*.json"))
    if len(event_files) != 1:
        raise ValueError("accepted_event_set_file_unavailable")
    event_hash = _sha256(event_files[0])
    expected_id = str(summary.get("id") or "")
    if event_hash != event_files[0].stem or not expected_id or int(summary.get("event_count") or 0) != 2142:
        raise ValueError("accepted_event_set_identity_mismatch")
    json.loads(event_files[0].read_text(encoding="utf-8"))
    return {
        "event_set_id": expected_id,
        "event_file_hash": event_hash,
        "content_hash": summary.get("content_hash"),
        "event_count": 2142,
        "status": "reused",
    }


def _metric_computation(db: Session) -> dict[str, Any]:
    snapshots = _metric_snapshots(db)
    for snapshot in snapshots:
        if not _mapping(snapshot.metrics_json):
            raise ValueError("accepted_metric_snapshot_unreadable")
    return {"snapshot_ids": [row.id for row in snapshots], "status": "reused", "new_snapshots": 0}


def _metric_validation(db: Session) -> dict[str, Any]:
    snapshots = _metric_snapshots(db)
    if any(row.validation_status != "validated" for row in snapshots):
        raise ValueError("accepted_metric_snapshot_not_validated")
    if any(row.source_parser_artifact_id != PARSER_ARTIFACT_ID for row in snapshots):
        raise ValueError("accepted_metric_parser_lineage_mismatch")
    event_ids = {row.source_event_set_id for row in snapshots}
    if len(event_ids) != 1:
        raise ValueError("accepted_metric_event_lineage_mismatch")
    return {
        "validation_status": "validated",
        "snapshot_ids": [row.id for row in snapshots],
        "implementation_versions": sorted({str(row.implementation_version) for row in snapshots}),
    }


def _baseline_resolution(db: Session) -> CoachEvidenceBaseline:
    baseline = db.get(CoachEvidenceBaseline, BASELINE_ID)
    if baseline is None or baseline.owner_user_id != OWNER_USER_ID:
        raise ValueError("accepted_baseline_unavailable")
    if len(json.loads(baseline.match_ids_json)) != 30:
        raise ValueError("accepted_baseline_membership_mismatch")
    return baseline


def _baseline_summary(baseline: CoachEvidenceBaseline) -> dict[str, Any]:
    return {"baseline_id": baseline.id, "baseline_hash": baseline.baseline_hash, "match_count": 30}


def _provider_reuse(db: Session, domain: str) -> tuple[AIDomainAnalysis, dict[str, Any]]:
    analysis = db.get(AIDomainAnalysis, ANALYSIS_IDS[domain])
    if analysis is None or analysis.domain_key != domain or analysis.validation_status != "accepted":
        raise ValueError(f"accepted_{domain}_analysis_unavailable")
    expected_attempt = 2 if domain == "impact_leak" else 1
    if analysis.attempt_number != expected_attempt:
        raise ValueError(f"accepted_{domain}_attempt_mismatch")
    output = _mapping(analysis.structured_output_json)
    if not output:
        raise ValueError(f"accepted_{domain}_structured_output_unreadable")
    return analysis, output


def _structured_validation(output: Mapping[str, Any], bundle: Mapping[str, Any]) -> dict[str, Any]:
    errors = validate_domain_output(output, bundle)
    if errors:
        raise ValueError(f"accepted_structured_output_invalid:{','.join(errors)}")
    return {"validation_status": "accepted", "validation_errors": []}


def _proposal_reuse(db: Session, domain: str, analysis: AIDomainAnalysis) -> CoachMissionProposal:
    proposal = db.get(CoachMissionProposal, PROPOSAL_IDS[domain])
    if (
        proposal is None
        or proposal.domain_key != domain
        or proposal.analysis_id != analysis.id
        or proposal.baseline_id != BASELINE_ID
        or not proposal.is_current
        or not _mapping(proposal.payload_json)
    ):
        raise ValueError(f"accepted_{domain}_proposal_unavailable")
    return proposal


def _activation_reuse(db: Session, domain: str) -> dict[str, Any]:
    result = activate_domain_proposal(db, owner_user_id=OWNER_USER_ID, proposal_id=PROPOSAL_IDS[domain])
    mission = result["mission"]
    if not result["reused"] or mission.id != MISSION_IDS[domain] or mission.status != "active":
        raise ValueError(f"accepted_{domain}_activation_not_reused")
    return {"domain": domain, "mission_id": mission.id, "reused": True}


def _evaluation_reuse(db: Session) -> dict[str, Any]:
    rows = [db.get(MissionProgressEvaluation, value) for value in EVALUATION_IDS.values()]
    if any(row is None or row.status != "insufficient_data" for row in rows):
        raise ValueError("accepted_evaluations_unavailable")
    return {
        "evaluation_ids": sorted(row.id for row in rows if row is not None),
        "statuses": sorted({str(row.status) for row in rows if row is not None}),
        "status": "reused",
    }


def _mission_progress(db: Session) -> dict[str, Any]:
    serialized = []
    for evaluation_id in EVALUATION_IDS.values():
        row = db.get(MissionProgressEvaluation, evaluation_id)
        if row is None:
            raise ValueError("accepted_mission_progress_unavailable")
        serialized.append(serialize_mission_progress_evaluation(row))
    return {
        "evaluation_count": len(serialized),
        "evaluation_ids": sorted(item["evaluation_id"] for item in serialized),
        "status": "reused",
    }


def _api_serialization(db: Session) -> dict[str, Any]:
    payload = coach_domain_slots_payload(db, owner_user_id=OWNER_USER_ID, include_provenance=False)
    if payload.get("schema_version") != "coach-domain-slots-v1" or len(payload.get("cards") or []) != 2:
        raise ValueError("accepted_two_card_serialization_unavailable")
    domains = {card["domain"]["key"] for card in payload["cards"]}
    if domains != set(ANALYSIS_IDS):
        raise ValueError("accepted_two_card_domains_mismatch")
    return payload


def _idempotent_repeat(db: Session) -> dict[str, Any]:
    before = _accepted_counts(db)
    first = [_activation_reuse(db, domain) for domain in ANALYSIS_IDS]
    second = [_activation_reuse(db, domain) for domain in ANALYSIS_IDS]
    after = _accepted_counts(db)
    if before != after or first != second:
        raise ValueError("idempotent_reuse_changed_state")
    return {"counts_unchanged": True, "activation_reused": True, "external_calls": 0}


def _concurrency_reuse(db: Session) -> dict[str, Any]:
    proposals = int(
        db.scalar(
            select(func.count()).select_from(CoachMissionProposal).where(CoachMissionProposal.id.in_(PROPOSAL_IDS.values()))
        )
        or 0
    )
    missions = int(
        db.scalar(select(func.count()).select_from(CoachMission).where(CoachMission.id.in_(MISSION_IDS.values()))) or 0
    )
    if proposals != 2 or missions != 2:
        raise ValueError("concurrency_identity_uniqueness_mismatch")
    return {"deterministic_identity_count": 2, "duplicate_lineage": 0, "status": "reused"}


def _failure_smoke(run_root: Path) -> dict[str, Any]:
    fixture = json.loads((run_root / "artifacts" / "failure_smoke_safe.json").read_text(encoding="utf-8"))
    required = {"provider_unavailable", "provider_timeout", "malformed_response"}
    if set(fixture) != required:
        raise ValueError("failure_fixture_summary_incomplete")
    database_results = {}
    for name in required:
        database = run_root / "db" / f"failure_{name}.db"
        integrity, foreign_keys = _sqlite_checks(database)
        if integrity != "ok" or foreign_keys:
            raise ValueError(f"failure_fixture_integrity_failed:{name}")
        database_results[name] = {"integrity": integrity, "foreign_key_violations": 0}
    return {"fixtures": database_results, "sanitized_summary_hash": digest(fixture)}


def _final_acceptance(database: Path, preflight: Mapping[str, Any], semantic: Mapping[str, Any]) -> dict[str, Any]:
    final_hash = _sha256(database)
    if final_hash != preflight["clone_db_sha256_before"]:
        raise ValueError("timed_replay_database_mutated")
    if semantic.get("status") != "PASS":
        raise ValueError("two_card_semantic_distinctness_failed")
    return {
        "database_unchanged": True,
        "clone_db_sha256_after": final_hash,
        "two_card_semantic_distinctness": "PASS",
        "external_steam_calls": 0,
        "configured_model_calls": 0,
    }


def _semantic_card(
    domain: str,
    output: Mapping[str, Any],
    proposal: CoachMissionProposal,
) -> dict[str, Any]:
    mission_target = _mapping(proposal.payload_json)
    return {
        "domain": domain,
        "headline": output.get("headline"),
        "hypothesis": output.get("hypothesis"),
        "primary_pattern": output.get("primary_pattern"),
        "reasoning_summary": output.get("reasoning_summary"),
        "recommended_focus": output.get("recommended_focus"),
        "evidence_references": output.get("evidence_refs") or output.get("metric_refs") or [],
        "counterevidence_references": output.get("counterevidence_refs") or [],
        "caveats": output.get("caveats") or [],
        "mission_target": {
            key: mission_target.get(key)
            for key in (
                "primary_metric",
                "target_direction",
                "target_value",
                "target_delta",
                "minimum_future_matches",
                "maximum_future_matches",
                "behavioral_focus",
            )
        },
    }


def _metric_snapshots(db: Session) -> list[MetricSnapshot]:
    rows = list(
        db.scalars(select(MetricSnapshot).where(MetricSnapshot.id.in_(METRIC_SNAPSHOT_IDS)).order_by(MetricSnapshot.id))
    )
    if [row.id for row in rows] != list(METRIC_SNAPSHOT_IDS):
        raise ValueError("accepted_metric_snapshots_unavailable")
    return rows


def _accepted_counts(db: Session) -> dict[str, int]:
    return {
        "analyses": int(db.scalar(select(func.count()).select_from(AIDomainAnalysis)) or 0),
        "proposals": int(db.scalar(select(func.count()).select_from(CoachMissionProposal)) or 0),
        "missions": int(db.scalar(select(func.count()).select_from(CoachMission)) or 0),
        "evaluations": int(db.scalar(select(func.count()).select_from(MissionProgressEvaluation)) or 0),
    }


def _demo_path(run_root: Path) -> Path:
    matches = list((run_root / "demo_storage").glob(f"**/{EXPECTED_DEMO_SHA1}.dem"))
    if len(matches) != 1:
        raise ValueError("accepted_demo_copy_unavailable")
    return matches[0]


def _safe_vertical_summary(run_root: Path) -> dict[str, Any]:
    value = json.loads((run_root / "artifacts" / "vertical_safe_summary.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("run_id") != "20260711T181221Z":
        raise ValueError("accepted_safe_vertical_summary_unavailable")
    return value


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _sqlite_checks(database: Path) -> tuple[str, list[tuple[Any, ...]]]:
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_keys = list(connection.execute("PRAGMA foreign_key_check").fetchall())
    return integrity, foreign_keys


def _sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


__all__ = ("REPLAY_IMPLEMENTATION_VERSION", "run_timed_integration_replay")
