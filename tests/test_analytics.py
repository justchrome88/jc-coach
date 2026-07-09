import json
from datetime import datetime, timedelta

from app.services import metric_confidence as metric_confidence_module
from app.services.analytics import compare_periods, get_adr_profile, get_dashboard_status, get_map_stats, get_summary
from app.services.metric_confidence import exact_date_window_metadata, metric_confidence_map, metric_context
from tests.conftest import make_match


def test_summary_counts_core_metrics(sample_rows):
    matches = [make_match(**row) for row in sample_rows]

    summary = get_summary(matches)

    assert summary["matches_count"] == 2
    assert summary["winrate"] == 50.0
    assert summary["avg_adr"] == 74.6
    assert summary["avg_kast"] == 69.5
    assert summary["entry_diff"] == -4


def test_compare_periods_uses_latest_matches():
    start = datetime(2026, 6, 1)
    matches = []
    for index in range(30):
        recent = index >= 15
        matches.append(
            make_match(
                external_match_id=f"match-{index}",
                played_at=start + timedelta(days=index),
                result="loss" if recent else "win",
                kd=0.8 if recent else 1.2,
                adr=65 if recent else 85,
                kast=66 if recent else 76,
                rating=0.85 if recent else 1.15,
                deaths=20 if recent else 15,
                utility_damage=35 if recent else 90,
                flash_assists=0 if recent else 1,
                entry_kills=1 if recent else 3,
                entry_deaths=4 if recent else 2,
            )
        )

    comparison = compare_periods(matches)

    assert comparison["current_n"] == 15
    assert comparison["previous_n"] == 15
    assert comparison["deltas"]["winrate"]["delta"] == -100
    assert comparison["trend"] == "down"


def test_compare_periods_excludes_approximate_demo_dates_from_exact_windows():
    start = datetime(2026, 6, 1)
    matches = [
        make_match(
            source="demo",
            external_match_id=f"exact-{index}",
            played_at=start + timedelta(days=index),
            result="win" if index < 15 else "loss",
            adr=90 if index < 15 else 60,
            raw_json=_date_truth_raw("exact_match_date_available", "steam_gc_match_time"),
        )
        for index in range(30)
    ]
    matches.extend(
        [
            make_match(
                source="demo",
                external_match_id="approx-newer-1",
                played_at=start + timedelta(days=40),
                result="win",
                adr=120,
                raw_json=_date_truth_raw("approximate_match_date", "file_modified_fallback"),
            ),
            make_match(
                source="demo",
                external_match_id="approx-newer-2",
                played_at=start + timedelta(days=41),
                result="win",
                adr=120,
                raw_json=_date_truth_raw("approximate_match_date", "file_modified_fallback"),
            ),
        ]
    )

    comparison = compare_periods(matches)

    assert comparison["current_n"] == 15
    assert comparison["previous_n"] == 15
    assert comparison["deltas"]["winrate"]["current"] == 0.0
    assert comparison["date_window"]["approximate_date_matches"] == 2
    assert comparison["date_window"]["excluded_from_exact_windows"] == 2


def test_map_stats_sort_by_winrate(sample_rows):
    matches = [make_match(**row) for row in sample_rows]

    stats = get_map_stats(matches)

    assert stats[0]["map_name"] == "Mirage"
    assert stats[-1]["map_name"] == "Ancient"
    assert all("sample_confidence" in item for item in stats)


def test_dashboard_status_reports_source_and_quality(sample_rows):
    matches = [make_match(**row, source="demo" if index == 0 else "csv") for index, row in enumerate(sample_rows)]

    status = get_dashboard_status(matches)

    assert status["data_quality"]["coverage"]["ADR"] == 100.0
    assert status["data_quality"]["label"] == "Высокое"
    assert {item["source"] for item in status["source_breakdown"]} == {"csv", "demo"}
    assert status["adr_profile"]["average"] == 74.6


def test_adr_profile_tracks_recent_delta():
    start = datetime(2026, 6, 1)
    matches = [
        make_match(external_match_id=f"m-{index}", played_at=start + timedelta(days=index), adr=70 + index)
        for index in range(30)
    ]

    profile = get_adr_profile(matches)

    assert profile["coverage"] == 100.0
    assert profile["confidence"] == "high"
    assert profile["recent_average"] == 92
    assert profile["previous_average"] == 77
    assert profile["delta"] == 15


def test_form_score_is_unavailable_with_insufficient_exact_sample():
    matches = [
        make_match(
            source="demo",
            external_match_id=f"exact-small-{index}",
            played_at=datetime(2026, 6, index + 1),
            result="win",
            kd=1.2,
            adr=85,
            kast=75,
            raw_json=_date_truth_raw("exact_match_date_available", "steam_gc_match_time"),
        )
        for index in range(4)
    ]

    summary = get_summary(matches, date_windowed=True)

    assert summary["form_score"] is None
    assert summary["form_score_confidence"]["level"] == "unavailable"


def test_rating_zero_coverage_is_unavailable_not_hard_metric():
    matches = [
        make_match(
            source="demo",
            external_match_id=f"no-rating-{index}",
            played_at=datetime(2026, 6, index + 1),
            result="win",
            raw_json=_date_truth_raw("exact_match_date_available", "steam_gc_match_time"),
        )
        for index in range(5)
    ]

    summary = get_summary(matches, date_windowed=True)

    assert summary["avg_rating"] is None
    assert summary["metric_confidence"]["hltv_rating"]["level"] == "unavailable"


def test_steam_history_placeholders_are_not_counted_as_playable_date_windows():
    matches = [
        make_match(
            source="demo",
            external_match_id="demo-exact",
            played_at=datetime(2026, 6, 1),
            raw_json=_date_truth_raw("exact_match_date_available", "steam_gc_match_time"),
        ),
        make_match(
            source="steam_history",
            external_match_id="placeholder",
            played_at=datetime(2026, 6, 2),
            raw_json=_date_truth_raw("exact_match_date_available", "steam_gc_match_time"),
        ),
    ]

    metadata = exact_date_window_metadata(matches, required_sample=1)

    assert metadata["total_playable_matches"] == 1
    assert metadata["exact_date_matches"] == 1


def test_partial_metrics_are_caveated_not_exact_hard_claims(sample_rows):
    matches = [make_match(**row) for row in sample_rows]

    summary = get_summary(matches)

    assert summary["metric_confidence"]["kast"]["level"] == "low"
    assert summary["metric_confidence"]["kast"]["hard_recommendation_eligible"] is False
    assert summary["metric_confidence"]["swing_score"]["level"] == "unavailable"


def test_metric_context_caches_raw_json_parsing(monkeypatch):
    matches = [
        make_match(
            source="demo",
            external_match_id=f"cached-{index}",
            played_at=datetime(2026, 6, index + 1),
            raw_json=_date_truth_raw("exact_match_date_available", "steam_gc_match_time"),
            adr=80 + index,
            kast=70 + index,
        )
        for index in range(3)
    ]
    original_loads = metric_confidence_module.json.loads
    calls = 0

    def counting_loads(value):
        nonlocal calls
        calls += 1
        return original_loads(value)

    monkeypatch.setattr(metric_confidence_module.json, "loads", counting_loads)
    context = metric_context(matches)

    exact_date_window_metadata(matches, required_sample=2, context=context)
    exact_date_window_metadata(matches, required_sample=2, context=context)
    metric_confidence_map(("adr", "kast", "result"), matches, date_windowed=True, min_sample=2, context=context)

    assert calls == len(matches)


def _date_truth_raw(status: str, source: str) -> str:
    return json.dumps(
        {
            "match_date_status": status,
            "match_date_source": source,
            "played_at_source": source,
        }
    )
