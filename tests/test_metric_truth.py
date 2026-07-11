from app.services.shared.metric_policy import (
    METRIC_REGISTRY,
    is_metric_allowed,
    is_metric_allowed_for_hard_claim,
    metric_definition,
    metric_reliability,
    metric_truth_payload,
    metric_warning,
    suppressed_metrics_for_usage,
)


def test_registry_contains_required_core_metrics():
    required = {
        "adr",
        "kast",
        "hltv_rating",
        "kills_per_round",
        "deaths_per_round",
        "kd_ratio",
        "headshot_rate",
        "entry_deaths",
        "early_deaths",
        "trade_kills",
        "utility_damage",
        "grenade_rating",
        "aim_rating",
        "side_split_metrics",
    }

    assert required.issubset(METRIC_REGISTRY)
    for metric_id in required:
        definition = metric_definition(metric_id)
        assert definition.source
        assert definition.formula
        assert definition.limitations


def test_trusted_metric_can_be_used_for_hard_claims():
    assert metric_reliability("kd_ratio") == "trusted"
    assert is_metric_allowed("kd", "display")
    assert is_metric_allowed_for_hard_claim("kd", "diagnosis")
    assert is_metric_allowed_for_hard_claim("kd", "recommendation")
    assert is_metric_allowed_for_hard_claim("kd", "ai")


def test_disputed_kast_is_suppressed_from_trusted_consumers():
    definition = metric_definition("kast")

    assert definition.reliability == "approximate"
    assert definition.usage["diagnosis"] == "suppressed"
    assert definition.usage["recommendation"] == "suppressed"
    assert definition.usage["ai"] == "suppressed"
    assert not is_metric_allowed("kast", "diagnosis")
    assert not is_metric_allowed_for_hard_claim("kast", "diagnosis")
    assert metric_warning("kast", "ai") is not None


def test_low_and_unavailable_metrics_are_suppressed_from_hard_recommendations():
    assert metric_reliability("trade_kills") == "low"
    assert metric_reliability("traded_death") == "unavailable"
    assert not is_metric_allowed("trade_kills", "recommendation")
    assert not is_metric_allowed("traded_death", "diagnosis")
    assert "trade_kills" in suppressed_metrics_for_usage("recommendation")
    assert "traded_deaths" in suppressed_metrics_for_usage("diagnosis")


def test_early_deaths_fallback_is_not_fully_trusted():
    definition = metric_definition("early_deaths")

    assert definition.reliability == "approximate"
    assert any("fallback" in limitation for limitation in definition.limitations)
    assert definition.usage["recommendation"] == "warn"
    assert not is_metric_allowed_for_hard_claim("early_deaths", "recommendation")


def test_side_split_metrics_are_low_confidence_and_suppressed():
    definition = metric_definition("side_t_rounds_won")

    assert definition.metric_id == "side_split_metrics"
    assert definition.reliability == "low"
    assert definition.usage["display"] == "warn"
    assert definition.usage["diagnosis"] == "suppressed"
    assert definition.usage["recommendation"] == "suppressed"


def test_unknown_metric_returns_safe_unavailable_behavior():
    definition = metric_definition("future_magic_metric")

    assert definition.metric_id == "unknown"
    assert definition.reliability == "unavailable"
    assert not is_metric_allowed("future_magic_metric", "display")
    assert not is_metric_allowed_for_hard_claim("future_magic_metric", "ai")
    assert metric_warning("future_magic_metric", "diagnosis") is not None


def test_metric_truth_payload_is_serializable_and_deduplicated():
    payload = metric_truth_payload(["kd", "kd_ratio", "early_deaths"])
    ids = [item["metric_id"] for item in payload]

    assert ids == ["kd_ratio", "early_deaths"]
    assert payload[0]["usage"]["display"] == "allowed"
