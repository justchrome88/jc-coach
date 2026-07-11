from app.services.demo_parser import _early_deaths_from_timing, _metric_confidence, _parser_warnings
from app.services.metric_truth import (
    is_metric_allowed,
    is_metric_allowed_for_hard_claim,
    metric_definition,
    metric_reliability,
)


def test_early_deaths_requires_timing_anchor_and_never_falls_back_to_entry_deaths():
    player = {"name": "me", "steamid": "123"}
    death_events = [
        {
            "total_rounds_played": 1,
            "tick": 5000,
            "attacker_name": "enemy",
            "attacker_steamid": "456",
            "user_name": "me",
            "user_steamid": "123",
        }
    ]

    assert _early_deaths_from_timing(player, death_events, [], []) is None
    assert metric_reliability("early_deaths") == "approximate"
    assert not is_metric_allowed_for_hard_claim("early_deaths", "recommendation")


def test_early_deaths_counts_only_deaths_inside_supported_timing_window():
    player = {"name": "me", "steamid": "123"}
    death_events = [
        {
            "total_rounds_played": 1,
            "tick": 1000,
            "attacker_name": "enemy",
            "attacker_steamid": "456",
            "user_name": "me",
            "user_steamid": "123",
        },
        {
            "total_rounds_played": 2,
            "tick": 6000,
            "attacker_name": "enemy",
            "attacker_steamid": "456",
            "user_name": "me",
            "user_steamid": "123",
        },
    ]
    freeze_end_events = [
        {"total_rounds_played": 1, "tick": 100},
        {"total_rounds_played": 2, "tick": 100},
    ]

    assert _early_deaths_from_timing(player, death_events, [], freeze_end_events) == 1


def test_trade_and_traded_death_facts_stay_suppressed_until_parser_supports_them():
    assert metric_reliability("trade_kills") == "low"
    assert metric_reliability("traded_deaths") == "unavailable"
    assert not is_metric_allowed("trade_kills", "diagnosis")
    assert not is_metric_allowed("traded_deaths", "recommendation")


def test_side_split_metrics_remain_low_confidence_and_not_hard_claims():
    definition = metric_definition("side_ct_rounds_won")

    assert definition.metric_id == "side_split_metrics"
    assert definition.reliability == "low"
    assert definition.usage["display"] == "warn"
    assert definition.usage["diagnosis"] == "suppressed"
    assert definition.usage["recommendation"] == "suppressed"


def test_utility_and_flash_facts_keep_separate_reliability_limits():
    utility = metric_definition("utility_damage")
    flash = metric_definition("flash_assists")
    grenade_rating = metric_definition("grenade_rating")

    assert utility.reliability == "medium"
    assert flash.reliability == "approximate"
    assert grenade_rating.reliability == "unavailable"
    assert flash.usage["recommendation"] == "warn"
    assert not is_metric_allowed("grenade_rating", "diagnosis")


def test_parser_confidence_metadata_exposes_trade_kast_side_and_flash_limits():
    confidence = _metric_confidence(
        {
            "player_death": 5,
            "player_hurt": 5,
            "rounds": 2,
            "weapon_fire": 0,
            "grenade_events": 1,
            "player_blind": 0,
            "bomb_events": 0,
            "round_end": 2,
            "player_team": 0,
        },
        {"rounds_for": None},
        {"kast": 50},
        adr=60,
        early_deaths=None,
    )
    warnings = _parser_warnings(confidence)

    assert confidence["early_deaths"] == "low"
    assert confidence["kast_trade_component"] == "unavailable"
    assert confidence["trade_kills"] == "low"
    assert confidence["traded_deaths"] == "unavailable"
    assert confidence["side_stats"] == "low"
    assert confidence["flash"] == "low"
    assert any("Traded/untraded death facts" in warning for warning in warnings)
