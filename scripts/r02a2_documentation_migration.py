#!/usr/bin/env python3
"""Build and validate the H01B-R02A2 no-loss documentation manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path("_legacy_archive/r02a2-2026-07-11")
DEFAULT_INVENTORY = Path(
    "/opt/jc-coach-pm/reports/H01B-R02A1_source_of_truth_inventory.json"
)
DEFAULT_MANIFEST = ROOT / ARCHIVE / "MIGRATION_MANIFEST.json"

DOCS_SHELL = {
    "docs/README.md",
    "docs/CURRENT_STATUS.md",
    "docs/HANDOFF.md",
    "docs/metrics/AGENTS.md",
    "docs/project_management/WP_REGISTRY.md",
    "docs/project_management/DOCS_INDEX.md",
}

CONTROL_REPLACEMENTS = {
    "docs/CURRENT_STATUS.md",
    "docs/HANDOFF.md",
    "docs/PUBLIC_DEPLOYMENT_CHECKLIST.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/project_management/ACCEPTANCE_MATRIX.md",
    "docs/project_management/MASTER_WP_CHECKLIST.md",
    "docs/project_management/VERSION_ROADMAP.md",
    "docs/project_management/WORK_PACKAGE_BACKLOG.md",
    "docs/project_management/WP_REGISTRY.md",
}

RUNTIME_DESTINATIONS = {
    "docs/coach/coach-domain-model.json": "app/contracts/coach/coach-domain-model.json",
    "docs/coach/evidence-schemas/coach-domain-evidence.schema.json": (
        "app/contracts/coach/schemas/coach-domain-evidence.schema.json"
    ),
    "docs/coach/prompts/bad_fight_selection_hypothesis_prompt.md": (
        "app/contracts/coach/prompts/bad_fight_selection_hypothesis_prompt.md"
    ),
    "docs/coach/prompts/impact_leak_hypothesis_prompt.md": (
        "app/contracts/coach/prompts/impact_leak_hypothesis_prompt.md"
    ),
    "docs/coach/schemas/ai-domain-hypothesis.schema.json": (
        "app/contracts/coach/schemas/ai-domain-hypothesis.schema.json"
    ),
    "docs/metrics/coach/coach-domain-metric-requirements.json": (
        "app/contracts/metrics/coach-domain-metric-requirements.json"
    ),
    "docs/metrics/registry/metric-registry.schema.json": (
        "app/contracts/metrics/registry/metric-registry.schema.json"
    ),
    "docs/metrics/registry/metrics.json": "app/contracts/metrics/registry/metrics.json",
    "docs/project_management/DOCS_MAP.md": "project_control/manifests/DOCS_MAP.md",
}

AGENT_DESTINATIONS = {
    "docs/agents/DB_GUARDIAN.md": "project_control/agents/guardians/DB_GUARDIAN.md",
    "docs/agents/IMPORT_GUARDIAN.md": "project_control/agents/guardians/IMPORT_GUARDIAN.md",
    "docs/agents/METRICS_GUARDIAN.md": "project_control/agents/guardians/METRICS_GUARDIAN.md",
    "docs/agents/RUNTIME_GUARDIAN.md": "project_control/agents/guardians/RUNTIME_GUARDIAN.md",
    "docs/agents/TEST_GUARDIAN.md": "project_control/agents/guardians/TEST_GUARDIAN.md",
    "docs/agents/UI_COACH_GUARDIAN.md": "project_control/agents/guardians/UI_COACH_GUARDIAN.md",
    "docs/agents/README.md": "project_control/agents/README.md",
    "docs/agents/roles/DOCUMENTATION_STEWARD.md": (
        "project_control/agents/roles/DOCUMENTATION_STEWARD.md"
    ),
    "docs/agents/roles/IMPLEMENTATION_AGENT.md": (
        "project_control/agents/roles/IMPLEMENTATION_AGENT.md"
    ),
    "docs/agents/roles/QA_REVIEWER.md": "project_control/agents/roles/QA_REVIEWER.md",
    "docs/agents/roles/ROLE_CARD_TEMPLATE.md": (
        "project_control/agents/roles/ROLE_CARD_TEMPLATE.md"
    ),
    "docs/project_management/AGENT_WORKFLOW.md": (
        "project_control/agents/AGENT_WORKFLOW.md"
    ),
    "docs/project_management/PROJECT_OPERATING_PROTOCOL.md": (
        "project_control/agents/PROJECT_OPERATING_PROTOCOL.md"
    ),
    "docs/project_management/PROMPT_PLAYBOOK.md": (
        "project_control/agents/PROMPT_PLAYBOOK.md"
    ),
}

HUMAN_DESTINATIONS = {
    "docs/AI_COACH.md": "project_docs/product/AI_COACH.md",
    "docs/CS2_DOMAIN_CONTRACT.md": "project_docs/product/CS2_DOMAIN_CONTRACT.md",
    "docs/KNOWN_LIMITATIONS.md": "project_docs/product/KNOWN_LIMITATIONS.md",
    "docs/RECOMMENDATIONS.md": "project_docs/product/RECOMMENDATIONS.md",
    "docs/coach/CANONICAL_COACH_DOMAIN_MODEL.md": (
        "project_docs/product/CANONICAL_COACH_DOMAIN_MODEL.md"
    ),
    "docs/coach/MISSION_LINEAGE_AND_SELECTION_MODEL.md": (
        "project_docs/product/MISSION_LINEAGE_AND_SELECTION_MODEL.md"
    ),
    "docs/API_CONTRACTS.md": "project_docs/architecture/API_CONTRACTS.md",
    "docs/ARCHITECTURE.md": "project_docs/architecture/ARCHITECTURE.md",
    "docs/DECISIONS.md": "project_docs/architecture/DECISIONS.md",
    "docs/STEAM_IMPORT_ARCHITECTURE.md": (
        "project_docs/architecture/STEAM_IMPORT_ARCHITECTURE.md"
    ),
    "docs/coach/AI_HYPOTHESIS_ENGINE_ARCHITECTURE.md": (
        "project_docs/architecture/AI_HYPOTHESIS_ENGINE_ARCHITECTURE.md"
    ),
    "docs/BACKUP_RESTORE.md": "project_docs/operations/BACKUP_RESTORE.md",
    "docs/DEPLOYMENT.md": "project_docs/operations/DEPLOYMENT.md",
    "docs/MIGRATIONS.md": "project_docs/operations/MIGRATIONS.md",
    "docs/SECURITY.md": "project_docs/operations/SECURITY.md",
    "docs/STEAM_IMPORT.md": "project_docs/operations/STEAM_IMPORT.md",
    "docs/TESTING.md": "project_docs/operations/TESTING.md",
    "docs/METRICS.md": "project_docs/metrics/METRICS.md",
    "docs/metrics/README.md": "project_docs/metrics/README.md",
    "docs/metrics/GROUND_TRUTH_POLICY.md": "project_docs/metrics/GROUND_TRUTH_POLICY.md",
    "docs/metrics/METRIC_CHANGE_POLICY.md": "project_docs/metrics/METRIC_CHANGE_POLICY.md",
    "docs/metrics/METRIC_DATA_LINEAGE.md": "project_docs/metrics/METRIC_DATA_LINEAGE.md",
    "docs/metrics/METRIC_GOVERNANCE.md": "project_docs/metrics/METRIC_GOVERNANCE.md",
    "docs/metrics/coach/ADDING_A_COACH_METRIC.md": (
        "project_docs/metrics/coach/ADDING_A_COACH_METRIC.md"
    ),
    "docs/metrics/coach/COACH_DOMAIN_METRIC_REQUIREMENTS.md": (
        "project_docs/metrics/coach/COACH_DOMAIN_METRIC_REQUIREMENTS.md"
    ),
    "docs/metrics/coach/COACH_METRIC_EVIDENCE_CAPABILITY_MATRIX.md": (
        "project_docs/metrics/coach/COACH_METRIC_EVIDENCE_CAPABILITY_MATRIX.md"
    ),
    "docs/metrics/coach/COACH_METRIC_PACK_V1.md": (
        "project_docs/metrics/coach/COACH_METRIC_PACK_V1.md"
    ),
    "docs/metrics/coach/TEN_MATCH_REPLAY_CORPUS.md": (
        "project_docs/acceptance/TEN_MATCH_REPLAY_CORPUS.md"
    ),
    "docs/metrics/contracts/aim_weapon.md": "project_docs/metrics/contracts/aim_weapon.md",
    "docs/metrics/contracts/core_combat.md": "project_docs/metrics/contracts/core_combat.md",
    "docs/metrics/contracts/round_participation.md": (
        "project_docs/metrics/contracts/round_participation.md"
    ),
    "docs/metrics/contracts/temporal_survival.md": (
        "project_docs/metrics/contracts/temporal_survival.md"
    ),
    "docs/metrics/contracts/utility.md": "project_docs/metrics/contracts/utility.md",
    "docs/metrics/generated/METRIC_CATALOG.md": (
        "project_docs/metrics/generated/METRIC_CATALOG.md"
    ),
    "docs/acceptance/CANONICAL_TWO_DOMAIN_VERTICAL_REPLAY.md": (
        "project_docs/acceptance/CANONICAL_TWO_DOMAIN_VERTICAL_REPLAY.md"
    ),
}

ARCHIVE_FOR_REPLACEMENT = {
    *CONTROL_REPLACEMENTS,
    "docs/README.md",
    "docs/project_management/DOCS_INDEX.md",
    "docs/metrics/AGENTS.md",
    "docs/agents/PM_ORCHESTRATOR.md",
    "docs/agents/roles/PM_ORCHESTRATOR.md",
    "docs/AI_COACH_PROVIDER_ARCHITECTURE.md",
    "docs/FEATURES_RU.md",
    "docs/PROJECT_CONTROL.md",
    "docs/PROJECT_GOVERNANCE.md",
    "docs/foundation_hardening/2026-07-06-readiness-recovery-plan/current_schema_baseline.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_destination(source: str) -> str:
    return str(ARCHIVE / "docs" / source.removeprefix("docs/"))


def planned_destination(source: str, primary_class: str) -> tuple[str, str]:
    if source in ARCHIVE_FOR_REPLACEMENT:
        return archive_destination(source), "original archived before compact replacement or merge"
    if source in RUNTIME_DESTINATIONS:
        return RUNTIME_DESTINATIONS[source], "task runtime-contract mapping"
    if source in AGENT_DESTINATIONS:
        return AGENT_DESTINATIONS[source], "task agent-control mapping"
    if source in HUMAN_DESTINATIONS:
        return HUMAN_DESTINATIONS[source], "task human-documentation category mapping"
    if primary_class in {
        "historical_handoff",
        "historical_report",
        "superseded_plan_or_design",
        "duplicate_current_candidate",
    }:
        return archive_destination(source), "R02A1 legacy/superseded/duplicate classification"
    raise SystemExit(f"unmapped active source: {source} ({primary_class})")


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def build_manifest(args: argparse.Namespace) -> int:
    inventory_path = Path(args.inventory)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    audited = inventory["docs_inventory"]["files"]
    tracked_docs = git("ls-files", "docs").splitlines()
    audited_paths = [item["path"] for item in audited]
    if len(audited_paths) != 332 or set(audited_paths) != set(tracked_docs):
        raise SystemExit("MANIFEST_ERROR=R02A1_docs_inventory_does_not_match_tracked_tree")

    records = []
    for item in sorted(audited, key=lambda value: value["path"]):
        source = item["path"]
        source_path = ROOT / source
        destination, basis = planned_destination(source, item["primary_class"])
        records.append(
            {
                "source_path": source,
                "source_sha256": sha256(source_path),
                "source_size": source_path.stat().st_size,
                "r02a1_primary_class": item["primary_class"],
                "r02a1_recommended_destination": item["recommended_future_destination"],
                "planned_destination": destination,
                "destination_basis": basis,
                "preservation": "byte_identical",
            }
        )

    for source in ["AGENTS.md", "README.md", "AGENT.md", "LATER.md", "WORKLOG.md"]:
        source_path = ROOT / source
        destination = str(ARCHIVE / "product_root" / source)
        records.append(
            {
                "source_path": source,
                "source_sha256": sha256(source_path),
                "source_size": source_path.stat().st_size,
                "r02a1_primary_class": (
                    "fixed_path_compact_replacement" if source in {"AGENTS.md", "README.md"} else "root_legacy"
                ),
                "r02a1_recommended_destination": destination,
                "planned_destination": destination,
                "destination_basis": "task fixed-entrypoint preservation" if source in {"AGENTS.md", "README.md"} else "R02A1 root legacy audit",
                "preservation": "byte_identical",
            }
        )

    destinations = [record["planned_destination"] for record in records]
    if len(destinations) != len(set(destinations)):
        raise SystemExit("MANIFEST_ERROR=destination_is_not_unique")
    if any(destination == "deleted" for destination in destinations):
        raise SystemExit("MANIFEST_ERROR=deleted_destination")

    payload = {
        "manifest_version": 1,
        "task": "H01B-R02A2_SAFE_DOCUMENTATION_AND_CONTROL_MIGRATION",
        "archive_root": str(ARCHIVE) + "/",
        "authority": {
            "r02a1_inventory": str(inventory_path),
            "r02a1_inventory_sha256": sha256(inventory_path),
            "r02a1_final_artifact_commit": args.r02a1_commit,
            "classification_changes": [],
        },
        "original_state": {
            "captured_at": args.captured_at,
            "product_head": git("rev-parse", "HEAD"),
            "product_tree": git("rev-parse", "HEAD^{tree}"),
            "product_tracked_content_sha256": args.tracked_content_hash,
            "product_tracked_content_hash_method": "sha256 of concatenated git-ls-files file sha256 lines",
            "pm_head": args.pm_head,
            "production_db_sha256": args.db_sha256,
            "service": json.loads(args.service_json),
            "product_branch": git("branch", "--show-current"),
            "pm_branch": args.pm_branch,
        },
        "invariants": {
            "original_docs_files": 332,
            "unknown_active_files": 0,
            "deleted_destinations": 0,
            "one_destination_per_source": True,
            "byte_identical_preservation_required": True,
        },
        "records": records,
    }
    atomic_json_write(Path(args.output), payload)
    print(f"MIGRATION_MANIFEST={Path(args.output).resolve()}")
    print("ORIGINAL_DOC_FILES=332")
    print(f"TOTAL_PRESERVATION_RECORDS={len(records)}")
    print("MANIFEST_RESULT=written")
    return 0


def validate_manifest(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    errors: list[str] = []
    docs_records = 0
    for record in manifest["records"]:
        if record["source_path"].startswith("docs/"):
            docs_records += 1
        destination = ROOT / record["planned_destination"]
        if not destination.is_file():
            errors.append(f"missing:{record['planned_destination']}")
            continue
        if destination.stat().st_size != record["source_size"]:
            errors.append(f"size:{record['planned_destination']}")
        if sha256(destination) != record["source_sha256"]:
            errors.append(f"sha256:{record['planned_destination']}")
    tracked_docs = set(git("ls-files", "docs").splitlines())
    if docs_records != 332:
        errors.append(f"docs_records:{docs_records}")
    if not tracked_docs <= DOCS_SHELL or len(tracked_docs) > 6:
        errors.append("docs_shell_allowlist")
    if errors:
        print("NO_LOSS_RESULT=FAIL")
        for error in errors:
            print(f"NO_LOSS_ERROR={error}")
        return 1
    print("ORIGINAL_DOC_FILES_ACCOUNTED=332/332")
    print("ORIGINAL_CONTENT_DELETED=0")
    print(f"DOCS_TRACKED_FILE_COUNT={len(tracked_docs)}")
    print("NO_LOSS_RESULT=PASS")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build-manifest")
    build.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    build.add_argument("--output", default=str(DEFAULT_MANIFEST))
    build.add_argument("--captured-at", required=True)
    build.add_argument("--tracked-content-hash", required=True)
    build.add_argument("--pm-head", required=True)
    build.add_argument("--pm-branch", required=True)
    build.add_argument("--r02a1-commit", required=True)
    build.add_argument("--db-sha256", required=True)
    build.add_argument("--service-json", required=True)
    build.set_defaults(func=build_manifest)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    validate.set_defaults(func=validate_manifest)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
