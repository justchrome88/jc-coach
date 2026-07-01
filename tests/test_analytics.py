from datetime import datetime, timedelta

from app.services.analytics import compare_periods, get_map_stats, get_summary
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


def test_map_stats_sort_by_winrate(sample_rows):
    matches = [make_match(**row) for row in sample_rows]

    stats = get_map_stats(matches)

    assert stats[0]["map_name"] == "Mirage"
    assert stats[-1]["map_name"] == "Ancient"
