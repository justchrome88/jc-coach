import json
from pathlib import Path

from app.db.models import Match
from app.services.core_combat_metrics import (
    CORE_COMBAT_METRICS_VERSION,
    calculate_and_store_core_combat_metrics,
    calculate_core_combat_metrics,
)
from app.services.metric_snapshots import metric_snapshot_payload

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "metrics" / "core_combat_events_d02.json"


def _fixture_payload():
    return json.loads(FIXTURE_PATH.read_text())


def _metrics_by_player(events=None, players=None):
    payload = _fixture_payload()
    results = calculate_core_combat_metrics(
        events or payload["events"],
        players=players if players is not None else payload["players"],
    )
    return {result.player_key: result for result in results}


def test_core_combat_metrics_are_deterministic_for_fixture_events():
    by_player = _metrics_by_player()

    assert by_player["steam:T1"].metrics == {
        "kills": 1,
        "deaths": 1,
        "assists": 0,
        "damage": 80,
        "rounds": 2,
        "adr": 40.0,
        "survived_rounds": 1,
        "survival_rate": 0.5,
    }
    assert by_player["steam:T2"].metrics == {
        "kills": 0,
        "deaths": 0,
        "assists": 1,
        "damage": 50,
        "rounds": 2,
        "adr": 25.0,
        "survived_rounds": 2,
        "survival_rate": 1.0,
    }
    assert by_player["steam:CT1"].metrics == {
        "kills": 1,
        "deaths": 1,
        "assists": 0,
        "damage": 100,
        "rounds": 2,
        "adr": 50.0,
        "survived_rounds": 1,
        "survival_rate": 0.5,
    }
    assert by_player["steam:T1"].confidence_baseline["source"] == CORE_COMBAT_METRICS_VERSION
    assert by_player["steam:T1"].confidence_baseline["metrics"]["kills"] == "high"


def test_missing_event_streams_produce_partial_metrics_and_caveats_not_fake_zeroes():
    events = [
        {
            "schema_version": "normalized-parser-events-v1",
            "event_type": "round_timing",
            "category": "round",
            "support": "supported",
            "source": {"kind": "fixture"},
            "round_number": 1,
            "tick": 8000,
            "time_seconds": 125.0,
            "actor": None,
            "victim": None,
            "context": {"boundary": "round_end"},
            "source_event": "round_end",
            "confidence": "medium",
            "caveats": [],
            "payload": {},
        },
        {
            "schema_version": "normalized-parser-events-v1",
            "event_type": "damage",
            "category": "damage",
            "support": "supported",
            "source": {"kind": "fixture"},
            "round_number": 1,
            "tick": 1200,
            "time_seconds": 18.75,
            "actor": {"name": "Alpha", "steamid": "T1"},
            "victim": {"name": "Bravo", "steamid": "CT1"},
            "context": {"damage_health": None},
            "source_event": "player_hurt",
            "confidence": "low",
            "caveats": ["Source row omitted health damage; ADR consumers must ignore this row."],
            "payload": {},
        },
    ]

    alpha = _metrics_by_player(events=events, players=[{"name": "Alpha", "steamid": "T1"}])["steam:T1"]

    assert alpha.metrics == {"rounds": 1}
    assert "kills" not in alpha.metrics
    assert "deaths" not in alpha.metrics
    assert "assists" not in alpha.metrics
    assert "damage" not in alpha.metrics
    assert "adr" not in alpha.metrics
    assert "survival_rate" not in alpha.metrics
    assert "Kill events unavailable; kills are omitted instead of filled as zero." in alpha.caveats
    assert "Death events unavailable; deaths are omitted instead of filled as zero." in alpha.caveats
    assert "Some damage events omitted health damage; those rows were ignored." in alpha.caveats
    assert (
        "Damage events for this player omitted health damage; damage and ADR-like metrics are omitted."
        in alpha.caveats
    )
    assert "Round survival events unavailable or incomplete; survival metrics are omitted." in alpha.caveats


def test_core_combat_metrics_store_and_read_through_metric_snapshots(db):
    payload = _fixture_payload()
    match = Match(source="test", external_match_id="core-combat-d02")
    db.add(match)
    db.commit()
    db.refresh(match)

    first = calculate_and_store_core_combat_metrics(
        db,
        match_id=match.id,
        normalized_events=payload["events"],
        players=payload["players"],
        source_event_set_id="fixture:d02",
    )
    second = calculate_and_store_core_combat_metrics(
        db,
        match_id=match.id,
        normalized_events=payload["events"],
        players=payload["players"],
        source_event_set_id="fixture:d02",
    )

    assert {snapshot.id for snapshot in second} == {snapshot.id for snapshot in first}
    assert len(second) == 3

    alpha = next(snapshot for snapshot in second if snapshot.player_key == "steam:T1")
    snapshot_payload = metric_snapshot_payload(alpha)
    assert snapshot_payload["source"] == "core_combat_metrics"
    assert snapshot_payload["source_event_set_id"] == "fixture:d02"
    assert snapshot_payload["metrics"]["adr"] == 40.0
    assert snapshot_payload["confidence_baseline"]["source"] == CORE_COMBAT_METRICS_VERSION
    assert snapshot_payload["metadata"]["input_event_schema"] == "normalized-parser-events-v1"
