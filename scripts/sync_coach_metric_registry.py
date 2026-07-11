from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/metrics/registry/metrics.json"

SEMANTIC_VERSION = "3.0.0"
IMPLEMENTATION = "app/services/coach_metric_pack.py"

PACK: dict[str, tuple[str, str, str, str, str]] = {
    "rounds_played": ("Rounds played", "performance", "rounds", "integer", "completed participated rounds"),
    "kills": ("Kills", "performance", "events", "integer", "accepted enemy kills"),
    "deaths": ("Deaths", "performance", "events", "integer", "accepted owner deaths"),
    "kd_ratio": ("K/D", "performance", "ratio", "number", "kills / deaths; null at zero deaths"),
    "kills_per_round": ("Kills per round", "performance", "ratio", "number", "kills / rounds_played"),
    "ordinary_assists": ("Ordinary assists", "performance", "events", "integer", "accepted non-flash assists"),
    "flash_assists": ("Flash assists", "performance", "events", "integer", "accepted assistedflash assists"),
    "combined_assists": ("Combined assists", "performance", "events", "integer", "ordinary + flash assists"),
    "headshot_kills": ("Headshot kills", "performance", "events", "integer", "accepted headshot kills"),
    "headshot_kill_rate": (
        "Headshot-kill rate",
        "performance",
        "percent",
        "percentage",
        "headshot_kills / kills * 100",
    ),
    "survival_rate": (
        "Survival rate",
        "performance",
        "fraction",
        "number",
        "survived participated rounds / rounds_played",
    ),
    "survived_rounds": (
        "Survived rounds",
        "performance",
        "rounds",
        "integer",
        "participated rounds without accepted owner death",
    ),
    "effective_enemy_damage": (
        "Effective enemy damage",
        "performance",
        "health points",
        "integer",
        "enemy damage capped at remaining accepted victim health",
    ),
    "adr": ("ADR", "performance", "health points per round", "number", "effective_enemy_damage / rounds_played"),
    "kast": (
        "KAST",
        "performance",
        "percent",
        "percentage",
        "accepted rounds with K or A or S or T / rounds_played * 100",
    ),
    "opening_duel_attempts": (
        "Opening duel attempts",
        "performance",
        "events",
        "integer",
        "opening_duel_wins + opening_duel_losses",
    ),
    "opening_duel_wins": (
        "Opening duel wins",
        "performance",
        "events",
        "integer",
        "first accepted enemy kill in round by owner",
    ),
    "opening_duel_losses": (
        "Opening duel losses",
        "performance",
        "events",
        "integer",
        "first accepted enemy kill in round against owner",
    ),
    "opening_duel_win_rate": (
        "Opening duel win rate",
        "performance",
        "fraction",
        "number",
        "opening_duel_wins / opening_duel_attempts",
    ),
    "opening_deaths": (
        "Opening deaths",
        "performance",
        "events",
        "integer",
        "opening_duel_losses",
    ),
    "opening_death_rate": (
        "Opening death rate",
        "performance",
        "fraction",
        "number",
        "opening_deaths / rounds_played",
    ),
    "multi_kill_rounds": (
        "Multi-kill rounds",
        "performance",
        "rounds",
        "integer",
        "rounds with at least two accepted kills",
    ),
    "multi_kill_2_rounds": ("2K rounds", "performance", "rounds", "integer", "rounds with exactly two kills"),
    "multi_kill_3_rounds": ("3K rounds", "performance", "rounds", "integer", "rounds with exactly three kills"),
    "multi_kill_4_rounds": ("4K rounds", "performance", "rounds", "integer", "rounds with exactly four kills"),
    "multi_kill_5_plus_rounds": (
        "5K+ rounds",
        "performance",
        "rounds",
        "integer",
        "rounds with at least five kills",
    ),
    "trade_opportunities": (
        "Trade opportunities",
        "performance",
        "events",
        "integer",
        "same-round teammate deaths with explicit owner team lineage",
    ),
    "trade_kills": ("Trade kills", "performance", "events", "integer", "owner refrags inside five seconds"),
    "traded_deaths": (
        "Traded deaths",
        "performance",
        "events",
        "integer",
        "owner deaths refragged inside five seconds",
    ),
    "untraded_deaths": (
        "Untraded deaths",
        "performance",
        "events",
        "integer",
        "owner deaths not refragged inside five seconds",
    ),
    "trade_status_known_deaths": (
        "Deaths with known trade status",
        "performance",
        "events",
        "integer",
        "traded_deaths + untraded_deaths",
    ),
    "trade_success_rate": (
        "Trade success rate",
        "performance",
        "fraction",
        "number",
        "trade_kills / deterministic trade opportunities",
    ),
    "traded_death_rate": (
        "Traded-death rate",
        "performance",
        "fraction",
        "number",
        "traded_deaths / deaths",
    ),
    "untraded_death_rate": (
        "Untraded-death rate",
        "performance",
        "fraction",
        "number",
        "untraded_deaths / deaths",
    ),
    "he_detonations": ("HE detonations", "utility", "events", "integer", "accepted owned HE detonations"),
    "smoke_detonations": (
        "Smoke detonations",
        "utility",
        "events",
        "integer",
        "accepted owned smoke detonations",
    ),
    "flash_detonations": (
        "Flash detonations",
        "utility",
        "events",
        "integer",
        "accepted owned flash detonations",
    ),
    "fire_grenade_detonations": (
        "Fire grenade detonations",
        "utility",
        "events",
        "integer",
        "accepted owned fire-grenade entity starts",
    ),
    "enemy_he_damage": (
        "Enemy HE damage",
        "utility",
        "health points",
        "integer",
        "effective enemy health damage from owned HE",
    ),
    "enemy_fire_damage": (
        "Enemy fire damage",
        "utility",
        "health points",
        "integer",
        "effective enemy health damage from owned fire utility",
    ),
    "effective_enemy_utility_damage": (
        "Effective enemy utility damage",
        "utility",
        "health points",
        "integer",
        "enemy_he_damage + enemy_fire_damage",
    ),
    "utility_damage_per_round": (
        "Utility damage per round",
        "utility",
        "health points per round",
        "number",
        "effective_enemy_utility_damage / rounds_played",
    ),
    "enemies_effectively_flashed": (
        "Enemy flash effects",
        "utility",
        "events",
        "integer",
        "accepted enemy blind events caused by owner",
    ),
    "effective_enemy_flash_duration": (
        "Effective enemy flash duration",
        "utility",
        "seconds",
        "number",
        "enemy blind duration clipped to accepted round end",
    ),
    "smokes_used": ("Smokes used", "utility", "events", "integer", "accepted owned smoke detonations"),
    "accepted_shots": ("Accepted shots", "aim", "shots", "integer", "accepted firearm weapon_fire events"),
    "accepted_hits": ("Accepted hits", "aim", "hits", "integer", "accepted enemy firearm hurt events"),
    "shot_accuracy": ("Shot accuracy", "aim", "percent", "percentage", "accepted_hits / accepted_shots * 100"),
    "head_hits": ("Head hits", "aim", "hits", "integer", "accepted hits with hitgroup=head"),
    "hit_based_headshot_rate": (
        "Hit-based headshot rate",
        "aim",
        "percent",
        "percentage",
        "head_hits / accepted_hits * 100",
    ),
    "first_shots": ("First shots", "aim", "shots", "integer", "first shot of deterministic engagement"),
    "first_shot_hits": (
        "First-shot hits",
        "aim",
        "shots",
        "integer",
        "first shots with enemy hit before second shot",
    ),
    "first_bullet_accuracy": (
        "First-bullet accuracy",
        "aim",
        "percent",
        "percentage",
        "first_shot_hits / first_shots * 100",
    ),
    "engagements_with_kill": (
        "Engagements with kill",
        "aim",
        "engagements",
        "integer",
        "deterministic engagements ending in owner kill",
    ),
    "first_shot_to_kill_ms": (
        "First shot to kill",
        "aim",
        "milliseconds",
        "number",
        "mean first-shot-to-kill time for killed engagements",
    ),
    "first_damage_to_kill_ms": (
        "First damage to kill",
        "aim",
        "milliseconds",
        "number",
        "mean first-damage-to-kill time for killed engagements",
    ),
}


def _entry(key: str, spec: tuple[str, str, str, str, str], existing: dict[str, Any] | None) -> dict[str, Any]:
    display_name, domain, unit, value_type, formula = spec
    value = dict(existing or {})
    value.update(
        {
            "metric_key": key,
            "display_name": display_name,
            "domain": domain,
            "scope": "player_match",
            "unit": unit,
            "value_type": value_type,
            "source_kind": "coach_metric_event_ledger",
            "source_tables_or_events": [
                "retained demo",
                "coach-metric-events-v1",
                "metric_snapshots.metrics_json",
            ],
            "identity_keys": [
                "owner_user_id",
                "match_id",
                "player_steamid",
                "source_event_set_id",
                "semantic_version",
            ],
            "numerator_definition": formula,
            "denominator_definition": _denominator(key),
            "include_rules": ["completed regulation/overtime", "proven owner participation", "explicit team identity"],
            "exclude_rules": ["warmup", "incomplete round", "post-round", "post-match", "unclassified relation"],
            "rounding_storage": "integer when count; otherwise 3 decimals",
            "rounding_display": "metric-specific documented unit",
            "semantic_version": SEMANTIC_VERSION,
            "implementation_entrypoints": [IMPLEMENTATION],
            "persistence_targets": ["metric_snapshots.metrics_json"],
            "ui_consumers": ["trusted coach/API snapshot payload"],
            "coach_consumers": ["coach insights", "hypotheses", "missions", "progress evaluation"],
            "validation_rules": [
                "real-demo golden corpus",
                "independent low-level ledger checksum",
                "owner/player/version/provenance gate",
            ],
            "ground_truth_status": "verified",
            "status": "active",
            "last_verified_evidence": [
                "H01A-M04 five-demo golden corpus",
                "match 124 independently audited ledger",
            ],
            "known_discrepancies": [],
            "critical": True,
            "round_phase_boundary": (
                "accepted completed regulation/overtime rounds through inclusive final round-end tick; "
                "warmup/incomplete/post-match excluded"
            ),
            "classification": "validated_candidate",
            "validation_status": "validated",
            "consumer_policy": "trusted",
            "backfill_requirement": "append v3 snapshots from retained demos; preserve v1/v2 observations",
        }
    )
    return value


def _denominator(key: str) -> str | None:
    return {
        "kd_ratio": "deaths",
        "kills_per_round": "rounds_played",
        "headshot_kill_rate": "kills",
        "survival_rate": "rounds_played",
        "adr": "rounds_played",
        "kast": "rounds_played",
        "opening_duel_win_rate": "opening_duel_attempts",
        "opening_death_rate": "rounds_played",
        "trade_success_rate": "trade opportunities",
        "traded_death_rate": "deaths",
        "untraded_death_rate": "deaths",
        "utility_damage_per_round": "rounds_played",
        "shot_accuracy": "accepted_shots",
        "hit_based_headshot_rate": "accepted_hits",
        "first_bullet_accuracy": "first_shots",
    }.get(key)


def main() -> None:
    document = json.loads(REGISTRY.read_text(encoding="utf-8"))
    by_key = {item["metric_key"]: item for item in document["metrics"]}
    for invalid_legacy_key in ("2k_rounds", "3k_rounds", "4k_rounds", "5k_plus_rounds"):
        by_key.pop(invalid_legacy_key, None)
    for key, spec in PACK.items():
        by_key[key] = _entry(key, spec, by_key.get(key))
    document["registry_version"] = SEMANTIC_VERSION
    document["metrics"] = sorted(by_key.values(), key=lambda item: item["metric_key"])
    REGISTRY.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
