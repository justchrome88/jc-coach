import json
from pathlib import Path

from scripts.metrics_registry import render_catalog, validate_registry

ROOT = Path(__file__).resolve().parents[1]


def test_registry_validates_and_catalog_is_reproducible() -> None:
    registry = json.loads((ROOT / "docs/metrics/registry/metrics.json").read_text())
    schema = json.loads((ROOT / "docs/metrics/registry/metric-registry.schema.json").read_text())

    assert validate_registry(registry, schema) == []
    assert (ROOT / "docs/metrics/generated/METRIC_CATALOG.md").read_text() == render_catalog(registry)


def test_disputed_metrics_do_not_claim_verified_ground_truth() -> None:
    registry = json.loads((ROOT / "docs/metrics/registry/metrics.json").read_text())
    by_key = {metric["metric_key"]: metric for metric in registry["metrics"]}

    for key in ("kills", "deaths", "kd_ratio", "damage", "adr", "rounds", "kast", "survival_rate"):
        assert by_key[key]["ground_truth_status"] == "disputed"
