import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from app.services.analytics import compare_periods, get_map_stats, get_summary, match_detail
from app.services.metric_confidence import exact_date_window_metadata, metric_confidence_map, metric_context
from app.services.metric_truth import METRIC_REGISTRY, metric_definition
from tests.conftest import make_match

FIXTURE_ROOT = Path(__file__).parent / "fixtures"
SENSITIVE_PATTERNS = (
    re.compile(r"STEAM_[0-5]:[01]:\d+", re.IGNORECASE),
    re.compile(r"\b7656119\d{10}\b"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def _load_fixture(relative_path: str) -> dict:
    with (FIXTURE_ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _fixture_matches() -> list:
    payload = _load_fixture("metrics/golden_aggregate_c2.json")
    matches = []
    for row in payload["matches"]:
        values = dict(row)
        values["played_at"] = datetime.fromisoformat(values["played_at"])
        values["raw_json"] = json.dumps(values.pop("raw"))
        matches.append(make_match(**values))
    return matches


def test_filter_confidence_labels_are_carried_with_selected_match_windows():
    matches = _fixture_matches()
    selected = [match for match in matches if match.map_name == "de_mirage"]
    context = metric_context(selected)

    summary = get_summary(selected, date_windowed=True, context=context)
    date_window = exact_date_window_metadata(selected, required_sample=3, context=context)

    assert date_window["confidence"] == "low"
    assert summary["metric_confidence"]["adr"]["level"] == "low"
    assert summary["metric_confidence"]["kast"]["level"] == "low"
    assert summary["metric_confidence"]["side_split_metrics"]["level"] == "unavailable"
    assert "insufficient_exact_date_sample" in summary["metric_confidence"]["adr"]["reason_codes"]
    assert summary["metric_confidence"]["adr"]["source_trust"]["parser_confidence"] == "medium"
    assert summary["metric_confidence"]["adr"]["usable_for_insights"] is False
    assert summary["metric_confidence"]["adr"]["hard_recommendation_eligible"] is False
    assert any("Only 2 exact-date matches available" in warning for warning in date_window["warnings"])


def test_metric_formula_and_reliability_stay_in_sync_with_metrics_doc():
    docs = Path("project_docs/metrics/METRICS.md").read_text(encoding="utf-8")
    core_table = docs.split("## Core Metric Table", 1)[1].split("## Runtime Policy", 1)[0]
    rows = [
        line
        for line in core_table.splitlines()
        if line.startswith("| `") and " Metric id " not in line and "---" not in line
    ]

    assert rows
    documented = set()
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        metric_ids = re.findall(r"`([^`]+)`", cells[0])
        reliability = cells[1].strip("`")
        source_formula = cells[2]
        assert source_formula
        for metric_id in metric_ids:
            definition = metric_definition(metric_id)
            documented.add(definition.metric_id)
            assert definition.metric_id != "unknown", metric_id
            assert definition.reliability == reliability, metric_id
            assert definition.formula and definition.formula != "not defined"

    assert {"adr", "kast", "side_split_metrics", "traded_deaths"}.issubset(documented)
    for definition in METRIC_REGISTRY.values():
        assert definition.formula and definition.source


def test_golden_aggregate_fixture_suite_matches_expected_outputs():
    payload = _load_fixture("metrics/golden_aggregate_c2.json")
    matches = _fixture_matches()
    context = metric_context(matches)

    summary = get_summary(matches, date_windowed=True, context=context)
    comparison = compare_periods(matches, current_n=2, previous_n=2, context=context)
    map_stats = sorted(get_map_stats(matches, context=context), key=lambda item: item["map_name"], reverse=True)

    expected_summary = payload["expected"]["summary"]
    assert summary["matches_count"] == expected_summary["matches_count"]
    assert summary["winrate"] == expected_summary["winrate"]
    assert summary["avg_kd"] == expected_summary["avg_kd"]
    assert summary["avg_adr"] == expected_summary["avg_adr"]
    assert summary["avg_kast"] == expected_summary["avg_kast"]
    assert summary["entry_diff"] == expected_summary["entry_diff"]
    assert summary["round_diff"] == expected_summary["round_diff"]
    assert summary["date_window"]["confidence"] == expected_summary["date_window_confidence"]
    assert summary["date_window"]["excluded_from_exact_windows"] == expected_summary["excluded_from_exact_windows"]

    expected_comparison = payload["expected"]["period_comparison"]
    assert comparison["current_n"] == expected_comparison["current_n"]
    assert comparison["previous_n"] == expected_comparison["previous_n"]
    assert comparison["confidence"] == expected_comparison["confidence"]
    assert comparison["deltas"]["adr"]["delta"] == expected_comparison["adr_delta"]

    assert [
        {
            "map_name": item["map_name"],
            "matches_count": item["matches_count"],
            "sample_confidence": item["sample_confidence"],
            "winrate": item["winrate"],
        }
        for item in map_stats
    ] == payload["expected"]["map_stats"]


@pytest.mark.parametrize("metric_id", ("adr", "kast", "hltv_rating", "entry_deaths"))
def test_null_and_empty_metrics_remain_unavailable_without_imputation(metric_id):
    assert metric_confidence_map((metric_id,), [], date_windowed=True)[metric_id]["level"] == "unavailable"

    matches = [
        make_match(
            source="demo",
            external_match_id=f"null-{index}",
            played_at=datetime(2026, 7, index + 1),
            result="win",
            kills=20,
            deaths=10,
            raw_json=json.dumps(
                {
                    "match_date_status": "exact_match_date_available",
                    "match_date_source": "steam_gc_match_time",
                    "played_at_source": "steam_gc_match_time",
                }
            ),
        )
        for index in range(3)
    ]

    confidence = metric_confidence_map((metric_id,), matches, date_windowed=True, min_sample=3)[metric_id]

    assert confidence["level"] == "unavailable"
    assert confidence["present_count"] == 0
    assert confidence["coverage"] == 0.0
    assert "metric_no_populated_values" in confidence["reason_codes"]
    assert any("no populated values" in reason for reason in confidence["reasons"])


def test_sanitized_parser_payload_fixture_has_required_confidence_metadata_and_no_sensitive_values():
    fixture = _load_fixture("parser/sanitized_parser_payload_c2.json")
    payload = fixture["payload"]
    serialized = json.dumps(payload)

    assert "synthetic" in fixture["description"].lower()
    for pattern in SENSITIVE_PATTERNS:
        assert not pattern.search(serialized)
    assert "password" not in serialized.lower()
    assert "token" not in serialized.lower()
    assert payload["parser"] == "demoparser2"
    assert payload["parser_confidence"] == "medium"
    assert payload["metric_confidence"]["kast_trade_component"] == "low"
    assert payload["metric_confidence"]["traded_deaths"] == "unavailable"
    assert payload["metric_confidence"]["side_stats"] == "low"

    match = make_match(
        source="demo",
        external_match_id=payload["match"]["external_match_id"],
        played_at=datetime.fromisoformat(payload["match"]["played_at"]),
        raw_json=json.dumps(payload),
    )
    evidence = match_detail(match)["parser_evidence"]

    assert evidence["confidence"] == "medium"
    assert evidence["metric_confidence"]["traded_deaths"] == "unavailable"
    assert evidence["player"]["steamid"] == "SYNTHETIC_STEAM_ID"
