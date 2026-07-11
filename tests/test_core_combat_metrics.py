import json
from pathlib import Path

from app.db.models import Match
from app.services.combat_event_derivation import derive_combat_events
from app.services.core_combat_metrics import (
    CORE_COMBAT_METRICS_VERSION,
    calculate_and_store_core_combat_metrics,
    calculate_core_combat_metrics,
)
from app.services.metric_snapshots import metric_snapshot_payload

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "metrics" / "core_combat_events_d02.json"
C04_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "parser" / "combat_derivation_c04_events.json"


def _fixture_payload():
    return json.loads(FIXTURE_PATH.read_text())


def _metrics_by_player(events=None, players=None):
    payload = _fixture_payload()
    results = calculate_core_combat_metrics(
        events or payload["events"],
        players=players if players is not None else payload["players"],
    )
    return {result.player_key: result for result in results}


def _c04_payload():
    return json.loads(C04_FIXTURE_PATH.read_text())


def _c04_derived_metric_input():
    payload = _c04_payload()
    derived = derive_combat_events(payload["events"], tracked_players=payload["players"])
    return {
        "players": payload["players"],
        "events": [*payload["events"], *derived],
    }


def test_core_combat_metrics_are_deterministic_for_fixture_events():
    by_player = _metrics_by_player()

    assert by_player["steam:T1"].metrics == {
        "kills": 1,
        "deaths": 1,
        "ordinary_assists": 0,
        "flash_assists": 0,
        "combined_assists": 0,
        "assists": 0,
        "unclassified_raw_attempted_damage": 80,
        "rounds": 2,
        "survived_rounds": 1,
        "survival_rate": 0.5,
        "kd_ratio": 1.0,
        "headshot_kills": 0,
        "headshot_kill_rate": 0.0,
    }
    assert by_player["steam:T2"].metrics == {
        "kills": 0,
        "deaths": 0,
        "ordinary_assists": 1,
        "flash_assists": 0,
        "combined_assists": 1,
        "assists": 1,
        "unclassified_raw_attempted_damage": 50,
        "rounds": 2,
        "survived_rounds": 2,
        "survival_rate": 1.0,
        "kd_ratio": None,
        "headshot_kills": 0,
        "headshot_kill_rate": 0.0,
    }
    assert by_player["steam:CT1"].metrics == {
        "kills": 1,
        "deaths": 1,
        "ordinary_assists": 0,
        "flash_assists": 0,
        "combined_assists": 0,
        "assists": 0,
        "unclassified_raw_attempted_damage": 100,
        "rounds": 2,
        "survived_rounds": 1,
        "survival_rate": 0.5,
        "kd_ratio": 1.0,
        "headshot_kills": 0,
        "headshot_kill_rate": 0.0,
    }
    assert by_player["steam:T1"].confidence_baseline["source"] == CORE_COMBAT_METRICS_VERSION
    kills_confidence = by_player["steam:T1"].confidence_baseline["metrics"]["kills"]
    assert kills_confidence["level"] == "high"
    assert "event_confidence_high" in kills_confidence["reason_codes"]
    assert kills_confidence["source_trust"]["event_count"] == 2
    assert kills_confidence["hard_recommendation_eligible"] is True


def test_opening_trade_and_survival_metrics_are_deterministic_for_c04_events():
    payload = _c04_derived_metric_input()
    by_player = _metrics_by_player(events=payload["events"], players=payload["players"])

    alpha = by_player["steam:T1"]
    assert alpha.metrics["rounds"] == 3
    assert alpha.metrics["opening_duels"] == 1
    assert alpha.metrics["opening_duel_wins"] == 1
    assert alpha.metrics["opening_deaths"] == 0
    assert alpha.metrics["opening_death_rate"] == 0.0
    assert alpha.metrics["opening_duel_win_rate"] == 1.0
    assert alpha.metrics["traded_deaths"] == 0
    assert alpha.metrics["untraded_deaths"] == 1
    assert alpha.metrics["traded_death_rate"] == 0.0
    assert alpha.metrics["untraded_death_rate"] == 1.0
    assert alpha.metrics["survival_rate"] == 0.667

    bravo = by_player["steam:CT1"]
    assert bravo.metrics["opening_duels"] == 1
    assert bravo.metrics["opening_deaths"] == 1
    assert bravo.metrics["opening_death_rate"] == 0.333
    assert bravo.metrics["opening_duel_win_rate"] == 0.0
    assert bravo.metrics["traded_deaths"] == 1
    assert bravo.metrics["traded_death_rate"] == 1.0
    assert bravo.metrics["untraded_death_rate"] == 0.0
    assert bravo.metrics["survival_rate"] == 0.667

    assert alpha.confidence_baseline["metrics"]["opening_death_rate"]["level"] == "medium"
    assert alpha.confidence_baseline["metrics"]["opening_duel_win_rate"]["level"] == "high"
    traded_confidence = alpha.confidence_baseline["metrics"]["traded_death_rate"]
    assert traded_confidence["level"] == "high"
    assert traded_confidence["hard_recommendation_eligible"] is False
    assert "suppressed_metric_blocks_hard_recommendation" in traded_confidence["reason_codes"]
    assert alpha.confidence_baseline["event_coverage"]["opening_duel_events"] == 3
    assert alpha.confidence_baseline["event_coverage"]["traded_death_events"] == 5


def test_ambiguous_trade_metrics_exclude_unknown_status_and_carry_caveat():
    payload = _c04_derived_metric_input()
    by_player = _metrics_by_player(events=payload["events"], players=payload["players"])

    unknown_b = by_player["steam:UB"]
    assert unknown_b.metrics["ambiguous_traded_deaths"] == 1
    assert unknown_b.metrics["trade_status_known_deaths"] == 0
    assert "traded_death_rate" not in unknown_b.metrics
    assert "untraded_death_rate" not in unknown_b.metrics
    assert unknown_b.confidence_baseline["metrics"]["traded_death_rate"]["level"] == "low"
    assert unknown_b.confidence_baseline["metrics"]["untraded_death_rate"]["level"] == "low"
    assert (
        "low_confidence_blocks_hard_recommendation"
        in unknown_b.confidence_baseline["metrics"]["traded_death_rate"]["reason_codes"]
    )
    assert "Ambiguous traded death events were excluded from traded/untraded death rates." in unknown_b.caveats
    assert (
        "Source events do not include both actor/victim team side; traded death is ambiguous."
        in unknown_b.caveats
    )


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
    assert snapshot_payload["metrics"]["unclassified_raw_attempted_damage"] == 80
    assert "adr" not in snapshot_payload["metrics"]
    assert snapshot_payload["semantic_version"] == "2.0.0"
    assert snapshot_payload["confidence_baseline"]["source"] == CORE_COMBAT_METRICS_VERSION
    assert snapshot_payload["metadata"]["input_event_schema"] == "normalized-parser-events-v1"


def test_c04_opening_trade_survival_metrics_store_in_metric_snapshots(db):
    payload = _c04_derived_metric_input()
    match = Match(source="test", external_match_id="core-combat-d03")
    db.add(match)
    db.commit()
    db.refresh(match)

    snapshots = calculate_and_store_core_combat_metrics(
        db,
        match_id=match.id,
        normalized_events=payload["events"],
        players=payload["players"],
        source_event_set_id="fixture:c04-derived:d03",
    )

    alpha = next(snapshot for snapshot in snapshots if snapshot.player_key == "steam:T1")
    snapshot_payload = metric_snapshot_payload(alpha)
    assert snapshot_payload["source"] == "core_combat_metrics"
    assert snapshot_payload["source_event_set_id"] == "fixture:c04-derived:d03"
    assert snapshot_payload["metrics"]["opening_duel_win_rate"] == 1.0
    assert snapshot_payload["metrics"]["opening_death_rate"] == 0.0
    assert snapshot_payload["metrics"]["traded_death_rate"] == 0.0
    assert snapshot_payload["metrics"]["untraded_death_rate"] == 1.0
    assert snapshot_payload["metrics"]["survival_rate"] == 0.667
    assert snapshot_payload["confidence_baseline"]["source"] == CORE_COMBAT_METRICS_VERSION
    assert snapshot_payload["metadata"]["schema_version"] == CORE_COMBAT_METRICS_VERSION
