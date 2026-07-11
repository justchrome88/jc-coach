import json
from pathlib import Path

from app.services.parsing.combat_events import DEFAULT_TRADE_WINDOW_SECONDS, derive_combat_events

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "parser" / "combat_derivation_c04_events.json"


def _fixture_payload():
    return json.loads(FIXTURE_PATH.read_text())


def _derived():
    payload = _fixture_payload()
    return derive_combat_events(payload["events"], tracked_players=payload["players"])


def test_opening_duel_win_loss_and_opening_death_are_derived_per_round():
    events = [event for event in _derived() if event["event_type"] == "opening_duel"]

    assert [(event["round_number"], event["tick"]) for event in events] == [(1, 1200), (2, 1100), (3, 1300)]
    assert events[0]["actor"] == {"name": "Alpha", "steamid": "T1"}
    assert events[0]["victim"] == {"name": "Bravo", "steamid": "CT1"}
    assert events[0]["context"]["actor_outcome"] == "opening_duel_win"
    assert events[0]["context"]["victim_outcome"] == "opening_duel_loss"
    assert events[0]["context"]["opening_death"] is True
    assert events[0]["confidence"] == "high"


def test_trade_and_untraded_death_statuses_use_configurable_window():
    payload = _fixture_payload()
    events = derive_combat_events(
        payload["events"],
        tracked_players=payload["players"],
        trade_window_seconds=DEFAULT_TRADE_WINDOW_SECONDS,
    )
    traded_deaths = [
        event
        for event in events
        if event["event_type"] == "traded_death" and event["round_number"] in {1, 2}
    ]

    first_death = next(event for event in traded_deaths if event["victim"]["steamid"] == "CT1")
    refragged_death = next(event for event in traded_deaths if event["victim"]["steamid"] == "T1")
    untraded_death = next(event for event in traded_deaths if event["victim"]["steamid"] == "T2")

    assert first_death["context"]["trade_status"] == "traded"
    assert first_death["context"]["trade_delay_seconds"] == 3.906
    assert first_death["context"]["trade_actor"] == {"name": "Charlie", "steamid": "CT2"}
    assert refragged_death["context"]["trade_status"] == "untraded"
    assert untraded_death["context"]["trade_status"] == "untraded"

    tight_window_events = derive_combat_events(
        payload["events"],
        tracked_players=payload["players"],
        trade_window_seconds=3,
    )
    tight_first_death = next(
        event
        for event in tight_window_events
        if event["event_type"] == "traded_death" and event["victim"]["steamid"] == "CT1"
    )
    assert tight_first_death["context"]["trade_status"] == "untraded"
    assert tight_first_death["context"]["trade_window_seconds"] == 3


def test_survival_is_derived_for_tracked_players_per_round():
    round_one_survival = [
        event for event in _derived() if event["event_type"] == "round_survival" and event["round_number"] == 1
    ]
    survived = {event["actor"]["steamid"]: event["context"]["survived"] for event in round_one_survival}

    assert survived == {"T1": False, "T2": True, "CT1": False, "CT2": True}
    assert all(event["context"]["tracked_players_explicit"] is True for event in round_one_survival)
    assert all(event["confidence"] == "medium" for event in round_one_survival)


def test_ambiguous_trade_cases_carry_low_confidence_and_caveat():
    ambiguous = next(
        event
        for event in _derived()
        if event["event_type"] == "traded_death" and event["round_number"] == 3 and event["victim"]["steamid"] == "UB"
    )

    assert ambiguous["context"]["trade_status"] == "ambiguous"
    assert ambiguous["context"]["traded"] is None
    assert ambiguous["confidence"] == "low"
    assert (
        "Source events do not include both actor/victim team side; traded death is ambiguous."
        in ambiguous["caveats"]
    )
