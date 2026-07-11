from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.services.coach_metric_pack import calculate_coach_metric_pack

OWNER = "76561198056634139"
TEAMMATE = "76561198000000001"
ENEMIES = [f"7656119900000000{index}" for index in range(1, 7)]
ROOT = Path(__file__).resolve().parents[1]


def _evidence(*, events: dict | None = None, rounds: int = 2) -> dict:
    round_rows = [
        {
            "round_number": number,
            "start_tick": number * 500,
            "end_tick": (number + 1) * 500 - 1,
            "phase": "regulation",
        }
        for number in range(rounds)
    ]
    return {
        "schema_version": "coach-metric-events-v1",
        "payload_version": "fixture-v1",
        "parser": {"name": "independent_fixture", "version": "1"},
        "identity": {
            "match_id": 1,
            "demo_sha1": "a" * 40,
            "owner_steamid": OWNER,
            "owner_name": "Owner",
            "map_name": "de_test",
        },
        "phase": {
            "classification": "completed_regulation_and_overtime",
            "rounds": round_rows,
            "final_round_end_tick": round_rows[-1]["end_tick"],
            "incomplete_round_starts": [],
        },
        "participation": {
            "roster_steamids": [OWNER, TEAMMATE, *ENEMIES],
            "owner_spawns": [
                {
                    "kind": "spawn",
                    "round_number": number,
                    "tick": number * 500,
                    "steamid": OWNER,
                    "team": 3,
                    "warmup": False,
                }
                for number in range(rounds)
            ],
            "owner_disconnects": [],
            "owner_connects": [],
            "owner_team_events": [],
        },
        "events": {
            "deaths": [],
            "hurts": [],
            "shots": [],
            "blinds": [],
            "detonations": [],
            **(events or {}),
        },
    }


def _death(
    tick: int,
    attacker: str,
    victim: str,
    *,
    round_number: int = 0,
    assister: str | None = None,
    assistedflash: bool = False,
    headshot: bool = False,
) -> dict:
    attacker_team = 3 if attacker in {OWNER, TEAMMATE} else 2
    victim_team = 3 if victim in {OWNER, TEAMMATE} else 2
    return {
        "round_number": round_number,
        "tick": tick,
        "attacker_steamid": attacker,
        "attacker_team": attacker_team,
        "victim_steamid": victim,
        "victim_team": victim_team,
        "assister_steamid": assister,
        "assister_team": 3 if assister else None,
        "assistedflash": assistedflash,
        "headshot": headshot,
        "weapon": "ak47",
    }


def _hurt(
    tick: int,
    attacker: str,
    victim: str,
    damage: int,
    health_after: int,
    *,
    round_number: int = 0,
    weapon: str = "ak47",
    hitgroup: str = "chest",
) -> dict:
    return {
        "round_number": round_number,
        "tick": tick,
        "attacker_steamid": attacker,
        "attacker_team": 3 if attacker in {OWNER, TEAMMATE} else 2,
        "victim_steamid": victim,
        "victim_team": 3 if victim in {OWNER, TEAMMATE} else 2,
        "damage_health": damage,
        "victim_health_after": health_after,
        "hitgroup": hitgroup,
        "weapon": weapon,
    }


def test_metric_pack_transparent_contracts_cover_edges() -> None:
    events = {
        "deaths": [
            _death(11, OWNER, ENEMIES[0], headshot=True),
            _death(14, TEAMMATE, ENEMIES[1], assister=OWNER, assistedflash=True),
            _death(16, TEAMMATE, ENEMIES[2], assister=OWNER),
            _death(20, ENEMIES[3], TEAMMATE),
            _death(30, OWNER, ENEMIES[3]),
            _death(40, ENEMIES[4], TEAMMATE),
            _death(400, OWNER, ENEMIES[4]),
            _death(650, ENEMIES[5], OWNER, round_number=1),
            _death(660, TEAMMATE, ENEMIES[5], round_number=1),
            # Explicit post-match evidence is excluded by the participation/round filter.
            _death(1001, ENEMIES[5], OWNER, round_number=2),
        ],
        "hurts": [
            _hurt(11, OWNER, ENEMIES[0], 140, 0, hitgroup="head"),
            _hurt(620, OWNER, ENEMIES[5], 150, 0, round_number=1, weapon="hegrenade"),
            _hurt(630, OWNER, TEAMMATE, 5, 95, round_number=1, weapon="hegrenade"),
        ],
        "shots": [
            {"round_number": 0, "tick": 10, "player_steamid": OWNER, "player_team": 3, "weapon": "weapon_ak47"},
            {"round_number": 0, "tick": 12, "player_steamid": OWNER, "player_team": 3, "weapon": "ak47"},
        ],
        "blinds": [
            {
                "round_number": 1,
                "tick": 690,
                "attacker_steamid": OWNER,
                "attacker_team": 3,
                "victim_steamid": ENEMIES[5],
                "victim_team": 2,
                "blind_duration": 10.0,
                "entity_id": "1",
            },
            {
                "round_number": 1,
                "tick": 700,
                "attacker_steamid": OWNER,
                "attacker_team": 3,
                "victim_steamid": TEAMMATE,
                "victim_team": 3,
                "blind_duration": 2.0,
                "entity_id": "1",
            },
        ],
        "detonations": [
            {
                "round_number": 1, "tick": 610, "owner_steamid": OWNER, "owner_team": 3,
                "utility_type": "he", "entity_id": "2",
            },
            {
                "round_number": 1, "tick": 680, "owner_steamid": OWNER, "owner_team": 3,
                "utility_type": "smoke", "entity_id": "3",
            },
            {
                "round_number": 1, "tick": 685, "owner_steamid": OWNER, "owner_team": 3,
                "utility_type": "flash", "entity_id": "1",
            },
            {
                "round_number": 1, "tick": 687, "owner_steamid": OWNER, "owner_team": 3,
                "utility_type": "fire", "entity_id": "4",
            },
        ],
    }

    result = calculate_coach_metric_pack(_evidence(events=events))

    assert result.performance == {
        "rounds_played": 2,
        "kills": 3,
        "deaths": 1,
        "kd_ratio": 3.0,
        "kills_per_round": 1.5,
        "ordinary_assists": 1,
        "flash_assists": 1,
        "combined_assists": 2,
        "headshot_kills": 1,
        "headshot_kill_rate": 33.333,
        "survived_rounds": 1,
        "survival_rate": 0.5,
        "effective_enemy_damage": 200,
        "adr": 100.0,
        "kast": 100.0,
        "opening_duel_attempts": 2,
        "opening_duel_wins": 1,
        "opening_duel_losses": 1,
        "opening_duel_win_rate": 0.5,
        "opening_deaths": 1,
        "opening_death_rate": 0.5,
        "multi_kill_rounds": 1,
        "multi_kill_2_rounds": 0,
        "multi_kill_3_rounds": 1,
        "multi_kill_4_rounds": 0,
        "multi_kill_5_plus_rounds": 0,
        "trade_opportunities": 2,
        "trade_kills": 1,
        "traded_deaths": 1,
        "untraded_deaths": 0,
        "trade_status_known_deaths": 1,
        "trade_success_rate": 0.5,
        "traded_death_rate": 1.0,
        "untraded_death_rate": 0.0,
    }
    assert result.utility == {
        "he_detonations": 1,
        "smoke_detonations": 1,
        "flash_detonations": 1,
        "fire_grenade_detonations": 1,
        "enemy_he_damage": 100,
        "enemy_fire_damage": 0,
        "effective_enemy_utility_damage": 100,
        "utility_damage_per_round": 50.0,
        "enemies_effectively_flashed": 1,
        "effective_enemy_flash_duration": 4.828,
        "smokes_used": 1,
    }
    assert result.aim == {
        "accepted_shots": 2,
        "accepted_hits": 1,
        "shot_accuracy": 50.0,
        "head_hits": 1,
        "hit_based_headshot_rate": 100.0,
        "first_shots": 2,
        "first_shot_hits": 1,
        "first_bullet_accuracy": 50.0,
        "engagements_with_kill": 2,
        "first_shot_to_kill_ms": 148.5,
        "first_damage_to_kill_ms": 0.0,
    }
    assert result.metadata["damage_ledger"][0]["effective_damage"] == 100
    assert result.metadata["damage_ledger"][2]["relation"] == "team"
    assert result.metadata["accepted_phase"]["round_numbers"] == [0, 1]


def test_metric_pack_zero_deaths_and_zero_shots_are_explicitly_unavailable() -> None:
    result = calculate_coach_metric_pack(_evidence(rounds=1))

    assert result.performance["rounds_played"] == 1
    assert result.performance["deaths"] == 0
    assert result.performance["kd_ratio"] is None
    assert result.performance["survival_rate"] == 1.0
    assert result.performance["kast"] == 100.0
    assert result.aim["accepted_shots"] == 0
    assert result.aim["shot_accuracy"] is None
    assert result.aim["first_bullet_accuracy"] is None
    assert {"kd_ratio", "shot_accuracy", "first_bullet_accuracy"} <= set(
        result.metadata["unavailable_metrics"]
    )


@pytest.mark.parametrize("fixture", json.loads(
    (ROOT / "tests/fixtures/metrics/coach_metric_real_demo_corpus.json").read_text(encoding="utf-8")
)["fixtures"])
def test_real_demo_golden_corpus(fixture: dict) -> None:
    raw = (ROOT / fixture["fixture"]).read_bytes().rstrip(b"\n")
    assert hashlib.sha256(raw).hexdigest() == fixture["ledger_checksum"]
    evidence = json.loads(raw)

    result = calculate_coach_metric_pack(evidence)

    assert result.input_event_hash == fixture["event_set_hash"]
    assert result.player_steamid == fixture["owner_steamid"]
    assert result.metrics | fixture["expected_metrics"] == result.metrics
    assert {key: result.metrics[key] for key in fixture["expected_metrics"]} == fixture["expected_metrics"]


def test_match_124_golden_retains_m03_truth_and_closes_quarantined_inputs() -> None:
    corpus = json.loads(
        (ROOT / "tests/fixtures/metrics/coach_metric_real_demo_corpus.json").read_text(encoding="utf-8")
    )
    fixture = next(item for item in corpus["fixtures"] if item["match_id"] == 124)
    metrics = fixture["expected_metrics"]

    assert metrics | {
        "rounds_played": 20,
        "kills": 16,
        "deaths": 10,
        "kd_ratio": 1.6,
        "ordinary_assists": 3,
        "flash_assists": 1,
        "combined_assists": 4,
        "headshot_kills": 10,
        "headshot_kill_rate": 62.5,
        "effective_enemy_damage": 1643,
        "adr": 82.15,
        "kast": 70.0,
        "effective_enemy_utility_damage": 144,
    } == metrics
