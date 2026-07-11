#!/usr/bin/env python3
"""Validate the canonical metric registry and generate its Markdown catalog."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/metrics/registry/metrics.json"
SCHEMA = ROOT / "docs/metrics/registry/metric-registry.schema.json"
CATALOG = ROOT / "docs/metrics/generated/METRIC_CATALOG.md"
GROUND_TRUTH = {"verified", "partially_verified", "disputed", "unknown", "not_applicable"}
STATUSES = {"active", "experimental", "deprecated", "blocked"}
CLASSIFICATIONS = {
    "validated_candidate", "confirmed_defect", "semantic_difference",
    "disputed_missing_evidence", "experimental", "deprecated",
}
VALIDATION_STATUSES = {"validated", "quarantined", "rejected", "unavailable"}
CONSUMER_POLICIES = {"trusted", "label_semantic_difference", "unavailable", "forbidden"}


def validate_registry(registry: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = schema["properties"]["metrics"]["items"]["required"]
    allowed = set(schema["properties"]["metrics"]["items"]["properties"])
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(registry.get("registry_version") or "")):
        errors.append("registry_version must be semantic x.y.z")
    metrics = registry.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        return [*errors, "metrics must be a non-empty array"]
    keys: set[str] = set()
    for index, metric in enumerate(metrics):
        path = f"metrics[{index}]"
        if not isinstance(metric, dict):
            errors.append(f"{path} must be an object")
            continue
        errors.extend(f"{path} missing {field}" for field in required if field not in metric)
        errors.extend(f"{path} unknown {field}" for field in metric if field not in allowed)
        key = metric.get("metric_key")
        if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            errors.append(f"{path}.metric_key is invalid")
        elif key in keys:
            errors.append(f"duplicate metric_key {key}")
        else:
            keys.add(key)
        if metric.get("ground_truth_status") not in GROUND_TRUTH:
            errors.append(f"{path}.ground_truth_status is invalid")
        if metric.get("status") not in STATUSES:
            errors.append(f"{path}.status is invalid")
        if metric.get("classification") not in CLASSIFICATIONS:
            errors.append(f"{path}.classification is invalid")
        if metric.get("validation_status") not in VALIDATION_STATUSES:
            errors.append(f"{path}.validation_status is invalid")
        if metric.get("consumer_policy") not in CONSUMER_POLICIES:
            errors.append(f"{path}.consumer_policy is invalid")
        if not isinstance(metric.get("critical"), bool):
            errors.append(f"{path}.critical must be boolean")
        if metric.get("critical") and metric.get("validation_status") not in VALIDATION_STATUSES:
            errors.append(f"{path} critical metric must be validated or quarantined")
        if metric.get("critical") and "owner_user_id" not in metric.get("identity_keys", []):
            errors.append(f"{path} critical metric identity must include owner_user_id")
        if metric.get("critical") and "semantic_version" not in metric.get("identity_keys", []):
            errors.append(f"{path} critical metric identity must include semantic_version")
        if not re.fullmatch(r"\d+\.\d+\.\d+", str(metric.get("semantic_version") or "")):
            errors.append(f"{path}.semantic_version must be x.y.z")
        for field, definition in schema["properties"]["metrics"]["items"]["properties"].items():
            if definition.get("type") == "array" and not isinstance(metric.get(field), list):
                errors.append(f"{path}.{field} must be an array")
    return errors


def render_catalog(registry: dict[str, Any]) -> str:
    lines = [
        "# Metric Catalog",
        "",
        "Generated from `docs/metrics/registry/metrics.json`; do not edit by hand.",
        "",
        f"Registry version: `{registry['registry_version']}`. Metrics: `{len(registry['metrics'])}`.",
        "",
        "| Metric | Domain / scope | Unit | Semantics | Truth | Validation | Status | Persistence | Consumers |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for metric in sorted(registry["metrics"], key=lambda item: (item["domain"], item["metric_key"])):
        semantics = metric["numerator_definition"] or "source value / not applicable"
        if metric["denominator_definition"]:
            semantics += f" / {metric['denominator_definition']}"
        persistence = ", ".join(metric["persistence_targets"]) or "none"
        consumers = ", ".join([*metric["ui_consumers"], *metric["coach_consumers"]]) or "none"
        values = [
            f"`{metric['metric_key']}` — {metric['display_name']}",
            f"{metric['domain']} / {metric['scope']}",
            metric["unit"],
            semantics,
            metric["ground_truth_status"],
            f"{metric['validation_status']} / {metric['consumer_policy']}",
            f"{metric['status']} (`{metric['semantic_version']}`)",
            persistence,
            consumers,
        ]
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
    lines.extend(["", "Validation: `.venv/bin/python scripts/metrics_registry.py --check`.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="also require the generated catalog to be current")
    parser.add_argument("--write", action="store_true", help="write the generated catalog")
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text())
    schema = json.loads(SCHEMA.read_text())
    errors = validate_registry(registry, schema)
    if errors:
        raise SystemExit("registry validation failed:\n- " + "\n- ".join(errors))
    rendered = render_catalog(registry)
    if args.write:
        CATALOG.parent.mkdir(parents=True, exist_ok=True)
        CATALOG.write_text(rendered)
    if args.check and (not CATALOG.exists() or CATALOG.read_text() != rendered):
        raise SystemExit("generated metric catalog is stale")
    print(f"METRIC_REGISTRY_VALID metrics={len(registry['metrics'])} version={registry['registry_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
