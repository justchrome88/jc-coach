import json

import pytest

from app.db.models import DemoParseArtifact, Match, MetricSnapshot
from app.services.metric_snapshots import (
    create_metric_snapshot,
    find_metric_snapshot,
    get_metric_snapshot,
    list_metric_snapshots,
    metric_snapshot_payload,
    update_metric_snapshot,
    upsert_metric_snapshot,
)


def test_metric_snapshot_create_read_and_payload_are_independent_of_parser_artifact(db):
    match = _persist_match(db)

    snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:76561198000000001",
        player_name="JC",
        player_steamid="76561198000000001",
        source="normalized_events",
        source_event_set_id="events:c02:rounds-1-2",
        metrics={"adr": 84.5, "kills": 17},
        confidence_baseline={"source": "parser-artifact-v0", "metrics": {"adr": "medium", "kills": "trusted"}},
        caveats=["adr derived from normalized damage events"],
        metadata={"schema_version": "metric-snapshot-v1"},
    )

    persisted = get_metric_snapshot(db, snapshot.id)
    assert persisted is not None
    assert persisted.source_parser_artifact_id is None
    assert json.loads(persisted.metrics_json) == {"adr": 84.5, "kills": 17}

    payload = metric_snapshot_payload(persisted)
    assert payload["match_id"] == match.id
    assert payload["player_key"] == "steam:76561198000000001"
    assert payload["source"] == "normalized_events"
    assert payload["source_event_set_id"] == "events:c02:rounds-1-2"
    assert payload["metrics"] == {"adr": 84.5, "kills": 17}
    assert payload["confidence_baseline"]["metrics"]["adr"] == "medium"
    assert payload["caveats"] == ["adr derived from normalized damage events"]
    assert payload["metadata"] == {"schema_version": "metric-snapshot-v1"}


def test_metric_snapshot_updates_without_touching_parser_artifact(db):
    match = _persist_match(db)
    snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="name:JC",
        source="manual_fixture",
        metrics={"kills": 10},
        confidence_baseline={"metrics": {"kills": "medium"}},
    )

    updated = update_metric_snapshot(
        db,
        snapshot,
        metrics={"kills": 12, "deaths": 9},
        confidence_baseline={"metrics": {"kills": "trusted", "deaths": "trusted"}},
        caveats=["fixture update"],
        metadata={"updated_by": "repository_test"},
    )

    payload = metric_snapshot_payload(updated)
    assert payload["metrics"] == {"deaths": 9, "kills": 12}
    assert payload["confidence_baseline"]["metrics"] == {"deaths": "trusted", "kills": "trusted"}
    assert payload["caveats"] == ["fixture update"]
    assert payload["metadata"] == {"updated_by": "repository_test"}


def test_metric_snapshot_records_parser_artifact_and_event_set_metadata(db):
    match = _persist_match(db)
    artifact = DemoParseArtifact(
        match_id=match.id,
        parser_name="fixture-parser",
        parser_version="c02",
        payload_version="parser-artifact-v0.10",
        status="completed",
        source_demo_file="/tmp/retained/demo.dem",
        demo_sha1="a" * 40,
        event_counts_json=json.dumps({"damage": 3}),
        confidence_json=json.dumps({"source": "fixture"}),
        data_gaps_json=json.dumps([]),
        payload_json=json.dumps({"normalized_events": []}),
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    snapshot = upsert_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:76561198000000002",
        source="parser_artifact",
        source_parser_artifact_id=artifact.id,
        source_event_set_id="parser-artifact-v0.10:damage-events",
        metrics={"damage": 255, "adr": 85.0},
        confidence_baseline={"artifact_id": artifact.id, "metrics": {"damage": "trusted", "adr": "medium"}},
        metadata={"event_schema": "normalized-events-v0.10"},
    )

    found = find_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:76561198000000002",
        source="parser_artifact",
    )
    assert found is not None
    assert found.id == snapshot.id
    assert found.source_parser_artifact_id == artifact.id
    assert metric_snapshot_payload(found)["metadata"] == {"event_schema": "normalized-events-v0.10"}

    snapshots = list_metric_snapshots(db, match_id=match.id, source="parser_artifact")
    assert [item.id for item in snapshots] == [snapshot.id]


def test_metric_snapshot_upsert_updates_existing_player_match_source_row(db):
    match = _persist_match(db)

    first = upsert_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:76561198000000003",
        source="normalized_events",
        metrics={"kills": 8},
        confidence_baseline={"metrics": {"kills": "medium"}},
    )
    second = upsert_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:76561198000000003",
        source="normalized_events",
        metrics={"kills": 11},
        confidence_baseline={"metrics": {"kills": "trusted"}},
        source_event_set_id="events:updated",
    )

    assert second.id == first.id
    assert db.query(MetricSnapshot).count() == 1
    payload = metric_snapshot_payload(second)
    assert payload["metrics"] == {"kills": 11}
    assert payload["confidence_baseline"] == {"metrics": {"kills": "trusted"}}
    assert payload["source_event_set_id"] == "events:updated"


def test_metric_snapshot_rejects_missing_match(db):
    with pytest.raises(ValueError, match="match_id does not exist"):
        create_metric_snapshot(
            db,
            match_id=999,
            player_key="steam:missing",
            source="normalized_events",
            metrics={"kills": 1},
            confidence_baseline={"metrics": {"kills": "medium"}},
        )


def _persist_match(db) -> Match:
    match = Match(source="test", external_match_id="metric-snapshot-match")
    db.add(match)
    db.commit()
    db.refresh(match)
    return match
