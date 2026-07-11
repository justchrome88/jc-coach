#!/usr/bin/env python3
"""Validate the JC Coach application service dependency architecture."""

from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = ROOT / "app" / "services"

SERVICE_PACKAGES = (
    "ingestion",
    "parsing",
    "metrics",
    "coach",
    "missions",
    "owner",
    "shared",
)

TARGET_PACKAGE_BY_LEGACY_MODULE = {
    "ai_coach": "coach",
    "ai_validator": "coach",
    "aim_stats": "metrics",
    "analytics": "metrics",
    "app_settings": "ingestion",
    "artifact_integrity": "ingestion",
    "auth": "owner",
    "coach_domain_ai": "coach",
    "coach_domain_model": "approved_root_contract_loader",
    "coach_insights": "coach",
    "coach_metric_pack": "metrics",
    "coach_rules": "coach",
    "combat_event_derivation": "parsing",
    "core_combat_metrics": "metrics",
    "demo_parser": "parsing",
    "demo_retention": "shared",
    "demo_storage": "ingestion",
    "event_metric_dictionary": "parsing",
    "fresh_match_discovery": "ingestion",
    "i18n": "shared",
    "import_jobs": "ingestion",
    "import_orchestration": "ingestion",
    "importer": "ingestion",
    "match_phase": "parsing",
    "match_processing": "owner",
    "match_queries": "shared",
    "metric_confidence": "metrics",
    "metric_downstream_state": "metrics",
    "metric_snapshots": "metrics",
    "metric_truth": "shared",
    "mission_domain": "missions",
    "mistake_detection": "coach",
    "owner_coach_sync": "owner",
    "owner_coach_sync_batch": "owner",
    "owner_identity_reconciliation": "owner",
    "ownership": "owner",
    "parser_artifact_reader": "parsing",
    "parser_evidence": "parsing",
    "recommendation_tracking": "metrics",
    "report_generator": "coach",
    "security": "owner",
    "steam_demo_acquisition": "ingestion",
    "steam_demo_downloader": "ingestion",
    "steam_integration": "ingestion",
    "steam_match_metadata": "ingestion",
    "steam_storage_guard": "ingestion",
    "utility_metrics": "metrics",
    "weapon_names": "shared",
}

CANONICAL_MODULE_BY_LEGACY_MODULE = {
    legacy: f"app.services.{legacy}" for legacy in TARGET_PACKAGE_BY_LEGACY_MODULE
}
CANONICAL_MODULE_BY_LEGACY_MODULE.update(
    {
        "app_settings": "app.services.ingestion.settings",
        "artifact_integrity": "app.services.ingestion.artifact_integrity",
        "ai_coach": "app.services.coach.ai",
        "ai_validator": "app.services.coach.validation",
        "auth": "app.services.owner.auth",
        "aim_stats": "app.services.metrics.aim",
        "analytics": "app.services.metrics.analytics",
        "coach_metric_pack": "app.services.metrics.coach_pack",
        "coach_domain_ai": "app.services.coach.domain_analysis",
        "coach_insights": "app.services.coach.insights",
        "coach_rules": "app.services.coach.rules",
        "combat_event_derivation": "app.services.parsing.combat_events",
        "core_combat_metrics": "app.services.metrics.combat",
        "demo_parser": "app.services.parsing.demo_parser",
        "demo_retention": "app.services.shared.demo_retention",
        "demo_storage": "app.services.ingestion.demo_storage",
        "event_metric_dictionary": "app.services.parsing.event_dictionary",
        "fresh_match_discovery": "app.services.ingestion.discovery",
        "import_jobs": "app.services.ingestion.jobs",
        "import_orchestration": "app.services.ingestion.orchestration",
        "importer": "app.services.ingestion.structured_import",
        "i18n": "app.services.shared.i18n",
        "match_phase": "app.services.parsing.match_phase",
        "match_processing": "app.services.owner.match_processing",
        "match_queries": "app.services.shared.match_queries",
        "metric_confidence": "app.services.metrics.confidence",
        "metric_downstream_state": "app.services.metrics.downstream",
        "metric_snapshots": "app.services.metrics.snapshots",
        "metric_truth": "app.services.shared.metric_policy",
        "mission_domain": "app.services.missions.lifecycle",
        "mistake_detection": "app.services.coach.mistakes",
        "owner_coach_sync": "app.services.owner.sync",
        "owner_coach_sync_batch": "app.services.owner.sync_batch",
        "owner_identity_reconciliation": "app.services.owner.reconciliation",
        "ownership": "app.services.owner.scope",
        "parser_artifact_reader": "app.services.parsing.artifact_reader",
        "parser_evidence": "app.services.parsing.evidence",
        "recommendation_tracking": "app.services.metrics.recommendations",
        "report_generator": "app.services.coach.reports",
        "security": "app.services.owner.security",
        "steam_demo_acquisition": "app.services.ingestion.demo_acquisition",
        "steam_demo_downloader": "app.services.ingestion.demo_downloader",
        "steam_integration": "app.services.ingestion.steam",
        "steam_match_metadata": "app.services.ingestion.match_metadata",
        "steam_storage_guard": "app.services.ingestion.storage_guard",
        "utility_metrics": "app.services.metrics.utility",
        "weapon_names": "app.services.shared.weapon_names",
    }
)

COMPATIBILITY_FACADES = {
    "app.services.ai_coach": "app.services.coach.ai",
    "app.services.coach_domain_ai": "app.services.coach.domain_analysis",
    "app.services.demo_parser": "app.services.parsing.demo_parser",
    "app.services.metric_snapshots": "app.services.metrics.snapshots",
    "app.services.mission_domain": "app.services.missions.lifecycle",
    "app.services.owner_coach_sync": "app.services.owner.sync",
    "app.services.steam_demo_downloader": "app.services.ingestion.demo_downloader",
    "app.services.steam_integration": "app.services.ingestion.steam",
    "app.services.steam_match_metadata": "app.services.ingestion.match_metadata",
}


@dataclass(frozen=True)
class ImportGraph:
    modules: dict[str, Path]
    edges: dict[str, set[str]]


def module_name(path: Path, *, root: Path = ROOT) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts)


def python_modules(paths: Iterable[Path], *, root: Path = ROOT) -> dict[str, Path]:
    return {module_name(path, root=root): path for path in paths}


def _resolve_import(candidate: str, known: set[str]) -> str | None:
    while candidate:
        if candidate in known:
            return candidate
        candidate = candidate.rpartition(".")[0]
    return None


def build_import_graph(paths: Iterable[Path], *, root: Path = ROOT) -> ImportGraph:
    modules = python_modules(paths, root=root)
    known = set(modules)
    edges: dict[str, set[str]] = defaultdict(set)
    for source, path in modules.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                candidates = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    package = source.split(".")[:-1]
                    prefix = package[: len(package) - node.level + 1]
                    base = ".".join(prefix + ([node.module] if node.module else []))
                else:
                    base = node.module or ""
                candidates = [f"{base}.{alias.name}" if base else alias.name for alias in node.names]
                candidates.append(base)
            else:
                continue
            for candidate in candidates:
                target = _resolve_import(candidate, known)
                if target is not None:
                    edges[source].add(target)
        edges.setdefault(source, set())
    return ImportGraph(modules=modules, edges=dict(edges))


def strongly_connected_components(graph: ImportGraph, *, prefix: str) -> list[list[str]]:
    nodes = sorted(module for module in graph.modules if module.startswith(prefix))
    node_set = set(nodes)
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in graph.edges.get(node, set()):
            if target not in node_set:
                continue
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] != indices[node]:
            return
        component: list[str] = []
        while True:
            target = stack.pop()
            on_stack.remove(target)
            component.append(target)
            if target == node:
                break
        if len(component) > 1 or node in graph.edges.get(node, set()):
            components.append(sorted(component))

    for node in nodes:
        if node not in indices:
            visit(node)
    return sorted(components)


def import_boundary_violations(graph: ImportGraph) -> list[str]:
    violations: list[str] = []
    forbidden = {
        "metrics": {"coach", "missions"},
        "ingestion": {"coach", "missions"},
        "parsing": {"coach", "missions"},
        "missions": {"provider"},
    }
    for source, targets in sorted(graph.edges.items()):
        source_parts = source.split(".")
        if source_parts[:2] != ["app", "services"] or len(source_parts) < 4:
            continue
        source_package = source_parts[2]
        for target in sorted(targets):
            target_parts = target.split(".")
            if target_parts[:2] != ["app", "services"] or len(target_parts) < 4:
                continue
            target_package = target_parts[2]
            if target_package in forbidden.get(source_package, set()):
                violations.append(f"forbidden_dependency:{source}->{target}")
            if source_package == "missions" and target == "app.services.coach.provider":
                violations.append(f"missions_import_provider:{source}->{target}")
    return violations


def root_service_module_violations(service_root: Path = SERVICE_ROOT) -> list[str]:
    allowed = {"__init__.py", "coach_domain_model.py"}
    allowed.update(f"{module.rsplit('.', 1)[-1]}.py" for module in COMPATIBILITY_FACADES)
    return [
        f"non_allowlisted_root_service_module:{path.name}"
        for path in sorted(service_root.glob("*.py"))
        if path.name not in allowed
    ]


def facade_file_contains_logic(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for index, node in enumerate(tree.body):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if (
            index == 0
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            continue
        if (
            isinstance(node, (ast.Assign, ast.AnnAssign))
            and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
            )
        ):
            continue
        return True
    return False


def compatibility_facade_violations(root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    for module in sorted(COMPATIBILITY_FACADES):
        path = root.joinpath(*module.split(".")).with_suffix(".py")
        if facade_file_contains_logic(path):
            violations.append(f"compatibility_facade_contains_logic:{module}")
    return violations


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def runtime_narrative_import_violations(paths: Iterable[Path], *, root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    forbidden = ("_legacy_archive", "docs", "project_docs", "project_control")
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                if module.startswith(forbidden):
                    violations.append(f"runtime_narrative_import:{_display_path(path, root)}:{module}")
    return violations


def private_cross_package_import_violations(paths: Iterable[Path], *, root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    for path in paths:
        source = module_name(path, root=root)
        source_parts = source.split(".")
        if source_parts[:2] != ["app", "services"] or len(source_parts) < 4:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            target_parts = node.module.split(".")
            if target_parts[:2] != ["app", "services"] or len(target_parts) < 4:
                continue
            if source_parts[2] == target_parts[2]:
                continue
            for alias in node.names:
                if alias.name.startswith("_"):
                    violations.append(f"private_cross_package_import:{source}->{node.module}.{alias.name}")
    return violations


def api_domain_calculation_violations(paths: Iterable[Path], *, root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            is_route = any(
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr in {"get", "post", "put", "patch", "delete"}
                for decorator in node.decorator_list
            )
            if is_route and any(
                isinstance(item, ast.BinOp) and not isinstance(item.op, ast.BitOr) for item in ast.walk(node)
            ):
                violations.append(f"api_route_domain_calculation:{_display_path(path, root)}:{node.name}")
    return violations


def contract_location_violations(root: Path = ROOT) -> list[str]:
    app_root = root / "app"
    contract_root = app_root / "contracts"
    return [
        f"runtime_contract_outside_app_contracts:{path.relative_to(root)}"
        for path in sorted(app_root.rglob("*.json"))
        if contract_root not in path.parents
    ]


def canonical_domain_violations(domains: Iterable[str]) -> list[str]:
    return [] if tuple(domains) == ("impact_leak", "bad_fight_selection") else ["canonical_coach_domains_not_exact"]


def mission_suppression_violations(source: str) -> list[str]:
    required = ("domain_key", "_active_mission_domain_keys")
    return [] if all(token in source for token in required) else ["global_cross_domain_mission_suppression"]


def architecture_violations(root: Path = ROOT) -> list[str]:
    service_paths = sorted((root / "app" / "services").rglob("*.py"))
    app_paths = sorted((root / "app").rglob("*.py"))
    graph = build_import_graph(service_paths, root=root)
    violations = [
        f"service_import_cycle:{','.join(cycle)}"
        for cycle in strongly_connected_components(graph, prefix="app.services")
    ]
    violations.extend(import_boundary_violations(graph))
    violations.extend(root_service_module_violations(root / "app" / "services"))
    violations.extend(compatibility_facade_violations(root))
    violations.extend(runtime_narrative_import_violations(app_paths, root=root))
    violations.extend(private_cross_package_import_violations(service_paths, root=root))
    violations.extend(
        api_domain_calculation_violations(
            sorted((root / "app" / "api" / "routes").glob("*.py")), root=root
        )
    )
    violations.extend(contract_location_violations(root))

    from app.services.coach_domain_model import CANONICAL_COACH_DOMAINS
    from app.services.missions import presentation

    violations.extend(canonical_domain_violations(CANONICAL_COACH_DOMAINS))
    violations.extend(mission_suppression_violations(Path(presentation.__file__).read_text(encoding="utf-8")))
    return sorted(set(violations))


def route_inventory() -> list[dict[str, object]]:
    from app.api.routes import router as api_router
    from app.main import app
    from app.web.routes import router as web_router

    rows: list[dict[str, object]] = []
    for source, routes in (("app", app.routes), ("api", api_router.routes), ("web", web_router.routes)):
        for route in routes:
            path = getattr(route, "path", None)
            if path is None:
                continue
            rows.append(
                {
                    "source": source,
                    "path": path,
                    "methods": sorted(getattr(route, "methods", set()) or set()),
                    "name": getattr(route, "name", ""),
                }
            )
    return sorted(rows, key=lambda row: (str(row["path"]), str(row["methods"]), str(row["name"]), str(row["source"])))


def route_fingerprint() -> str:
    import hashlib

    payload = json.dumps(route_inventory(), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", action="store_true")
    args = parser.parse_args()
    paths = sorted(SERVICE_ROOT.rglob("*.py"))
    graph = build_import_graph(paths)
    cycles = strongly_connected_components(graph, prefix="app.services")
    result = {
        "service_packages": list(SERVICE_PACKAGES),
        "target_package_by_legacy_module": TARGET_PACKAGE_BY_LEGACY_MODULE,
        "canonical_module_by_legacy_module": CANONICAL_MODULE_BY_LEGACY_MODULE,
        "compatibility_facades": COMPATIBILITY_FACADES,
        "cycles": cycles,
        "route_count": len(route_inventory()),
        "route_fingerprint": route_fingerprint(),
        "violations": architecture_violations(),
    }
    if args.inventory:
        result["imports"] = {key: sorted(value) for key, value in sorted(graph.edges.items())}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
