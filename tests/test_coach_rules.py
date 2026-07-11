from app.services.coach_rules import build_coach_focus
from app.services.metrics.analytics import compare_periods, detect_weaknesses, get_map_stats, get_summary
from tests.conftest import make_match


def test_detects_low_utility_and_entry_problem(sample_rows):
    matches = [make_match(**row) for row in sample_rows]
    summary = get_summary(matches)
    comparison = compare_periods(matches)
    map_stats = get_map_stats(matches)

    weaknesses = detect_weaknesses(summary, comparison, map_stats)
    titles = [item["title"] for item in weaknesses]

    assert "Дисциплина первых дуэлей" in titles
    assert "Низкий impact гранат" in titles


def test_build_focus_has_actions(sample_rows):
    matches = [make_match(**row) for row in sample_rows]
    focus = build_coach_focus(get_summary(matches), compare_periods(matches), get_map_stats(matches))

    assert focus["title"]
    assert focus["actions"]
