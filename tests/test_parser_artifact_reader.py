import json
from pathlib import Path

import pytest

from app.services.parsing.artifact_reader import (
    NORMALIZED_EVENT_SCHEMA_VERSION,
    NormalizedEventValidationError,
    ParserArtifactReaderError,
    normalized_events_from_parser_artifact,
    read_normalized_events,
    read_normalized_events_from_artifact_file,
    validate_normalized_event,
)
from app.services.parsing.event_dictionary import EVENT_METRIC_DICTIONARY, NORMALIZED_EVENT_SCHEMA
from app.services.shared.demo_retention import (
    ARTIFACT_CATEGORY_NORMALIZED_EVENT_STORE,
    RETENTION_CLASS_DERIVED_REBUILDABLE,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "parser"
ARTIFACT_PATH = FIXTURE_DIR / "parser_artifact_c02.json"
C03_ARTIFACT_PATH = FIXTURE_DIR / "parser_artifact_c03_combat.json"
C05_UTILITY_SUPPORTED_PATH = FIXTURE_DIR / "parser_artifact_c05_utility_supported.json"
C05_UTILITY_MISSING_PATH = FIXTURE_DIR / "parser_artifact_c05_utility_missing.json"
HANDOFF_PATH = "/opt/jc-coach/data/uploads/retained/00/0000000000000000000000000000000000000000.dem"


def test_normalized_event_schema_declares_stable_fields():
    required_fields = {
        "schema_version",
        "event_type",
        "category",
        "support",
        "source",
        "round_number",
        "tick",
        "time_seconds",
        "actor",
        "victim",
        "context",
        "source_event",
        "confidence",
        "caveats",
        "payload",
    }

    assert required_fields.issubset(NORMALIZED_EVENT_SCHEMA)


def test_parser_artifact_fixture_reads_normalized_events():
    events = read_normalized_events_from_artifact_file(ARTIFACT_PATH)
    event_types = {event["event_type"] for event in events}

    assert {
        "round_summary",
        "round_timing",
        "objective_event",
        "player_kill",
        "player_death",
        "opening_duel",
        "damage",
        "flash_effect",
        "utility_damage",
        "grenade_path",
        "weapon_accuracy",
        "round_survival",
    }.issubset(event_types)
    assert all(event["schema_version"] == NORMALIZED_EVENT_SCHEMA_VERSION for event in events)
    assert all(event["event_type"] in EVENT_METRIC_DICTIONARY for event in events)
    assert all(event["source"]["source_demo_file"] == HANDOFF_PATH for event in events)
    assert all(event["retention"]["category"] == ARTIFACT_CATEGORY_NORMALIZED_EVENT_STORE for event in events)
    assert all(event["retention"]["retention_class"] == RETENTION_CLASS_DERIVED_REBUILDABLE for event in events)

    kill = next(event for event in events if event["event_type"] == "player_kill")
    assert kill["round_number"] == 1
    assert kill["tick"] == 2500
    assert kill["time_seconds"] == 39.062
    assert kill["actor"] == {"name": "Synthetic Player", "steamid": "SYNTHETIC_STEAM_ID"}
    assert kill["victim"] == {"name": "Synthetic Opponent", "steamid": "SYNTHETIC_OPPONENT_ID"}
    assert kill["context"]["weapon"] == "ak47"
    assert kill["confidence"] == "high"


def test_c03_round_boundary_fixture_extracts_expected_values():
    events = read_normalized_events_from_artifact_file(C03_ARTIFACT_PATH)
    round_events = [event for event in events if event["event_type"] == "round_timing"]

    assert [(event["source_event"], event["tick"], event["time_seconds"]) for event in round_events] == [
        ("round_start", 640, 10.0),
        ("round_freeze_end", 960, 15.0),
        ("round_end", 7800, 121.875),
    ]
    assert all(event["round_number"] == 1 for event in round_events)
    assert round_events[-1]["context"] == {
        "boundary": "round_end",
        "winner_side": "CT",
        "end_reason": "target_saved",
    }


def test_c03_kill_death_damage_fixture_extracts_expected_player_context():
    events = read_normalized_events_from_artifact_file(C03_ARTIFACT_PATH)
    kill = next(event for event in events if event["event_type"] == "player_kill")
    death = next(event for event in events if event["event_type"] == "player_death")
    damage = next(event for event in events if event["event_type"] == "damage")

    assert kill["source_event"] == "player_death"
    assert kill["round_number"] == 1
    assert kill["tick"] == 2500
    assert kill["actor"] == {"name": "Synthetic Player", "steamid": "SYNTHETIC_STEAM_ID"}
    assert kill["victim"] == {"name": "Synthetic Opponent", "steamid": "SYNTHETIC_OPPONENT_ID"}
    assert kill["context"]["assister"] == {"name": "Synthetic Teammate", "steamid": "SYNTHETIC_TEAMMATE_ID"}
    assert kill["context"]["weapon"] == "ak47"
    assert kill["context"]["headshot"] is True
    assert death["actor"] == kill["actor"]
    assert death["victim"] == kill["victim"]

    assert damage["source_event"] == "player_hurt"
    assert damage["round_number"] == 1
    assert damage["tick"] == 2450
    assert damage["actor"] == kill["actor"]
    assert damage["victim"] == kill["victim"]
    assert damage["context"] == {
        "weapon": "ak47",
        "hitgroup": "chest",
        "damage_health": 28,
        "damage_armor": 4,
        "victim_health_after": 72,
        "victim_armor_after": 96,
    }
    assert damage["confidence"] == "medium"


def test_c03_missing_combat_fields_are_caveated_without_crashing():
    artifact = json.loads(C03_ARTIFACT_PATH.read_text())
    row = artifact["payload"]["deep"]["player_hurt"][0]
    row.pop("tick")
    row.pop("attacker_steamid")
    row.pop("user_steamid")
    row.pop("dmg_health")

    damage = next(
        event for event in normalized_events_from_parser_artifact(artifact) if event["event_type"] == "damage"
    )

    assert damage["tick"] is None
    assert damage["time_seconds"] is None
    assert damage["actor"] == {"name": "Synthetic Player"}
    assert damage["victim"] == {"name": "Synthetic Opponent"}
    assert "Source row omitted tick; time_seconds is unavailable." in damage["caveats"]
    assert "Source row omitted actor steamid; player joins may require name fallback." in damage["caveats"]
    assert "Source row omitted victim steamid; player joins may require name fallback." in damage["caveats"]
    assert "Source row omitted health damage; ADR consumers must ignore this row." in damage["caveats"]


def test_c05_supported_utility_events_extract_first_pass_facts():
    events = read_normalized_events_from_artifact_file(C05_UTILITY_SUPPORTED_PATH)

    detonations = [event for event in events if event["event_type"] == "utility_detonation"]
    assert {event["context"]["utility_type"] for event in detonations} == {
        "flashbang",
        "smoke",
        "hegrenade",
        "incendiary",
    }
    assert all(event["support"] == "weak" for event in detonations)
    assert all(event["confidence"] == "medium" for event in detonations)

    raw_utility_damage = next(
        event
        for event in events
        if event["event_type"] == "utility_damage" and event["source_event"] == "player_hurt"
    )
    assert raw_utility_damage["context"]["utility_type"] == "hegrenade"
    assert raw_utility_damage["context"]["damage_health"] == 42
    assert "Utility damage is inferred from parser weapon name on player_hurt." in raw_utility_damage["caveats"]

    flash = next(
        event for event in events if event["event_type"] == "flash_effect" and event["source_event"] == "player_blind"
    )
    assert flash["actor"] == {"name": "Synthetic Player", "steamid": "SYNTHETIC_STEAM_ID"}
    assert flash["victim"] == {"name": "Synthetic Opponent", "steamid": "SYNTHETIC_OPPONENT_ID"}
    assert flash["context"]["blind_duration"] == 1.8
    assert flash["support"] == "weak"

    data_gap = next(event for event in events if event["event_type"] == "utility_data_gap")
    assert data_gap["support"] == "unsupported"
    assert data_gap["confidence"] == "low"
    assert data_gap["context"]["missing_sources"] == ["grenade_trajectories"]
    assert data_gap["context"]["unsupported_metrics"] == ["grenade_rating"]


def test_c05_missing_utility_data_is_explicitly_unsupported():
    events = read_normalized_events_from_artifact_file(C05_UTILITY_MISSING_PATH)
    utility_events = [event for event in events if event["category"] == "utility"]

    assert [event["event_type"] for event in utility_events] == ["utility_data_gap"]
    data_gap = utility_events[0]
    assert data_gap["support"] == "unsupported"
    assert data_gap["confidence"] == "low"
    assert data_gap["context"]["missing_sources"] == [
        "grenade_events",
        "player_blind",
        "grenade_trajectories",
        "utility_damage",
    ]
    assert "Downstream coach and metrics layers must not infer grenade quality from missing utility data." in data_gap[
        "caveats"
    ]


def test_retained_demo_handoff_path_reads_existing_parser_artifact():
    events = read_normalized_events(HANDOFF_PATH, parser_artifact_path=ARTIFACT_PATH)

    assert events
    assert {event["source"]["source_demo_file"] for event in events} == {HANDOFF_PATH}


def test_raw_demo_handoff_without_artifact_is_rejected():
    with pytest.raises(ParserArtifactReaderError) as excinfo:
        read_normalized_events(HANDOFF_PATH)

    assert excinfo.value.issues == ["parser_artifact_required_for_raw_demo_handoff"]


def test_schema_validation_catches_malformed_event_object():
    valid_event = read_normalized_events_from_artifact_file(ARTIFACT_PATH)[0]
    malformed = dict(valid_event)
    malformed["event_type"] = "not_a_real_event"
    malformed["round_number"] = "one"

    with pytest.raises(NormalizedEventValidationError) as excinfo:
        validate_normalized_event(malformed)

    assert "unknown_event_type" in excinfo.value.issues
    assert "invalid_round_number" in excinfo.value.issues


def test_malformed_artifact_deep_rows_are_rejected():
    artifact = json.loads(ARTIFACT_PATH.read_text())
    artifact["payload"]["deep"]["damage_events"] = [{"round_number": 1}, "not-a-dict"]

    with pytest.raises(ParserArtifactReaderError) as excinfo:
        normalized_events_from_parser_artifact(artifact)

    assert excinfo.value.issues == ["invalid_deep_damage_events"]


def test_parser_handoff_path_mismatch_is_rejected():
    with pytest.raises(ParserArtifactReaderError) as excinfo:
        read_normalized_events(
            "/opt/jc-coach/data/uploads/retained/ff/mismatch.dem",
            parser_artifact_path=ARTIFACT_PATH,
        )

    assert excinfo.value.issues == ["parser_handoff_path_mismatch"]
