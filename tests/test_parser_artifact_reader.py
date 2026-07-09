import json
from pathlib import Path

import pytest

from app.services.event_metric_dictionary import EVENT_METRIC_DICTIONARY, NORMALIZED_EVENT_SCHEMA
from app.services.parser_artifact_reader import (
    NORMALIZED_EVENT_SCHEMA_VERSION,
    NormalizedEventValidationError,
    ParserArtifactReaderError,
    normalized_events_from_parser_artifact,
    read_normalized_events,
    read_normalized_events_from_artifact_file,
    validate_normalized_event,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "parser"
ARTIFACT_PATH = FIXTURE_DIR / "parser_artifact_c02.json"
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

    kill = next(event for event in events if event["event_type"] == "player_kill")
    assert kill["round_number"] == 1
    assert kill["tick"] == 2500
    assert kill["time_seconds"] == 39.062
    assert kill["actor"] == {"name": "Synthetic Player", "steamid": "SYNTHETIC_STEAM_ID"}
    assert kill["victim"] == {"name": "Synthetic Opponent", "steamid": "SYNTHETIC_OPPONENT_ID"}
    assert kill["context"]["weapon"] == "ak47"
    assert kill["confidence"] == "high"


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
