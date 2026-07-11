from app.services.coach.mistakes import category_scorecard, detect_structured_mistakes, mistakes_by_match_id
from tests.conftest import make_match


def test_detects_structured_mistakes_for_bad_core_metrics():
    matches = [
        make_match(
            external_match_id=f"m-{index}",
            map_name="Mirage",
            result="loss",
            kills=10,
            deaths=20,
            adr=55,
            kast=58,
            entry_kills=0,
            entry_deaths=4,
            early_deaths=4,
            utility_damage=10,
            flash_assists=0,
        )
        for index in range(3)
    ]

    mistakes = detect_structured_mistakes(matches)
    mistake_types = {mistake["type"] for mistake in mistakes}

    assert "low_adr_pressure" in mistake_types
    assert "bad_entry_duels" in mistake_types
    assert "weak_utility_impact" in mistake_types
    assert mistakes[0]["severity"] == "high"


def test_groups_match_mistakes_by_match_id():
    match = make_match(
        id=42,
        external_match_id="m-42",
        adr=50,
        kast=55,
        entry_kills=0,
        entry_deaths=4,
        early_deaths=4,
        utility_damage=0,
        flash_assists=0,
    )

    grouped = mistakes_by_match_id([match])

    assert 42 in grouped
    assert {mistake["type"] for mistake in grouped[42]} >= {"match_low_adr", "match_early_deaths"}


def test_category_scorecard_marks_no_data_categories():
    scorecard = category_scorecard([])
    by_category = {item["category"]: item for item in scorecard}

    assert by_category["aim"]["status"] == "ok"
    assert by_category["crosshair_placement"]["status"] == "no_data"
