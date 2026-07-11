from pathlib import Path

from app.db.models import Match
from app.services.metrics.snapshots import metric_snapshot_payload
from app.services.metrics.utility import (
    UTILITY_METRICS_VERSION,
    calculate_and_store_utility_metrics,
    calculate_utility_metrics,
)
from app.services.parsing.artifact_reader import read_normalized_events_from_artifact_file

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "parser"
C05_SUPPORTED_PATH = FIXTURE_DIR / "parser_artifact_c05_utility_supported.json"
C05_MISSING_PATH = FIXTURE_DIR / "parser_artifact_c05_utility_missing.json"


def _result_by_player(events, players=None):
    results = calculate_utility_metrics(events, players=players)
    return {result.player_key: result for result in results}


def test_supported_c05_utility_metrics_are_calculated_without_grenade_rating():
    events = read_normalized_events_from_artifact_file(C05_SUPPORTED_PATH)

    player = _result_by_player(events)["steam:SYNTHETIC_STEAM_ID"]

    assert player.metrics == {
        "enemies_flashed": 1,
        "flash_detonations": 1,
        "he_damage": 42,
        "he_detonations": 1,
        "molotov_damage": 7,
        "molotov_detonations": 1,
        "smoke_detonations": 1,
        "raw_utility_event_amount": 49,
        "unknown_utility_damage": 49,
    }
    assert "flash_assists" not in player.metrics
    assert "grenade_rating" not in player.metrics
    assert player.confidence_baseline["metrics"]["utility_damage"]["level"] == "medium"
    assert player.confidence_baseline["metrics"]["enemies_flashed"]["level"] == "low"
    assert player.confidence_baseline["metrics"]["smoke_detonations"]["level"] == "low"
    assert player.confidence_baseline["metrics"]["grenade_rating"]["level"] == "unavailable"
    assert "Utility damage is inferred from parser weapon name on player_hurt." in player.caveats
    assert "Unsupported grenade_rating is omitted rather than inferred from weak utility events." in player.caveats


def test_missing_utility_data_omits_metrics_and_records_unavailable_reasons():
    events = read_normalized_events_from_artifact_file(C05_MISSING_PATH)

    player = _result_by_player(
        events,
        players=[{"name": "Synthetic Player", "steamid": "SYNTHETIC_STEAM_ID"}],
    )["steam:SYNTHETIC_STEAM_ID"]

    assert player.metrics == {}
    confidence = player.confidence_baseline["metrics"]
    assert confidence["utility_damage"]["level"] == "unavailable"
    assert confidence["enemies_flashed"]["level"] == "unavailable"
    assert confidence["flash_assists"]["level"] == "unavailable"
    assert confidence["grenade_rating"]["level"] == "unavailable"
    assert "utility damage is omitted instead of set to zero" in confidence["utility_damage"]["reasons"][0]
    assert "Utility damage source data is missing; utility damage metrics are unavailable." in player.caveats
    assert (
        "Downstream coach and metrics layers must not infer grenade quality from missing utility data."
        in player.caveats
    )


def test_weak_flash_utility_metric_carries_low_confidence_and_reason():
    events = [
        {
            "schema_version": "normalized-parser-events-v1",
            "event_type": "flash_effect",
            "category": "utility",
            "support": "weak",
            "source": {"kind": "fixture"},
            "round_number": 1,
            "tick": 1800,
            "time_seconds": 28.125,
            "actor": {"name": "Alpha", "steamid": "T1"},
            "victim": {"name": "Bravo", "steamid": "CT1"},
            "context": {"utility_type": "flashbang", "blind_duration": None},
            "source_event": "player_blind",
            "confidence": "low",
            "caveats": ["Source row omitted blind duration; flash value must remain low-confidence."],
            "payload": {},
        }
    ]

    alpha = _result_by_player(events)["steam:T1"]

    assert alpha.metrics["enemies_flashed"] == 1
    flash_confidence = alpha.confidence_baseline["metrics"]["enemies_flashed"]
    assert flash_confidence["level"] == "low"
    assert flash_confidence["reasons"] == [
        "Flash metrics are weak C05 facts; blind duration and kill impact are not exact value."
    ]
    assert "weak_event_support" in flash_confidence["reason_codes"]
    assert flash_confidence["source_trust"]["source_kinds"] == ["fixture"]
    assert flash_confidence["usable_for_insights"] is False
    assert flash_confidence["hard_recommendation_eligible"] is False
    assert "Source row omitted blind duration; flash value must remain low-confidence." in alpha.caveats


def test_utility_metrics_store_and_update_metric_snapshots(db):
    events = read_normalized_events_from_artifact_file(C05_SUPPORTED_PATH)
    match = Match(source="test", external_match_id="utility-metrics-d04")
    db.add(match)
    db.commit()
    db.refresh(match)

    first = calculate_and_store_utility_metrics(
        db,
        match_id=match.id,
        normalized_events=events,
        source_event_set_id="fixture:c05:utility",
    )
    second = calculate_and_store_utility_metrics(
        db,
        match_id=match.id,
        normalized_events=events,
        source_event_set_id="fixture:c05:utility",
    )

    assert {snapshot.id for snapshot in second} == {snapshot.id for snapshot in first}
    player = next(snapshot for snapshot in second if snapshot.player_key == "steam:SYNTHETIC_STEAM_ID")
    payload = metric_snapshot_payload(player)
    assert payload["source"] == "utility_metrics"
    assert payload["source_event_set_id"] == "fixture:c05:utility"
    assert payload["metrics"]["raw_utility_event_amount"] == 49
    assert "utility_damage" not in payload["metrics"]
    assert payload["semantic_version"] == "2.0.0"
    assert "grenade_rating" not in payload["metrics"]
    assert payload["confidence_baseline"]["source"] == UTILITY_METRICS_VERSION
    assert payload["confidence_baseline"]["metrics"]["grenade_rating"]["level"] == "unavailable"
    assert payload["metadata"]["schema_version"] == UTILITY_METRICS_VERSION
