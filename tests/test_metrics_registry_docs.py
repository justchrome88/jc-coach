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

    for key in ("damage", "rounds"):
        assert by_key[key]["ground_truth_status"] == "disputed"

    for key in (
        "kills",
        "deaths",
        "kd_ratio",
        "ordinary_assists",
        "flash_assists",
        "combined_assists",
        "adr",
        "kast",
        "survival_rate",
    ):
        assert by_key[key]["validation_status"] == "validated"
        assert by_key[key]["semantic_version"] == "3.0.0"


def test_every_critical_metric_has_explicit_terminal_validation_and_identity() -> None:
    registry = json.loads((ROOT / "docs/metrics/registry/metrics.json").read_text())
    critical = [metric for metric in registry["metrics"] if metric["critical"]]

    assert critical
    assert all(
        metric["validation_status"] in {"validated", "quarantined", "rejected", "unavailable"}
        for metric in critical
    )
    assert all("owner_user_id" in metric["identity_keys"] for metric in critical)
    assert all("semantic_version" in metric["identity_keys"] for metric in critical)
    assert not any(
        metric["ground_truth_status"] == "unknown" and metric["consumer_policy"] == "trusted"
        for metric in critical
    )


def test_registry_implementation_paths_exist_and_deprecated_aliases_fail_closed() -> None:
    registry = json.loads((ROOT / "docs/metrics/registry/metrics.json").read_text())
    by_key = {metric["metric_key"]: metric for metric in registry["metrics"]}
    for metric in registry["metrics"]:
        for entrypoint in metric["implementation_entrypoints"]:
            path = entrypoint.split("::", 1)[0]
            assert (ROOT / path).exists(), f"missing implementation path for {metric['metric_key']}: {path}"

    assert by_key["damage"]["validation_status"] == "rejected"
    assert by_key["headshot_rate"]["validation_status"] == "rejected"
    assert by_key["damage"]["consumer_policy"] == "forbidden"
    assert by_key["headshot_rate"]["consumer_policy"] == "forbidden"
