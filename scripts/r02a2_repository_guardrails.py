#!/usr/bin/env python3
"""Enforce post-R02A2 repository layout and active file-I/O boundaries."""

from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCS_ALLOWLIST = frozenset(
    {
        "docs/README.md",
        "docs/CURRENT_STATUS.md",
        "docs/HANDOFF.md",
        "docs/metrics/AGENTS.md",
        "docs/project_management/WP_REGISTRY.md",
        "docs/project_management/DOCS_INDEX.md",
    }
)

ROOT_SERVICE_MODULE_ALLOWLIST = frozenset(
    {
        "__init__.py",
        "ai_coach.py",
        "ai_validator.py",
        "aim_stats.py",
        "analytics.py",
        "app_settings.py",
        "artifact_integrity.py",
        "auth.py",
        "coach_domain_ai.py",
        "coach_domain_model.py",
        "coach_insights.py",
        "coach_metric_pack.py",
        "coach_rules.py",
        "combat_event_derivation.py",
        "core_combat_metrics.py",
        "demo_parser.py",
        "demo_retention.py",
        "demo_storage.py",
        "event_metric_dictionary.py",
        "fresh_match_discovery.py",
        "i18n.py",
        "import_jobs.py",
        "import_orchestration.py",
        "importer.py",
        "match_phase.py",
        "match_processing.py",
        "match_queries.py",
        "metric_confidence.py",
        "metric_downstream_state.py",
        "metric_snapshots.py",
        "metric_truth.py",
        "mission_domain.py",
        "mistake_detection.py",
        "owner_coach_sync.py",
        "owner_coach_sync_batch.py",
        "owner_identity_reconciliation.py",
        "ownership.py",
        "parser_artifact_reader.py",
        "parser_evidence.py",
        "recommendation_tracking.py",
        "report_generator.py",
        "security.py",
        "steam_demo_acquisition.py",
        "steam_demo_downloader.py",
        "steam_integration.py",
        "steam_match_metadata.py",
        "steam_storage_guard.py",
        "utility_metrics.py",
        "weapon_names.py",
    }
)

CANONICAL_COACH_DOMAINS = ("impact_leak", "bad_fight_selection")
ACTIVE_MISSION_MODEL = "at_most_one_per_domain_per_owner"
DOMAIN_SUPPRESSION_INVARIANT = "an active mission suppresses only the same canonical domain"
REQUIRED_AGENT_PRINCIPLES = frozenset(
    {
        "branch/worktree",
        "no push",
        "commit authority",
        "production mutation authorization",
        "backup/restore",
        "source priority",
        "artifact/report paths",
        "status/checklist update",
        "current/next routing",
        "quality gates",
        "token economy",
        "stop/block conditions",
        "historical evidence preservation",
    }
)

REQUIRED_CANONICAL_PATHS = frozenset(
    {
        "project_docs/README.md",
        "project_control/status/CURRENT_STATUS.md",
        "project_control/status/HANDOFF.md",
        "project_control/planning/WP_REGISTRY.md",
        "project_control/manifests/DOCS_MAP.md",
        "app/contracts/coach/coach-domain-model.json",
        "app/contracts/coach/prompts/impact_leak_hypothesis_prompt.md",
        "app/contracts/coach/prompts/bad_fight_selection_hypothesis_prompt.md",
        "app/contracts/coach/schemas/ai-domain-hypothesis.schema.json",
        "app/contracts/coach/schemas/coach-domain-evidence.schema.json",
        "app/contracts/db/current_schema_baseline.json",
        "app/contracts/metrics/registry/metrics.json",
        "app/contracts/metrics/registry/metric-registry.schema.json",
    }
)

MIGRATION_EVIDENCE_TOOLS = frozenset({"scripts/r02a2_documentation_migration.py"})
READ_METHODS = frozenset({"read_text", "read_bytes"})
WRITE_METHODS = frozenset(
    {
        "write_text",
        "write_bytes",
        "touch",
        "mkdir",
        "unlink",
        "rename",
        "replace",
        "rmdir",
    }
)


@dataclass(frozen=True, order=True)
class GuardrailError:
    code: str
    path: str
    detail: str


def _git_paths(root: Path, *args: str) -> set[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return {line for line in result.stdout.splitlines() if line}


def repository_paths(root: Path) -> set[str]:
    return _git_paths(root, "ls-files") | _git_paths(root, "ls-files", "--others", "--exclude-standard")


def _is_runtime_material(path: str) -> bool:
    relative = Path(path)
    lowered_parts = {part.lower() for part in relative.parts}
    lowered_name = relative.name.lower()
    return (
        relative.suffix.lower() in {".json", ".yaml", ".yml"}
        or "prompts" in lowered_parts
        or "schemas" in lowered_parts
        or ".schema." in lowered_name
        or lowered_name.endswith("_prompt.md")
    )


def layout_errors(root: Path, paths: set[str]) -> list[GuardrailError]:
    errors: list[GuardrailError] = []
    docs_paths = {path for path in paths if path.startswith("docs/")}
    for path in sorted(docs_paths - DOCS_ALLOWLIST):
        errors.append(GuardrailError("docs_file_not_allowlisted", path, "compatibility shell is limited to six files"))
    if len(docs_paths) > len(DOCS_ALLOWLIST):
        errors.append(
            GuardrailError(
                "docs_file_count_exceeded",
                "docs/",
                f"found {len(docs_paths)} files; maximum is {len(DOCS_ALLOWLIST)}",
            )
        )

    for path in sorted(docs_paths):
        if _is_runtime_material(path):
            errors.append(
                GuardrailError("runtime_contract_under_docs", path, "runtime contracts belong under app/contracts")
            )
        if path == "docs/metrics/AGENTS.md":
            continue
        file_path = root / path
        if file_path.is_file():
            content = file_path.read_text(encoding="utf-8")
            if len(content.splitlines()) > 50 or "DO NOT WRITE" not in content:
                errors.append(
                    GuardrailError(
                        "current_narrative_under_docs", path, "compatibility files must remain short pointer stubs"
                    )
                )

    for path in sorted(path for path in paths if path.startswith("project_docs/")):
        if _is_runtime_material(path):
            errors.append(
                GuardrailError(
                    "runtime_material_under_project_docs",
                    path,
                    "runtime prompts and schemas belong under app/contracts",
                )
            )

    service_root = root / "app" / "services"
    if service_root.is_dir():
        for module in sorted(service_root.glob("*.py")):
            if module.name not in ROOT_SERVICE_MODULE_ALLOWLIST:
                errors.append(
                    GuardrailError(
                        "root_service_module_not_allowlisted",
                        module.relative_to(root).as_posix(),
                        "new services require an explicit architecture-policy update or a bounded package",
                    )
                )
    return errors


def source_of_truth_errors(root: Path) -> list[GuardrailError]:
    errors: list[GuardrailError] = []
    for path in sorted(REQUIRED_CANONICAL_PATHS):
        if not (root / path).is_file():
            errors.append(
                GuardrailError("canonical_path_missing", path, "required post-migration source of truth is absent")
            )
    return errors


def _path_value(node: ast.AST, names: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.replace("\\", "/")
    if isinstance(node, ast.Name):
        return names.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _path_value(node.left, names)
        right = _path_value(node.right, names)
        if right is None:
            return left
        if left in {None, "."}:
            return right
        return f"{left.rstrip('/')}/{right.lstrip('/')}"
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "Path" and node.args:
            return _path_value(node.args[0], names)
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"resolve", "absolute"}:
            return _path_value(node.func.value, names)
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        return _path_value(node.value, names)
    return None


def _zone(path: str | None) -> str | None:
    if path is None:
        return None
    normalized = path.replace("\\", "/").lstrip("./")
    if normalized == "docs" or normalized.startswith("docs/") or "/docs/" in normalized:
        return "docs"
    if (
        normalized == "_legacy_archive"
        or normalized.startswith("_legacy_archive/")
        or "/_legacy_archive/" in normalized
    ):
        return "archive"
    return None


def _open_kind(call: ast.Call, names: dict[str, str]) -> tuple[str, str | None] | None:
    if isinstance(call.func, ast.Name) and call.func.id == "open" and call.args:
        path = _path_value(call.args[0], names)
        mode_node = (
            call.args[1]
            if len(call.args) > 1
            else next(
                (keyword.value for keyword in call.keywords if keyword.arg == "mode"),
                None,
            )
        )
        mode = _path_value(mode_node, names) if mode_node is not None else "r"
        kind = "write" if mode and any(flag in mode for flag in "wax+") else "read"
        return kind, path
    if not isinstance(call.func, ast.Attribute):
        return None
    method = call.func.attr
    if method in READ_METHODS:
        return "read", _path_value(call.func.value, names)
    if method in WRITE_METHODS:
        return "write", _path_value(call.func.value, names)
    if method == "open":
        path = _path_value(call.func.value, names)
        mode_node = (
            call.args[0]
            if call.args
            else next(
                (keyword.value for keyword in call.keywords if keyword.arg == "mode"),
                None,
            )
        )
        mode = _path_value(mode_node, names) if mode_node is not None else "r"
        kind = "write" if mode and any(flag in mode for flag in "wax+") else "read"
        return kind, path
    return None


class _FileIOVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: dict[str, str] = {"ROOT": "."}
        self.operations: list[tuple[str, str, int]] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        value = _path_value(node.value, self.names)
        if value is not None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.names[target.id] = value
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.value is not None:
            value = _path_value(node.value, self.names)
            if value is not None:
                self.names[node.target.id] = value
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        operation = _open_kind(node, self.names)
        if operation is not None and operation[1] is not None:
            self.operations.append((operation[0], operation[1], node.lineno))
        self.generic_visit(node)


def python_io_errors(root: Path, paths: set[str]) -> list[GuardrailError]:
    errors: list[GuardrailError] = []
    active_python = sorted(
        path for path in paths if path.endswith(".py") and (path.startswith("app/") or path.startswith("scripts/"))
    )
    for path in active_python:
        if path in MIGRATION_EVIDENCE_TOOLS:
            continue
        file_path = root / path
        if not file_path.is_file():
            continue
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=path)
        except SyntaxError as exc:
            errors.append(GuardrailError("python_ast_parse_failed", path, f"line {exc.lineno}"))
            continue
        visitor = _FileIOVisitor()
        visitor.visit(tree)
        for kind, target, lineno in visitor.operations:
            zone = _zone(target)
            if kind == "write" and zone == "docs":
                errors.append(GuardrailError("docs_stub_writer", path, f"line {lineno}: {target}"))
            if kind == "read" and path.startswith("app/") and zone == "docs":
                errors.append(GuardrailError("runtime_docs_read", path, f"line {lineno}: {target}"))
            if kind == "read" and path.startswith("app/") and zone == "archive":
                errors.append(GuardrailError("runtime_archive_read", path, f"line {lineno}: {target}"))
            if kind == "read" and path.startswith("scripts/") and zone == "archive":
                errors.append(GuardrailError("active_control_archive_read", path, f"line {lineno}: {target}"))
    return errors


def _literal_assignment(tree: ast.Module, name: str) -> object | None:
    for node in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if isinstance(target, ast.Name) and target.id == name and value is not None:
            try:
                return ast.literal_eval(value)
            except (ValueError, TypeError):
                return None
    return None


def domain_policy_errors(root: Path) -> list[GuardrailError]:
    path = "app/services/coach_domain_model.py"
    file_path = root / path
    if not file_path.is_file():
        return [GuardrailError("canonical_domain_source_missing", path, "runtime domain source is absent")]
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=path)
    errors: list[GuardrailError] = []
    domains = _literal_assignment(tree, "CANONICAL_COACH_DOMAINS")
    if tuple(domains or ()) != CANONICAL_COACH_DOMAINS:
        errors.append(GuardrailError("noncanonical_coach_domains", path, f"expected {CANONICAL_COACH_DOMAINS!r}"))
    mission_model = _literal_assignment(tree, "ACTIVE_MISSION_MODEL")
    if mission_model != ACTIVE_MISSION_MODEL:
        errors.append(
            GuardrailError("global_cross_domain_mission_suppression", path, f"expected {ACTIVE_MISSION_MODEL}")
        )
    invariants = _literal_assignment(tree, "COACH_DOMAIN_INVARIANTS")
    if not isinstance(invariants, tuple) or DOMAIN_SUPPRESSION_INVARIANT not in invariants:
        errors.append(
            GuardrailError("global_cross_domain_mission_suppression", path, "same-domain suppression invariant missing")
        )
    return errors


def agent_principle_parity_errors(root: Path) -> list[GuardrailError]:
    parity_path = root / "project_control/manifests/AGENT_PRINCIPLE_PARITY.md"
    protocol_path = root / "project_control/agents/PROJECT_OPERATING_PROTOCOL.md"
    errors: list[GuardrailError] = []
    if not parity_path.is_file():
        return [
            GuardrailError(
                "agent_principle_parity_missing",
                parity_path.relative_to(root).as_posix(),
                "the canonical 13-principle matrix is absent",
            )
        ]
    content = parity_path.read_text(encoding="utf-8")
    principles = []
    for line in content.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or cells[0] in {"Principle", "---"}:
            continue
        principles.append(cells[0])
    found = set(principles)
    if found != REQUIRED_AGENT_PRINCIPLES or len(principles) != len(REQUIRED_AGENT_PRINCIPLES):
        errors.append(
            GuardrailError(
                "agent_principle_matrix_incomplete",
                parity_path.relative_to(root).as_posix(),
                f"expected 13 unique principles; found {len(principles)} rows and {len(found)} unique labels",
            )
        )
    if "Parity result: `PASS`" not in content:
        errors.append(
            GuardrailError(
                "agent_principle_parity_not_pass",
                parity_path.relative_to(root).as_posix(),
                "the canonical matrix does not declare PASS",
            )
        )
    if protocol_path.is_file():
        protocol = protocol_path.read_text(encoding="utf-8")
        if "User performs\n`git add`, commit and push." in protocol:
            errors.append(
                GuardrailError(
                    "conflicting_active_agent_principle",
                    protocol_path.relative_to(root).as_posix(),
                    "superseded user-only commit/push policy remains active",
                )
            )
    return errors


def collect_errors(root: Path = ROOT, *, paths: set[str] | None = None) -> list[GuardrailError]:
    active_paths = repository_paths(root) if paths is None else paths
    return sorted(
        [
            *layout_errors(root, active_paths),
            *source_of_truth_errors(root),
            *python_io_errors(root, active_paths),
            *domain_policy_errors(root),
            *agent_principle_parity_errors(root),
        ]
    )


def main() -> int:
    errors = collect_errors()
    if errors:
        print("R02A2_REPOSITORY_GUARDRAILS=FAIL")
        for error in errors:
            print(f"GUARDRAIL_ERROR={error.code}:{error.path}:{error.detail}")
        return 1
    print("DOCS_TRACKED_FILE_COUNT=6")
    print("RUNTIME_DOCS_DEPENDENCIES=0")
    print("ARCHIVE_RUNTIME_DEPENDENCIES=0")
    print("ACTIVE_WRITERS_TO_DOCS_STUBS=0")
    print("CANONICAL_DOMAIN_POLICY=PASS")
    print("AGENT_PRINCIPLE_PARITY=PASS")
    print("SOURCE_OF_TRUTH_PATHS=PASS")
    print("R02A2_REPOSITORY_GUARDRAILS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
