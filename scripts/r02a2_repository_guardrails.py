#!/usr/bin/env python3
"""Enforce post-R02A2 repository layout and active file-I/O boundaries."""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCS_ALLOWLIST = frozenset(
    {
        "docs/README.md",
        "docs/metrics/AGENTS.md",
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
        "project_control/planning/VERSION_ROADMAP.md",
        "project_control/planning/WORK_PACKAGE_BACKLOG.md",
        "project_control/planning/WP_REGISTRY.md",
        "project_control/checklists/MASTER_WP_CHECKLIST.md",
        "project_control/manifests/DOCS_MAP.md",
        "README.md",
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

TRADE_DOCUMENTS = (
    "project_docs/product/AI_COACH.md",
    "project_docs/product/CS2_DOMAIN_CONTRACT.md",
    "project_docs/product/KNOWN_LIMITATIONS.md",
    "project_docs/product/RECOMMENDATIONS.md",
    "project_docs/architecture/ARCHITECTURE.md",
    "project_docs/architecture/API_CONTRACTS.md",
    "project_docs/metrics/METRICS.md",
)

DYNAMIC_ROUTE_PATTERNS = (
    re.compile(r"\bCURRENT_TASK\s*:", re.IGNORECASE),
    re.compile(r"\bNEXT_TASK(?:_GATED)?\s*:", re.IGNORECASE),
    re.compile(r"\bR02A3_MAY_START\s*:", re.IGNORECASE),
    re.compile(r"\bthe (?:required )?next (?:task|lane|work package|WP)\b", re.IGNORECASE),
    re.compile(r"\brequired next lane\b", re.IGNORECASE),
    re.compile(r"^#{1,6}\s+Next Work\s*$", re.IGNORECASE | re.MULTILINE),
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
    candidates = _git_paths(root, "ls-files") | _git_paths(root, "ls-files", "--others", "--exclude-standard")
    return {path for path in candidates if (root / path).is_file() or (root / path).is_symlink()}


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
        errors.append(GuardrailError("docs_file_not_allowlisted", path, "compatibility shell is limited to two files"))
    if len(docs_paths) > len(DOCS_ALLOWLIST):
        errors.append(
            GuardrailError(
                "docs_file_count_exceeded",
                "docs/",
                f"found {len(docs_paths)} files; required allowlist has {len(DOCS_ALLOWLIST)}",
            )
        )

    for path in sorted(docs_paths):
        if _is_runtime_material(path):
            errors.append(
                GuardrailError("runtime_contract_under_docs", path, "runtime contracts belong under app/contracts")
            )
        if (
            path.startswith("docs/metrics/")
            and path != "docs/metrics/AGENTS.md"
            and not _is_runtime_material(path)
        ):
            errors.append(
                GuardrailError(
                    "metric_human_doc_under_docs",
                    path,
                    "human metric documentation belongs under project_docs/metrics",
                )
            )
        if path.startswith("docs/project_management/") or Path(path).name in {
            "CURRENT_STATUS.md",
            "HANDOFF.md",
            "WP_REGISTRY.md",
            "VERSION_ROADMAP.md",
            "WORK_PACKAGE_BACKLOG.md",
            "MASTER_WP_CHECKLIST.md",
        }:
            errors.append(
                GuardrailError(
                    "current_control_file_under_docs",
                    path,
                    "active route, planning, and checklist truth belongs under project_control",
                )
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

    docs_root = root / "docs"
    if docs_root.is_dir():
        for directory in sorted(path for path in docs_root.rglob("*") if path.is_dir()):
            if not any(directory.iterdir()):
                errors.append(
                    GuardrailError(
                        "empty_docs_directory",
                        directory.relative_to(root).as_posix(),
                        "obsolete empty documentation directories must be removed",
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


def current_markdown_content(content: str) -> str:
    """Return active prose while excluding explicit historical/superseded sections."""
    current: list[str] = []
    excluded_level: int | None = None
    for line in content.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2)
            if excluded_level is not None and level <= excluded_level:
                excluded_level = None
            if re.search(r"\b(?:historical|superseded)\b", title, re.IGNORECASE):
                excluded_level = level
                continue
        if excluded_level is None:
            current.append(line)
    return "\n".join(current)


def durable_doc_route_errors(root: Path) -> list[GuardrailError]:
    errors: list[GuardrailError] = []
    docs_root = root / "project_docs"
    if not docs_root.is_dir():
        return errors
    for file_path in sorted(docs_root.rglob("*.md")):
        path = file_path.relative_to(root).as_posix()
        content = current_markdown_content(file_path.read_text(encoding="utf-8"))
        if any(pattern.search(content) for pattern in DYNAMIC_ROUTE_PATTERNS):
            errors.append(
                GuardrailError(
                    "dynamic_route_in_durable_docs",
                    path,
                    "current task/next-task routing belongs under project_control",
                )
            )
    return errors


def current_document_contract_errors(root: Path) -> list[GuardrailError]:
    errors: list[GuardrailError] = []

    def read(path: str) -> str:
        file_path = root / path
        if not file_path.is_file():
            errors.append(GuardrailError("current_document_missing", path, "required semantic owner is absent"))
            return ""
        return current_markdown_content(file_path.read_text(encoding="utf-8"))

    def normalized(content: str) -> str:
        return " ".join(content.split())

    domain_path = "project_docs/product/CANONICAL_COACH_DOMAIN_MODEL.md"
    domain = read(domain_path)
    domain_normalized = normalized(domain)
    domain_requirements = (
        "exactly two MVP coach domains",
        "`impact_leak`",
        "`bad_fight_selection`",
        "`performance`, `utility`, and `aim` are metric groups",
        "They are not product domains",
        "`utility_value`",
        "`context-only`",
    )
    if domain and any(marker not in domain_normalized for marker in domain_requirements):
        errors.append(
            GuardrailError(
                "current_domain_document_parity",
                domain_path,
                "two domains, metric-group-only labels, or utility_value context-only rule is missing",
            )
        )

    for path in TRADE_DOCUMENTS:
        content = read(path)
        lowered = normalized(content).lower()
        if content and "bounded aggregate" not in lowered:
            errors.append(
                GuardrailError(
                    "trade_document_missing_bounded_capability",
                    path,
                    "validated bounded aggregate trade capability must remain explicit",
                )
            )
        if content and not any(marker in lowered for marker in ("spatial", "exact position", "spacing")):
            errors.append(
                GuardrailError(
                    "trade_document_missing_no_spatial_limit",
                    path,
                    "trade evidence must not imply spatial or individual tactical cause",
                )
            )

    ai_path = "project_docs/product/AI_COACH.md"
    ai = read(ai_path)
    ai_normalized = normalized(ai)
    ai_markers = (
        "versioned domain prompts",
        "strict `ai-domain-hypothesis-v1` structured-output schema",
        "registered metric and semantic version",
        "exact metric values",
        "baseline match IDs",
        "Rejected attempts remain append-only evidence",
        "provider, model and route provenance",
    )
    if ai and any(marker not in ai_normalized for marker in ai_markers):
        errors.append(
            GuardrailError(
                "ai_contract_documentation_parity",
                ai_path,
                "R02 version/schema/value/reference/lineage/provenance behavior is incomplete",
            )
        )
    if ai and re.search(
        r"(?:prompt versioning|semantic (?:validation|checks|evals?)|structured output).{0,80}(?:future|planned)",
        ai_normalized,
        re.IGNORECASE,
    ):
        errors.append(
            GuardrailError(
                "implemented_ai_contract_described_as_future",
                ai_path,
                "R02 prompt/schema/semantic validation is already implemented",
            )
        )

    steam_path = "project_docs/operations/STEAM_IMPORT.md"
    steam = read(steam_path)
    steam_normalized = normalized(steam)
    if steam and (
        "Steam import is accepted with warnings for controlled personal use." not in steam_normalized
        or "Accepted capabilities:" not in steam_normalized
        or "Remaining limitations:" not in steam_normalized
        or re.search(r"acceptance\s+is\s+blocked", steam_normalized, re.IGNORECASE)
    ):
        errors.append(
            GuardrailError(
                "steam_import_documentation_parity",
                steam_path,
                "current accepted capabilities and remaining limitations must be unambiguous",
            )
        )

    testing_path = "project_docs/operations/TESTING.md"
    testing = read(testing_path)
    testing_normalized = normalized(testing)
    if testing and (
        "accepted general local CI-equivalent gate for JC Coach" not in testing_normalized
        or "focused" not in testing_normalized.lower()
        or "full safe pytest" not in testing_normalized.lower()
        or "restricted foundation-hardening lane" in testing_normalized.lower()
    ):
        errors.append(
            GuardrailError(
                "testing_documentation_parity",
                testing_path,
                "the general focused/full local quality gate contract is missing or foundation-owned",
            )
        )

    return errors


def planning_contract_errors(root: Path) -> list[GuardrailError]:
    """Keep the macro route, detailed plan, registry, and checklist aligned."""
    errors: list[GuardrailError] = []

    def read(path: str) -> str:
        file_path = root / path
        if not file_path.is_file():
            errors.append(GuardrailError("planning_document_missing", path, "canonical planning owner is absent"))
            return ""
        return file_path.read_text(encoding="utf-8")

    roadmap_path = "project_control/planning/VERSION_ROADMAP.md"
    backlog_path = "project_control/planning/WORK_PACKAGE_BACKLOG.md"
    registry_path = "project_control/planning/WP_REGISTRY.md"
    checklist_path = "project_control/checklists/MASTER_WP_CHECKLIST.md"
    roadmap = read(roadmap_path)
    backlog = read(backlog_path)
    registry = read(registry_path)
    checklist = read(checklist_path)

    roadmap_markers = (
        "personal CS2 AI Coach",
        "exactly two canonical coaching domains",
        "## C. Current milestone",
        "## D. Functional MVP milestone",
        "## E. End-to-end acceptance milestone",
        "## F. Live personal beta milestone",
        "## G. Visual Product milestone",
        "## H. Operational hardening milestone",
        "## I. Later/public scope",
        "30-match immutable baseline",
        "10 subsequent matches",
        "no third coach domain",
    )
    if roadmap and any(marker not in roadmap for marker in roadmap_markers):
        errors.append(
            GuardrailError(
                "roadmap_macro_contract_incomplete",
                roadmap_path,
                "Product goal, R02A3-R07 milestones, two-domain boundary, or 30+10 acceptance is missing",
            )
        )
    sequence = ("R02A3", "R03", "R04", "R05", "R06", "R07")
    positions = [roadmap.find(marker) for marker in sequence]
    canonical_sequence = "R02A3 → R03 → R04 → R05 planned → R06 planned → R07 deferred/planned"
    normalized_roadmap = " ".join(roadmap.split())
    if roadmap and (
        any(position < 0 for position in positions)
        or positions != sorted(positions)
        or canonical_sequence not in normalized_roadmap
    ):
        errors.append(
            GuardrailError(
                "roadmap_sequence_invalid",
                roadmap_path,
                "required sequence is R02A3 -> R03 -> R04 -> R05 -> R06 -> R07",
            )
        )
    functional = roadmap.find("## D. Functional MVP milestone")
    visual = roadmap.find("## G. Visual Product milestone")
    if roadmap and (functional < 0 or visual < 0 or functional >= visual):
        errors.append(
            GuardrailError(
                "visual_polish_before_functional_mvp",
                roadmap_path,
                "functional MVP acceptance must precede visual polish",
            )
        )

    backlog_markers = (
        "## H01B-R02A3 — next",
        "## H01B-R03 — pending",
        "## H01B-R04 — pending",
        "## H01B-R05 — planned, not authorized",
        "## H01B-R06 — planned, not authorized",
        "## H01B-R07 — deferred/planned",
        "**Explicit non-goals:**",
        "WP-018",
        "historical or superseded",
    )
    if backlog and any(marker not in backlog for marker in backlog_markers):
        errors.append(
            GuardrailError(
                "work_package_backlog_incomplete",
                backlog_path,
                "R02A3-R07 detail, explicit non-goals, or historical disposition is missing",
            )
        )

    registry_markers = (
        "CURRENT_TASK: `none`",
        "NEXT_TASK: `H01B-R02A3_CODEBASE_SERVICE_BOUNDARY_CONSOLIDATION`",
        "NEXT_TASK_GATED: `false`",
        "| H01B-R02A3 | next |",
        "| H01B-R03 | pending |",
        "| H01B-R04 | pending |",
        "| H01B-R05 | planned |",
        "| H01B-R06 | planned |",
        "| H01B-R07 | deferred_planned |",
    )
    if registry and any(marker not in registry for marker in registry_markers):
        errors.append(
            GuardrailError(
                "wp_registry_route_incomplete",
                registry_path,
                "exact current/next route or R02A3-R07 statuses are missing",
            )
        )

    checklist_markers = (
        "| Foundation/safety | completed |",
        "| Import/parser/owner loop | completed |",
        "| Metric correctness | completed |",
        "| Two-domain backend | completed |",
        "| Real LLM proposals | completed |",
        "| Documentation/control migration | completed |",
        "| Codebase architecture cleanup | next |",
        "| Functional mission UI | pending |",
        "| 30+10 replay | pending |",
        "| Live personal beta | planned |",
        "| Visual polish | planned |",
        "| Provider/ops hardening | deferred_planned |",
        "| Public/multi-user work | later |",
    )
    if checklist and any(marker not in checklist for marker in checklist_markers):
        errors.append(
            GuardrailError(
                "master_checklist_registry_mismatch",
                checklist_path,
                "milestone statuses contradict or incompletely reflect WP_REGISTRY",
            )
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
            *durable_doc_route_errors(root),
            *current_document_contract_errors(root),
            *planning_contract_errors(root),
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
    print("DOCS_TRACKED_FILE_COUNT=2")
    print("METRIC_RUNTIME_ASSETS_UNDER_DOCS=0")
    print("METRIC_HUMAN_DOCS_UNDER_DOCS=0")
    print("EMPTY_DOCS_DIRECTORIES=0")
    print("RUNTIME_DOCS_DEPENDENCIES=0")
    print("ARCHIVE_RUNTIME_DEPENDENCIES=0")
    print("ACTIVE_WRITERS_TO_DOCS_STUBS=0")
    print("CANONICAL_DOMAIN_POLICY=PASS")
    print("AGENT_PRINCIPLE_PARITY=PASS")
    print("SOURCE_OF_TRUTH_PATHS=PASS")
    print("DURABLE_DOCS_CONTROL_PLANE_SEPARATION=PASS")
    print("CURRENT_DOCUMENT_CONTRACT_PARITY=PASS")
    print("ROADMAP_REGISTRY_CHECKLIST_PARITY=PASS")
    print("R02A2_REPOSITORY_GUARDRAILS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
