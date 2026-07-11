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
    "recommendation_tracking": "coach",
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
        "match_phase": "app.services.parsing.match_phase",
        "match_processing": "app.services.owner.match_processing",
        "match_queries": "app.services.shared.match_queries",
        "metric_confidence": "app.services.metrics.confidence",
        "metric_downstream_state": "app.services.metrics.downstream",
        "metric_snapshots": "app.services.metrics.snapshots",
        "metric_truth": "app.services.shared.metric_policy",
        "mistake_detection": "app.services.coach.mistakes",
        "parser_artifact_reader": "app.services.parsing.artifact_reader",
        "parser_evidence": "app.services.parsing.evidence",
        "recommendation_tracking": "app.services.coach.recommendations",
        "report_generator": "app.services.coach.reports",
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
    }
    if args.inventory:
        result["imports"] = {key: sorted(value) for key, value in sorted(graph.edges.items())}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
