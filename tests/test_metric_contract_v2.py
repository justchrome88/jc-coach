import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from app.db.models import Match, MetricSnapshot, SteamAccount, User
from app.services.core_combat_metrics import calculate_core_combat_metrics
from app.services.metric_downstream_state import (
    MATCH_124_DISPOSITIONS,
    match_124_downstream_plan,
    stale_evidence_marker,
)
from app.services.metric_snapshots import (
    MetricSnapshotAnalysisScope,
    create_metric_snapshot,
    deterministic_input_hash,
    metric_snapshot_payload,
    process_persisted_match_metric_snapshots_for_coach_loop,
    select_metric_snapshots_for_analysis_scope,
)
from app.services.parsing.artifact_reader import normalized_events_from_parser_artifact
from app.services.parsing.match_phase import accepted_events, accepted_match_phase, player_participation_rounds
from app.services.shared.weapon_names import canonical_weapon_name

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/metrics/match_124_metric_contract_v2.json").read_text())


def test_match_124_independent_golden_contract_and_quarantine() -> None:
    expected = FIXTURE["independent_expected"]
    rows = FIXTURE["ledger_rows"]
    calculated = {
        "rounds": len(rows),
        "kills": sum(row["k"] for row in rows),
        "deaths": sum(row["d"] for row in rows),
        "ordinary_assists": sum(row["oa"] for row in rows),
        "flash_assists": sum(row["fa"] for row in rows),
        "headshot_kills": sum(row["hs"] for row in rows),
        "raw_attempted_enemy_damage": sum(row["enemy_raw"] for row in rows),
        "team_damage": sum(row["team"] for row in rows),
        "raw_utility_event_amount": sum(row["utility_raw"] for row in rows),
    }
    calculated["combined_assists"] = calculated["ordinary_assists"] + calculated["flash_assists"]
    calculated["kd_ratio"] = calculated["kills"] / calculated["deaths"]
    calculated["headshot_kill_rate"] = calculated["headshot_kills"] / calculated["kills"] * 100
    assert calculated == expected
    assert expected == {
        "rounds": 20,
        "kills": 16,
        "deaths": 10,
        "kd_ratio": 1.6,
        "ordinary_assists": 3,
        "flash_assists": 1,
        "combined_assists": 4,
        "headshot_kills": 10,
        "headshot_kill_rate": 62.5,
        "raw_attempted_enemy_damage": 2165,
        "team_damage": 5,
        "raw_utility_event_amount": 149,
    }
    assert {"adr", "kast"}.issubset(FIXTURE["quarantined_metric_keys"])


def test_match_124_phase_excludes_post_match_and_keeps_quiet_rounds() -> None:
    phase_fixture = FIXTURE["phase"]
    events = [
        {
            "event_type": "round_timing",
            "round_number": round_number,
            "tick": phase_fixture["final_round_end_tick"] if round_number == 19 else 1000 + round_number,
            "source_event": "round_end",
            "context": {"boundary": "round_end"},
        }
        for round_number in phase_fixture["accepted_round_numbers"]
    ]
    events.append(
        {
            "event_type": "player_death",
            "round_number": 20,
            "tick": phase_fixture["post_match_event"]["tick"],
            "actor": None,
            "victim": {"steamid": FIXTURE["demo_identity"]["owner_steam_id"]},
            "context": {},
        }
    )
    phase = accepted_match_phase(events)
    assert len(phase.round_numbers) == 20
    assert phase.final_round_end_tick == 114168
    assert not any(event.get("round_number") == 20 for event in accepted_events(events, phase))
    rounds, complete = player_participation_rounds(
        f"steam:{FIXTURE['demo_identity']['owner_steam_id']}", events, phase
    )
    assert len(rounds) == 20
    assert complete is False
    assert len(phase_fixture["activity_round_numbers"]) == 17
    assert set(phase_fixture["quiet_round_numbers"]).issubset(rounds)


def test_retained_round_end_numbering_and_nested_flash_assist_are_preserved() -> None:
    artifact = {
        "parser_name": "demoparser2",
        "parser_version": "0.41.3",
        "payload": {
            "deep": {
                "rounds": [
                    {"round_number": 0, "start_tick": 10, "freeze_end_tick": 20, "end_tick": None},
                    {"round_number": 1, "start_tick": 110, "freeze_end_tick": 120, "end_tick": 100},
                    {"round_number": 2, "start_tick": None, "freeze_end_tick": None, "end_tick": 200},
                ],
                "duels": [{
                    "round_number": 1,
                    "tick": 150,
                    "attacker_name": "ally",
                    "attacker_steamid": "ally",
                    "victim_name": "enemy",
                    "victim_steamid": "enemy",
                    "assister_name": "owner",
                    "assister_steamid": "owner",
                    "headshot": False,
                    "raw": {"assistedflash": True},
                }],
                "players": [],
            }
        },
    }
    events = normalized_events_from_parser_artifact(artifact)
    assert accepted_match_phase(events).round_numbers == (0, 1)
    owner = next(result for result in calculate_core_combat_metrics(events) if result.player_steamid == "owner")
    assert owner.metrics["ordinary_assists"] == 0
    assert owner.metrics["flash_assists"] == 1
    assert owner.metrics["combined_assists"] == 1


def test_weapon_aliases_are_canonical_and_do_not_split() -> None:
    assert canonical_weapon_name("ak47") == "ak47"
    assert canonical_weapon_name("weapon_ak47") == "ak47"
    buckets = {}
    for raw in ("ak47", "weapon_ak47"):
        key = canonical_weapon_name(raw)
        buckets[key] = buckets.get(key, 0) + 1
    assert buckets == {"ak47": 2}


def test_versioned_snapshot_identity_and_trusted_payload_fail_closed(db, monkeypatch) -> None:
    owner = User(email="contract-v2@example.test", password_hash="hash")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    db.add(SteamAccount(user_id=owner.id, steam_id="owner-v2"))
    match = Match(user_id=owner.id, source="test", external_match_id="contract-v2")
    db.add(match)
    db.commit()
    db.refresh(match)
    legacy = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:owner-v2",
        player_steamid="owner-v2",
        source="core_combat_metrics",
        metric_domain="core_combat",
        semantic_version="1.0.0",
        validation_status="legacy_unverified",
        metrics={"adr": 103.33},
        confidence_baseline={},
    )
    accepted = create_metric_snapshot(
        db,
        owner_user_id=owner.id,
        match_id=match.id,
        player_key="steam:owner-v2",
        player_steamid="owner-v2",
        source="core_combat_metrics",
        metric_domain="core_combat",
        semantic_version="2.0.0",
        validation_status="validated",
        source_event_set_id="events:v2",
        metrics={"kills": 16, "adr": 83},
        confidence_baseline={},
        metadata={
            "metric_validation": {
                "kills": {"status": "validated"},
                "adr": {"status": "quarantined"},
            }
        },
    )
    assert legacy.id != accepted.id
    assert db.query(MetricSnapshot).count() == 2
    trusted = metric_snapshot_payload(accepted, trusted_only=True)
    assert trusted["metrics"] == {"kills": 16}
    scope = MetricSnapshotAnalysisScope(
        match_ids=(match.id,), owner_user_id=owner.id, player_key="steam:owner-v2",
        player_steamid="owner-v2", semantic_versions=("2.0.0",), validation_statuses=("validated",)
    )
    assert [row.id for row in select_metric_snapshots_for_analysis_scope(db, scope)] == [accepted.id]
    called = {}
    monkeypatch.setattr(
        "app.services.ai_coach.process_owner_match_metric_snapshots_for_coach_loop",
        lambda _db, **kwargs: called.update(kwargs) or {"selected_metric_snapshot_ids": [accepted.id]},
    )
    process_persisted_match_metric_snapshots_for_coach_loop(
        db, user_id=owner.id, match_id=match.id, metric_snapshots=[legacy, accepted]
    )
    assert called["metric_snapshot_ids"] == []


def test_contract_provenance_records_rate_numerators_and_denominators(db) -> None:
    owner = User(email="provenance-v2@example.test", password_hash="hash")
    db.add(owner)
    db.commit()
    match = Match(user_id=owner.id, source="test", external_match_id="provenance-v2")
    db.add(match)
    db.commit()
    snapshot = create_metric_snapshot(
        db,
        owner_user_id=owner.id,
        match_id=match.id,
        player_key="steam:provenance-v2",
        source="core_combat_metrics",
        metric_domain="core_combat",
        semantic_version="2.0.0",
        validation_status="validated",
        source_event_set_id="events:provenance-v2",
        metrics={"kills": 16, "deaths": 10, "kd_ratio": 1.6, "headshot_kills": 10,
                 "headshot_kill_rate": 62.5},
        confidence_baseline={},
    )
    provenance = json.loads(snapshot.metadata_json)["provenance"]
    assert provenance["numerators"]["kd_ratio"] == 16
    assert provenance["denominators"]["kd_ratio"] == 10
    assert provenance["numerators"]["headshot_kill_rate"] == 10
    assert provenance["denominators"]["headshot_kill_rate"] == 16


def test_deterministic_provenance_hash() -> None:
    left = deterministic_input_hash({"b": 2, "a": 1})
    right = deterministic_input_hash({"a": 1, "b": 2})
    assert left == right
    assert len(left) == 64


def test_isolated_snapshot_schema_upgrade_and_rollback(tmp_path) -> None:
    database = tmp_path / "metric-contract.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        CREATE TABLE matches (id INTEGER PRIMARY KEY, user_id INTEGER);
        CREATE TABLE demo_parse_artifacts (id INTEGER PRIMARY KEY);
        CREATE TABLE metric_snapshots (
          id INTEGER PRIMARY KEY, match_id INTEGER NOT NULL, player_key TEXT NOT NULL,
          player_name TEXT, player_steamid TEXT, source TEXT NOT NULL,
          source_parser_artifact_id INTEGER, source_event_set_id TEXT, metrics_json TEXT NOT NULL,
          confidence_baseline_json TEXT NOT NULL, caveats_json TEXT NOT NULL, metadata_json TEXT NOT NULL,
          created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
          UNIQUE(match_id, player_key, source)
        );
        INSERT INTO users VALUES (17);
        INSERT INTO matches VALUES (124, 17);
        INSERT INTO metric_snapshots VALUES
          (1138,124,'steam:owner','JC','owner','core',91,'events','{}','{}','[]','{}','2026-01-01','2026-01-01');
        """
    )
    connection.close()
    command = [
        sys.executable,
        str(ROOT / "scripts/migrate_metric_snapshot_contract_v2.py"),
        "--database",
        str(database),
    ]
    assert subprocess.run([*command, "--direction", "upgrade"], check=False).returncode == 0
    connection = sqlite3.connect(database)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(metric_snapshots)")}
    row = connection.execute(
        "SELECT owner_user_id, semantic_version, validation_status FROM metric_snapshots"
    ).fetchone()
    connection.execute(
        """INSERT INTO metric_snapshots (
        owner_user_id,match_id,player_key,source,metric_domain,semantic_version,scope,
        validation_status,metrics_json,confidence_baseline_json,caveats_json,metadata_json
        ) VALUES (17,124,'steam:owner','core','core_combat','2.0.0','player_match',
        'validated','{}','{}','[]','{}')"""
    )
    inserted_timestamps = connection.execute(
        "SELECT created_at,updated_at FROM metric_snapshots WHERE semantic_version='2.0.0'"
    ).fetchone()
    connection.rollback()
    connection.close()
    assert {"owner_user_id", "semantic_version", "validation_status"}.issubset(columns)
    assert row == (17, "1.0.0", "legacy_unverified")
    assert inserted_timestamps[0] and inserted_timestamps[1]
    assert subprocess.run([*command, "--direction", "rollback"], check=False).returncode == 0
    connection = sqlite3.connect(database)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(metric_snapshots)")}
    connection.close()
    assert "semantic_version" not in columns


def test_migration_refuses_production_database() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/migrate_metric_snapshot_contract_v2.py"),
         "--database", str(ROOT / "data/cs2_coach.db"), "--direction", "upgrade", "--dry-run"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "forbidden" in result.stderr


def test_downstream_stale_superseded_plan_is_dependency_scoped_and_idempotent() -> None:
    plan = match_124_downstream_plan()
    assert {item["object_id"] for item in plan} == {3, 9, 59, 110, 111, 1138, 1149}
    assert len({item["idempotency_key"] for item in plan}) == len(plan)
    analysis = next(item for item in MATCH_124_DISPOSITIONS if item.object_type == "analysis_run")
    assert analysis.dependency_snapshot_ids == (1138, 1149)
    marker = stale_evidence_marker({"status": "historical"}, analysis)
    assert marker["status"] == "historical"
    assert marker["metric_assurance"]["state"] == "superseded"
