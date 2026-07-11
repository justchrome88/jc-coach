from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.services.metrics.coach_pack import parse_coach_metric_evidence

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests/fixtures/metrics/coach_metric_real_demo_corpus"
MANIFEST = ROOT / "tests/fixtures/metrics/coach_metric_real_demo_corpus.json"
OWNER = "76561198056634139"

DEMOS = {
    29: (
        "data/uploads/20260704143015_180c6dcc40_CSGO-n6MHE-8AhD4-MnDuL-4cTuv-jBcBN.dem",
        "180c6dcc409b8e691d6f689793db31bf2c23da2a",
        "de_nuke",
        ["zero_utility", "low_performance", "opening_and_trade"],
    ),
    117: (
        "data/uploads/retained/d4/d4b2672e73f3c20c74408159ffeabd2f25316861.dem",
        "d4b2672e73f3c20c74408159ffeabd2f25316861",
        "de_dust2",
        ["high_utility", "he_and_fire", "flash_assist"],
    ),
    120: (
        "data/uploads/retained/dd/dd6c0a87aed91932eed4ed2b074d8bccc0273c3e.dem",
        "dd6c0a87aed91932eed4ed2b074d8bccc0273c3e",
        "de_overpass",
        ["overtime", "trade_variety", "aim_timeline"],
    ),
    122: (
        "data/uploads/retained/37/374e78cd2fed73ecc0362349444602ce4f5715bf.dem",
        "374e78cd2fed73ecc0362349444602ce4f5715bf",
        "de_anubis",
        ["incomplete_round_exclusion", "missing_player_info_fallback", "multi_kill"],
    ),
    124: (
        "data/uploads/retained/fc/fc3aac7a6176d1ec7b827762803fb4d333ecc6aa.dem",
        "fc3aac7a6176d1ec7b827762803fb4d333ecc6aa",
        "de_anubis",
        ["accepted_match_124", "post_match_death", "quiet_round", "team_damage", "side_switch"],
    ),
}

# These values were transcribed from independent, line-by-line event ledgers:
# death/assist ledgers, remaining-health hurt ledgers, grenade/blind ledgers and
# shot/engagement ledgers. This builder intentionally does not import or call
# calculate_coach_metric_pack.
EXPECTED: dict[int, dict[str, Any]] = {
    29: {
        "rounds_played": 18, "kills": 4, "deaths": 14, "kd_ratio": 0.286,
        "kills_per_round": 0.222, "ordinary_assists": 1, "flash_assists": 0,
        "combined_assists": 1, "headshot_kills": 2, "headshot_kill_rate": 50.0,
        "survival_rate": 0.222, "effective_enemy_damage": 584, "adr": 32.444,
        "kast": 38.889, "opening_duel_attempts": 3, "opening_duel_wins": 0,
        "opening_duel_losses": 3, "opening_duel_win_rate": 0.0,
        "multi_kill_rounds": 1, "trade_kills": 1, "traded_deaths": 1,
        "trade_success_rate": 0.016, "he_detonations": 3, "smoke_detonations": 4,
        "flash_detonations": 0, "fire_grenade_detonations": 6, "enemy_he_damage": 0,
        "enemy_fire_damage": 0, "effective_enemy_utility_damage": 0,
        "utility_damage_per_round": 0.0, "enemies_effectively_flashed": 0,
        "effective_enemy_flash_duration": 0, "smokes_used": 4, "accepted_shots": 70,
        "accepted_hits": 17, "shot_accuracy": 24.286, "head_hits": 3,
        "hit_based_headshot_rate": 17.647, "first_shots": 17, "first_shot_hits": 3,
        "first_bullet_accuracy": 17.647, "engagements_with_kill": 3,
        "first_shot_to_kill_ms": 265.667, "first_damage_to_kill_ms": 166.667,
    },
    117: {
        "rounds_played": 18, "kills": 15, "deaths": 10, "kd_ratio": 1.5,
        "kills_per_round": 0.833, "ordinary_assists": 4, "flash_assists": 1,
        "combined_assists": 5, "headshot_kills": 7, "headshot_kill_rate": 46.667,
        "survival_rate": 0.444, "effective_enemy_damage": 1611, "adr": 89.5,
        "kast": 72.222, "opening_duel_attempts": 4, "opening_duel_wins": 3,
        "opening_duel_losses": 1, "opening_duel_win_rate": 0.75,
        "multi_kill_rounds": 5, "trade_kills": 1, "traded_deaths": 2,
        "trade_success_rate": 0.022, "he_detonations": 3, "smoke_detonations": 5,
        "flash_detonations": 9, "fire_grenade_detonations": 8, "enemy_he_damage": 54,
        "enemy_fire_damage": 83, "effective_enemy_utility_damage": 137,
        "utility_damage_per_round": 7.611, "enemies_effectively_flashed": 9,
        "effective_enemy_flash_duration": 22.845, "smokes_used": 5,
        "accepted_shots": 214, "accepted_hits": 47, "shot_accuracy": 21.963,
        "head_hits": 11, "hit_based_headshot_rate": 23.404, "first_shots": 32,
        "first_shot_hits": 10, "first_bullet_accuracy": 31.25,
        "engagements_with_kill": 14, "first_shot_to_kill_ms": 720.0,
        "first_damage_to_kill_ms": 486.786,
    },
    120: {
        "rounds_played": 30, "kills": 15, "deaths": 25, "kd_ratio": 0.6,
        "kills_per_round": 0.5, "ordinary_assists": 8, "flash_assists": 0,
        "combined_assists": 8, "headshot_kills": 9, "headshot_kill_rate": 60.0,
        "survival_rate": 0.167, "effective_enemy_damage": 2007, "adr": 66.9,
        "kast": 63.333, "opening_duel_attempts": 6, "opening_duel_wins": 4,
        "opening_duel_losses": 2, "opening_duel_win_rate": 0.667,
        "multi_kill_rounds": 4, "trade_kills": 5, "traded_deaths": 4,
        "trade_success_rate": 0.059, "he_detonations": 3, "smoke_detonations": 13,
        "flash_detonations": 13, "fire_grenade_detonations": 6, "enemy_he_damage": 26,
        "enemy_fire_damage": 47, "effective_enemy_utility_damage": 73,
        "utility_damage_per_round": 2.433, "enemies_effectively_flashed": 11,
        "effective_enemy_flash_duration": 25.474, "smokes_used": 13,
        "accepted_shots": 364, "accepted_hits": 81, "shot_accuracy": 22.253,
        "head_hits": 11, "hit_based_headshot_rate": 13.58, "first_shots": 52,
        "first_shot_hits": 18, "first_bullet_accuracy": 34.615,
        "engagements_with_kill": 14, "first_shot_to_kill_ms": 814.857,
        "first_damage_to_kill_ms": 466.643,
    },
    122: {
        "rounds_played": 13, "kills": 15, "deaths": 7, "kd_ratio": 2.143,
        "kills_per_round": 1.154, "ordinary_assists": 5, "flash_assists": 0,
        "combined_assists": 5, "headshot_kills": 8, "headshot_kill_rate": 53.333,
        "survival_rate": 0.462, "effective_enemy_damage": 1490, "adr": 114.615,
        "kast": 84.615, "opening_duel_attempts": 3, "opening_duel_wins": 2,
        "opening_duel_losses": 1, "opening_duel_win_rate": 0.667,
        "multi_kill_rounds": 4, "trade_kills": 2, "traded_deaths": 1,
        "trade_success_rate": 0.053, "he_detonations": 2, "smoke_detonations": 7,
        "flash_detonations": 1, "fire_grenade_detonations": 2, "enemy_he_damage": 61,
        "enemy_fire_damage": 0, "effective_enemy_utility_damage": 61,
        "utility_damage_per_round": 4.692, "enemies_effectively_flashed": 2,
        "effective_enemy_flash_duration": 5.39, "smokes_used": 7,
        "accepted_shots": 180, "accepted_hits": 42, "shot_accuracy": 23.333,
        "head_hits": 9, "hit_based_headshot_rate": 21.429, "first_shots": 27,
        "first_shot_hits": 9, "first_bullet_accuracy": 33.333,
        "engagements_with_kill": 13, "first_shot_to_kill_ms": 483.077,
        "first_damage_to_kill_ms": 186.231,
    },
    124: {
        "rounds_played": 20, "kills": 16, "deaths": 10, "kd_ratio": 1.6,
        "kills_per_round": 0.8, "ordinary_assists": 3, "flash_assists": 1,
        "combined_assists": 4, "headshot_kills": 10, "headshot_kill_rate": 62.5,
        "survival_rate": 0.5, "effective_enemy_damage": 1643, "adr": 82.15,
        "kast": 70.0, "opening_duel_attempts": 2, "opening_duel_wins": 1,
        "opening_duel_losses": 1, "opening_duel_win_rate": 0.5,
        "multi_kill_rounds": 5, "trade_kills": 3, "traded_deaths": 1,
        "trade_success_rate": 0.057, "he_detonations": 5, "smoke_detonations": 11,
        "flash_detonations": 8, "fire_grenade_detonations": 5, "enemy_he_damage": 144,
        "enemy_fire_damage": 0, "effective_enemy_utility_damage": 144,
        "utility_damage_per_round": 7.2, "enemies_effectively_flashed": 16,
        "effective_enemy_flash_duration": 30.099, "smokes_used": 11,
        "accepted_shots": 237, "accepted_hits": 57, "shot_accuracy": 24.051,
        "head_hits": 12, "hit_based_headshot_rate": 21.053, "first_shots": 32,
        "first_shot_hits": 13, "first_bullet_accuracy": 40.625,
        "engagements_with_kill": 14, "first_shot_to_kill_ms": 526.857,
        "first_damage_to_kill_ms": 399.571,
    },
}


def main() -> None:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    fixtures = []
    for match_id, (relative_path, demo_sha1, map_name, coverage) in DEMOS.items():
        evidence = parse_coach_metric_evidence(
            ROOT / relative_path,
            match_id=match_id,
            owner_steamid=OWNER,
            demo_sha1=demo_sha1,
            map_name=map_name,
        )
        encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        checksum = hashlib.sha256(encoded).hexdigest()
        fixture_path = FIXTURE_ROOT / f"match_{match_id}.json"
        fixture_path.write_bytes(encoded + b"\n")
        fixtures.append(
            {
                "match_id": match_id,
                "fixture": str(fixture_path.relative_to(ROOT)),
                "demo_sha1": demo_sha1,
                "parser": evidence["parser"],
                "payload_version": evidence["payload_version"],
                "event_set_hash": checksum,
                "owner_steamid": OWNER,
                "accepted_rounds": len(evidence["phase"]["rounds"]),
                "ledger_checksum": checksum,
                "expected_metrics": EXPECTED[match_id],
                "unavailable_keys": [],
                "independent_evidence_method": "audited_low_level_event_ledger",
                "coverage": coverage,
            }
        )
    document = {
        "schema_version": "coach-metric-real-demo-corpus-v1",
        "semantic_version": "3.0.0",
        "fixtures": fixtures,
    }
    MANIFEST.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
