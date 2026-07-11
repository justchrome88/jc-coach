"""Canonical Coach Metric Pack computation and persistence."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import MetricSnapshot
from app.services.metrics.snapshots import deterministic_input_hash, upsert_metric_snapshot
from app.services.shared.weapon_names import canonical_weapon_name

COACH_METRIC_PACK_VERSION = "coach-metric-pack-v1"
COACH_METRIC_SEMANTIC_VERSION = "3.0.0"
COACH_METRIC_EVENT_SCHEMA_VERSION = "coach-metric-events-v1"
COACH_METRIC_PARSER_PAYLOAD_VERSION = "2026-07-11.coach-metric-v1"
COACH_METRIC_IMPLEMENTATION_VERSION = "coach-metric-pack-v1.0.0"
PERFORMANCE_SOURCE = "coach_metric_performance"
UTILITY_SOURCE = "coach_metric_utility"
AIM_SOURCE = "coach_metric_aim"
TRADE_WINDOW_TICKS = 5 * 64
ENGAGEMENT_GAP_TICKS = 80
SHOT_HIT_WINDOW_TICKS = 8

UTILITY_HE_WEAPONS = {"hegrenade"}
UTILITY_FIRE_WEAPONS = {"inferno", "incgrenade", "molotov", "firebomb"}
UTILITY_WEAPONS = {*UTILITY_HE_WEAPONS, *UTILITY_FIRE_WEAPONS, "flashbang", "smokegrenade", "decoy"}
NON_BULLET_WEAPONS = {*UTILITY_WEAPONS, "knife", "knife_t", "c4", "world", "unknown"}


@dataclass(frozen=True)
class CoachMetricPackResult:
    player_key: str
    player_name: str | None
    player_steamid: str
    event_set_id: str
    input_event_hash: str
    performance: dict[str, Any]
    utility: dict[str, Any]
    aim: dict[str, Any]
    confidence: dict[str, Any]
    metadata: dict[str, Any]
    caveats: tuple[str, ...]

    @property
    def metrics(self) -> dict[str, Any]:
        return {**self.performance, **self.utility, **self.aim}


def parse_coach_metric_evidence(
    demo_path: Path,
    *,
    match_id: int,
    owner_steamid: str,
    demo_sha1: str | None = None,
    map_name: str | None = None,
) -> dict[str, Any]:
    """Read a retained demo into the compact, append-only Coach Metric Pack ledger."""
    from demoparser2 import DemoParser

    path = demo_path.resolve()
    actual_sha1 = _sha1_file(path)
    if demo_sha1 and actual_sha1 != demo_sha1:
        raise ValueError(f"retained demo SHA-1 mismatch for match {match_id}")
    parser = DemoParser(str(path))
    player_props = ["team_num", "is_alive", "is_connected", "health", "active_weapon_name"]
    other_props = ["is_warmup_period", "total_rounds_played", "is_match_started", "game_phase"]

    def event(name: str) -> list[dict[str, Any]]:
        try:
            return _records(parser.parse_event(name, player=player_props, other=other_props))
        except Exception:
            return []

    event_names = (
        "begin_new_match",
        "round_start",
        "round_end",
        "player_spawn",
        "player_disconnect",
        "player_connect",
        "player_team",
        "player_death",
        "player_hurt",
        "weapon_fire",
        "player_blind",
        "hegrenade_detonate",
        "smokegrenade_detonate",
        "flashbang_detonate",
        "decoy_detonate",
        "molotov_detonate",
        "inferno_startburn",
    )
    raw = {name: event(name) for name in event_names}
    player_info = _records(parser.parse_player_info())
    parser_version = _parser_version()

    rounds = _accepted_rounds(raw["round_start"], raw["round_end"])
    accepted_round_numbers = {row["round_number"] for row in rounds}
    final_tick = max((row["end_tick"] for row in rounds), default=None)

    deaths = [
        _death_row(row)
        for row in raw["player_death"]
        if _accept_event(row, accepted_round_numbers, final_tick)
    ]
    hurts = [
        _hurt_row(row)
        for row in raw["player_hurt"]
        if _accept_event(row, accepted_round_numbers, final_tick)
    ]
    shots = [
        _shot_row(row)
        for row in raw["weapon_fire"]
        if _accept_event(row, accepted_round_numbers, final_tick)
        and _steam(row.get("user_steamid")) == owner_steamid
    ]
    blinds = [
        _blind_row(row)
        for row in raw["player_blind"]
        if _accept_event(row, accepted_round_numbers, final_tick)
        and _steam(row.get("attacker_steamid")) == owner_steamid
    ]
    detonations = []
    for name in event_names:
        if name not in {
            "hegrenade_detonate",
            "smokegrenade_detonate",
            "flashbang_detonate",
            "decoy_detonate",
            "molotov_detonate",
            "inferno_startburn",
        }:
            continue
        detonations.extend(
            _detonation_row(name, row)
            for row in raw[name]
            if _accept_event(row, accepted_round_numbers, final_tick)
            and _steam(row.get("user_steamid")) == owner_steamid
        )

    owner_spawns = [
        _presence_row("spawn", row)
        for row in raw["player_spawn"]
        if _steam(row.get("user_steamid")) == owner_steamid
    ]
    owner_disconnects = [
        _presence_row("disconnect", row)
        for row in raw["player_disconnect"]
        if _steam(row.get("user_steamid")) == owner_steamid
    ]
    owner_connects = [
        _presence_row("connect", row)
        for row in raw["player_connect"]
        if _steam(row.get("user_steamid")) == owner_steamid
    ]
    owner_team_events = [
        _presence_row("team", row)
        for row in raw["player_team"]
        if _steam(row.get("user_steamid")) == owner_steamid
    ]
    roster = sorted(
        {
            steam
            for row in player_info
            for steam in [_steam(row.get("steamid") or row.get("player_steamid"))]
            if steam
        }
    )
    owner_name = _owner_name(owner_steamid, player_info, deaths, hurts, shots)
    evidence = {
        "schema_version": COACH_METRIC_EVENT_SCHEMA_VERSION,
        "payload_version": COACH_METRIC_PARSER_PAYLOAD_VERSION,
        "parser": {"name": "demoparser2", "version": parser_version},
        "identity": {
            "match_id": match_id,
            "demo_sha1": actual_sha1,
            "owner_steamid": owner_steamid,
            "owner_name": owner_name,
            "map_name": map_name,
        },
        "phase": {
            "classification": "completed_regulation_and_overtime",
            "rounds": rounds,
            "final_round_end_tick": final_tick,
            "incomplete_round_starts": _incomplete_round_starts(raw["round_start"], rounds),
        },
        "participation": {
            "roster_steamids": roster,
            "owner_spawns": owner_spawns,
            "owner_disconnects": owner_disconnects,
            "owner_connects": owner_connects,
            "owner_team_events": owner_team_events,
        },
        "events": {
            "deaths": deaths,
            "hurts": hurts,
            "shots": shots,
            "blinds": blinds,
            "detonations": detonations,
        },
    }
    return json.loads(json.dumps(evidence, ensure_ascii=False, sort_keys=True, default=_json_default))


def calculate_coach_metric_pack(evidence: Mapping[str, Any]) -> CoachMetricPackResult:
    identity = _mapping(evidence.get("identity"))
    owner = str(identity.get("owner_steamid") or "").strip()
    if not owner:
        raise ValueError("coach metric evidence requires owner_steamid")
    phase = _mapping(evidence.get("phase"))
    rounds = [dict(row) for row in _sequence(phase.get("rounds")) if isinstance(row, Mapping)]
    if not rounds:
        raise ValueError("coach metric evidence has no completed rounds")
    events = _mapping(evidence.get("events"))
    deaths = [dict(row) for row in _sequence(events.get("deaths")) if isinstance(row, Mapping)]
    hurts = [dict(row) for row in _sequence(events.get("hurts")) if isinstance(row, Mapping)]
    shots = [dict(row) for row in _sequence(events.get("shots")) if isinstance(row, Mapping)]
    blinds = [dict(row) for row in _sequence(events.get("blinds")) if isinstance(row, Mapping)]
    detonations = [dict(row) for row in _sequence(events.get("detonations")) if isinstance(row, Mapping)]

    participation, participation_complete, participation_reasons = _participation_ledger(evidence, owner, rounds)
    if not participation_complete:
        raise ValueError("owner participation evidence is incomplete")
    side_by_round = {row["round_number"]: row["side"] for row in participation}
    accepted_rounds = {row["round_number"] for row in participation if row["participated"]}

    deaths = [row for row in deaths if row.get("round_number") in accepted_rounds]
    hurts = [row for row in hurts if row.get("round_number") in accepted_rounds]
    shots = [row for row in shots if row.get("round_number") in accepted_rounds]
    blinds = [row for row in blinds if row.get("round_number") in accepted_rounds]
    detonations = [row for row in detonations if row.get("round_number") in accepted_rounds]

    damage_ledger = _effective_damage_ledger(hurts)
    enemy_damage = [row for row in damage_ledger if row["attacker_steamid"] == owner and row["relation"] == "enemy"]
    owner_deaths = [row for row in deaths if row["victim_steamid"] == owner]
    owner_kills = [row for row in deaths if row["attacker_steamid"] == owner and _death_relation(row) == "enemy"]
    owner_assists = [
        row
        for row in deaths
        if row.get("assister_steamid") == owner and _death_relation(row, assister=True) == "enemy"
    ]
    flash_assists = [row for row in owner_assists if row.get("assistedflash") is True]
    ordinary_assists = [row for row in owner_assists if row.get("assistedflash") is not True]

    opening = _opening_duel_ledger(deaths)
    owner_opening_wins = [row for row in opening if row["attacker_steamid"] == owner]
    owner_opening_losses = [row for row in opening if row["victim_steamid"] == owner]
    trade = _trade_ledger(deaths, owner, side_by_round)
    trade_kills = [row for row in trade["trade_kills"]]
    traded_deaths = [row for row in trade["owner_deaths"] if row["traded"]]
    untraded_deaths = [row for row in trade["owner_deaths"] if not row["traded"]]

    kills_by_round = Counter(int(row["round_number"]) for row in owner_kills)
    multi_kill_buckets = {
        "multi_kill_2_rounds": sum(1 for value in kills_by_round.values() if value == 2),
        "multi_kill_3_rounds": sum(1 for value in kills_by_round.values() if value == 3),
        "multi_kill_4_rounds": sum(1 for value in kills_by_round.values() if value == 4),
        "multi_kill_5_plus_rounds": sum(1 for value in kills_by_round.values() if value >= 5),
    }
    multi_kill_rounds = sum(multi_kill_buckets.values())

    killed_rounds = {int(row["round_number"]) for row in owner_kills}
    assisted_rounds = {int(row["round_number"]) for row in owner_assists}
    died_rounds = {int(row["round_number"]) for row in owner_deaths}
    traded_rounds = {int(row["round_number"]) for row in traded_deaths}
    kast_ledger = []
    for round_number in sorted(accepted_rounds):
        killed = round_number in killed_rounds
        assisted = round_number in assisted_rounds
        survived = round_number not in died_rounds
        traded_death = round_number in traded_rounds
        kast_ledger.append(
            {
                "round_number": round_number,
                "kill": killed,
                "assist": assisted,
                "survive": survived,
                "trade": traded_death,
                "kast": killed or assisted or survived or traded_death,
            }
        )

    rounds_played = len(accepted_rounds)
    kills = len(owner_kills)
    deaths_count = len(owner_deaths)
    headshot_kills = sum(1 for row in owner_kills if row.get("headshot") is True)
    effective_enemy_damage = sum(int(row["effective_damage"]) for row in enemy_damage)
    survived_rounds = rounds_played - len(died_rounds)
    opening_wins = len(owner_opening_wins)
    opening_losses = len(owner_opening_losses)
    opening_attempts = opening_wins + opening_losses
    performance = {
        "rounds_played": rounds_played,
        "kills": kills,
        "deaths": deaths_count,
        "kd_ratio": round(kills / deaths_count, 3) if deaths_count else None,
        "kills_per_round": round(kills / rounds_played, 3),
        "ordinary_assists": len(ordinary_assists),
        "flash_assists": len(flash_assists),
        "combined_assists": len(owner_assists),
        "headshot_kills": headshot_kills,
        "headshot_kill_rate": round(headshot_kills / kills * 100, 3) if kills else None,
        "survived_rounds": survived_rounds,
        "survival_rate": round(survived_rounds / rounds_played, 3),
        "effective_enemy_damage": effective_enemy_damage,
        "adr": round(effective_enemy_damage / rounds_played, 3),
        "kast": round(sum(row["kast"] for row in kast_ledger) / rounds_played * 100, 3),
        "opening_duel_attempts": opening_attempts,
        "opening_duel_wins": opening_wins,
        "opening_duel_losses": opening_losses,
        "opening_duel_win_rate": round(opening_wins / opening_attempts, 3) if opening_attempts else None,
        "opening_deaths": opening_losses,
        "opening_death_rate": round(opening_losses / rounds_played, 3),
        "multi_kill_rounds": multi_kill_rounds,
        **multi_kill_buckets,
        "trade_opportunities": len(trade["opportunities"]),
        "trade_kills": len(trade_kills),
        "traded_deaths": len(traded_deaths),
        "untraded_deaths": len(untraded_deaths),
        "trade_status_known_deaths": len(trade["owner_deaths"]),
        "trade_success_rate": (
            round(len(trade_kills) / len(trade["opportunities"]), 3) if trade["opportunities"] else None
        ),
        "traded_death_rate": round(len(traded_deaths) / deaths_count, 3) if deaths_count else None,
        "untraded_death_rate": round(len(untraded_deaths) / deaths_count, 3) if deaths_count else None,
    }

    utility_damage = [row for row in enemy_damage if row["damage_class"] in {"he", "fire"}]
    enemy_he_damage = sum(int(row["effective_damage"]) for row in utility_damage if row["damage_class"] == "he")
    enemy_fire_damage = sum(int(row["effective_damage"]) for row in utility_damage if row["damage_class"] == "fire")
    effective_utility = enemy_he_damage + enemy_fire_damage
    enemy_blinds = [
        row
        for row in blinds
        if _relation_from_teams(row.get("attacker_team"), row.get("victim_team")) == "enemy"
    ]
    round_end_ticks = {int(row["round_number"]): int(row["end_tick"]) for row in rounds}
    effective_flash_duration = sum(
        min(
            max(float(row.get("blind_duration") or 0.0), 0.0),
            max((round_end_ticks[int(row["round_number"])] - int(row["tick"])) / 64.0, 0.0),
        )
        for row in enemy_blinds
    )
    detonation_counts = Counter(row["utility_type"] for row in _dedupe_detonations(detonations))
    utility = {
        "he_detonations": detonation_counts["he"],
        "smoke_detonations": detonation_counts["smoke"],
        "flash_detonations": detonation_counts["flash"],
        "fire_grenade_detonations": detonation_counts["fire"],
        "enemy_he_damage": enemy_he_damage,
        "enemy_fire_damage": enemy_fire_damage,
        "effective_enemy_utility_damage": effective_utility,
        "utility_damage_per_round": round(effective_utility / rounds_played, 3),
        "enemies_effectively_flashed": len(enemy_blinds),
        "effective_enemy_flash_duration": round(effective_flash_duration, 3),
        "smokes_used": detonation_counts["smoke"],
    }

    aim = _aim_metrics(owner, shots, damage_ledger, deaths, rounds)
    engagement_ledger = aim.pop("_engagement_ledger")
    weapon_class_dimensions = aim.pop("_weapon_class_dimensions")
    event_set_hash = deterministic_input_hash(evidence)
    event_set_id = f"coach-metric-events:{COACH_METRIC_EVENT_SCHEMA_VERSION}:{event_set_hash}"
    metric_keys = sorted({*performance, *utility, *aim})
    unavailable = sorted(key for key in metric_keys if performance.get(key, utility.get(key, aim.get(key))) is None)
    confidence = {
        "confidence": "high",
        "metrics": {
            key: {
                "level": "high" if key not in unavailable else "unavailable",
                "usable_for_insights": key not in unavailable,
                "usable_for_missions": key not in unavailable,
                "hard_recommendation_eligible": key not in unavailable,
                "reason_codes": (
                    ["coach_metric_pack_v1_validated_evidence"]
                    if key not in unavailable
                    else ["zero_denominator"]
                ),
            }
            for key in metric_keys
        },
    }
    side_dimensions = _side_dimensions(
        side_by_round,
        performance=performance,
        owner_kills=owner_kills,
        owner_deaths=owner_deaths,
        enemy_damage=enemy_damage,
        utility_damage=utility_damage,
    )
    metadata = {
        "schema_version": COACH_METRIC_PACK_VERSION,
        "contract_version": COACH_METRIC_SEMANTIC_VERSION,
        "event_schema_version": COACH_METRIC_EVENT_SCHEMA_VERSION,
        "accepted_phase": {
            "round_numbers": sorted(accepted_rounds),
            "final_round_end_tick": phase.get("final_round_end_tick"),
            "classification": phase.get("classification"),
            "overtime": rounds_played > 24,
            "incomplete_round_starts": list(_sequence(phase.get("incomplete_round_starts"))),
        },
        "participation": {
            "complete": participation_complete,
            "reason_codes": participation_reasons,
            "ledger": participation,
        },
        "damage_ledger": damage_ledger,
        "kast_round_ledger": kast_ledger,
        "opening_duel_ledger": opening,
        "trade_ledger": trade,
        "engagement_ledger": engagement_ledger,
        "multi_kill_buckets": multi_kill_buckets,
        "dimensions": {
            "map": identity.get("map_name"),
            "side": side_dimensions,
            "weapon_class": weapon_class_dimensions,
            "aggregation_strategy": "store player-match primitives; derive rolling/map/side/weapon views at query time",
        },
        "unavailable_metrics": unavailable,
        "metric_validation": {
            key: {
                "status": "validated" if key not in unavailable else "quarantined",
                "reason_codes": ["coach_metric_pack_v1_ground_truth_contract"]
                if key not in unavailable
                else ["zero_denominator"],
            }
            for key in metric_keys
        },
        "event_count": sum(len(value) for value in (deaths, hurts, shots, blinds, detonations)),
        "source_evidence": {
            "demo_sha1": identity.get("demo_sha1"),
            "parser": evidence.get("parser"),
            "payload_version": evidence.get("payload_version"),
            "event_set_id": event_set_id,
        },
    }
    return CoachMetricPackResult(
        player_key=f"steam:{owner}",
        player_name=str(identity.get("owner_name")) if identity.get("owner_name") else None,
        player_steamid=owner,
        event_set_id=event_set_id,
        input_event_hash=event_set_hash,
        performance=performance,
        utility=utility,
        aim=aim,
        confidence=confidence,
        metadata=metadata,
        caveats=(
            "Aim primitives use local shot/hurt/death timing contracts and do not claim formula identity "
            "with external products.",
            "Trade opportunity is a deterministic same-round teammate-death lineage, not a positioning claim.",
        ),
    )


def store_coach_metric_pack(
    db: Session,
    *,
    match_id: int,
    owner_user_id: int,
    source_parser_artifact_id: int,
    result: CoachMetricPackResult,
    artifact_path: Path | None = None,
) -> list[MetricSnapshot]:
    snapshots = []
    domains = (
        (PERFORMANCE_SOURCE, "coach_performance", result.performance),
        (UTILITY_SOURCE, "coach_utility", result.utility),
        (AIM_SOURCE, "coach_aim", result.aim),
    )
    for source, domain, metrics in domains:
        keys = set(metrics)
        validation = {
            key: dict(record)
            for key, record in _mapping(result.metadata.get("metric_validation")).items()
            if key in keys and isinstance(record, Mapping)
        }
        confidence = {
            **result.confidence,
            "metrics": {
                key: dict(record)
                for key, record in _mapping(result.confidence.get("metrics")).items()
                if key in keys and isinstance(record, Mapping)
            },
        }
        metadata = {
            **result.metadata,
            "metric_validation": validation,
            "artifact_path": str(artifact_path) if artifact_path else None,
        }
        snapshots.append(
            upsert_metric_snapshot(
                db,
                owner_user_id=owner_user_id,
                match_id=match_id,
                player_key=result.player_key,
                player_name=result.player_name,
                player_steamid=result.player_steamid,
                source=source,
                metric_domain=domain,
                semantic_version=COACH_METRIC_SEMANTIC_VERSION,
                scope="player_match",
                validation_status="validated",
                implementation_version=COACH_METRIC_IMPLEMENTATION_VERSION,
                source_parser_artifact_id=source_parser_artifact_id,
                source_event_set_id=result.event_set_id,
                input_event_hash=deterministic_input_hash(metrics),
                metrics=metrics,
                confidence_baseline=confidence,
                caveats=result.caveats,
                metadata=metadata,
            )
        )
    return snapshots


def write_coach_metric_evidence_artifact(evidence: Mapping[str, Any], artifact_root: Path) -> Path:
    encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    event_hash = hashlib.sha256(encoded).hexdigest()
    demo_sha1 = str(_mapping(evidence.get("identity")).get("demo_sha1") or "unknown")
    target = artifact_root / demo_sha1[:2] / f"{event_hash}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != encoded:
            raise ValueError(f"coach metric event artifact collision: {target}")
        return target
    temporary = target.with_suffix(f".tmp-{os.getpid()}")
    temporary.write_bytes(encoded)
    os.replace(temporary, target)
    return target


def _accepted_rounds(starts: Sequence[Mapping[str, Any]], ends: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    start_by_round = {
        number: int(row["tick"])
        for row in starts
        for number in [_event_round_number(row)]
        if number is not None and _int(row.get("tick")) is not None and row.get("is_warmup_period") is not True
    }
    end_by_round = {}
    for row in ends:
        number = _round_end_number(row)
        tick = _int(row.get("tick"))
        if number is None or tick is None or row.get("is_warmup_period") is True:
            continue
        end_by_round[number] = {
            "end_tick": tick,
            "winner": _clean(row.get("winner")),
            "reason": _clean(row.get("reason")),
        }
    return [
        {
            "round_number": number,
            "start_tick": start_by_round[number],
            **end_by_round[number],
            "phase": "regulation" if number < 24 else "overtime",
        }
        for number in sorted(set(start_by_round) & set(end_by_round))
        if start_by_round[number] <= end_by_round[number]["end_tick"]
    ]


def _incomplete_round_starts(starts: Sequence[Mapping[str, Any]], rounds: Sequence[Mapping[str, Any]]) -> list[int]:
    completed = {int(row["round_number"]) for row in rounds}
    return sorted(
        {
            number
            for row in starts
            for number in [_event_round_number(row)]
            if number is not None and number not in completed and row.get("is_warmup_period") is not True
        }
    )


def _accept_event(row: Mapping[str, Any], rounds: set[int], final_tick: int | None) -> bool:
    number = _event_round_number(row)
    tick = _int(row.get("tick"))
    return (
        number in rounds
        and tick is not None
        and (final_tick is None or tick <= final_tick)
        and row.get("is_warmup_period") is not True
    )


def _death_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "round_number": _event_round_number(row),
        "tick": _int(row.get("tick")),
        "attacker_steamid": _steam(row.get("attacker_steamid")),
        "attacker_name": _clean(row.get("attacker_name")),
        "attacker_team": _int(row.get("attacker_team_num")),
        "victim_steamid": _steam(row.get("user_steamid")),
        "victim_name": _clean(row.get("user_name")),
        "victim_team": _int(row.get("user_team_num")),
        "assister_steamid": _steam(row.get("assister_steamid")),
        "assister_name": _clean(row.get("assister_name")),
        "assister_team": _int(row.get("assister_team_num")),
        "assistedflash": _bool(row.get("assistedflash")),
        "headshot": _bool(row.get("headshot")),
        "weapon": canonical_weapon_name(row.get("weapon")) or "unknown",
    }


def _hurt_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "round_number": _event_round_number(row),
        "tick": _int(row.get("tick")),
        "attacker_steamid": _steam(row.get("attacker_steamid")),
        "attacker_name": _clean(row.get("attacker_name")),
        "attacker_team": _int(row.get("attacker_team_num")),
        "victim_steamid": _steam(row.get("user_steamid")),
        "victim_name": _clean(row.get("user_name")),
        "victim_team": _int(row.get("user_team_num")),
        "damage_health": max(_int(row.get("dmg_health")) or 0, 0),
        "victim_health_after": max(_int(row.get("health")) or 0, 0),
        "hitgroup": _clean(row.get("hitgroup")),
        "weapon": canonical_weapon_name(row.get("weapon")) or "unknown",
    }


def _shot_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "round_number": _event_round_number(row),
        "tick": _int(row.get("tick")),
        "player_steamid": _steam(row.get("user_steamid")),
        "player_team": _int(row.get("user_team_num")),
        "weapon": canonical_weapon_name(row.get("weapon")) or "unknown",
    }


def _blind_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "round_number": _event_round_number(row),
        "tick": _int(row.get("tick")),
        "attacker_steamid": _steam(row.get("attacker_steamid")),
        "attacker_team": _int(row.get("attacker_team_num")),
        "victim_steamid": _steam(row.get("user_steamid")),
        "victim_team": _int(row.get("user_team_num")),
        "blind_duration": max(_float(row.get("blind_duration")) or 0.0, 0.0),
        "entity_id": _clean(row.get("entityid")),
    }


def _detonation_row(event_name: str, row: Mapping[str, Any]) -> dict[str, Any]:
    utility_type = {
        "hegrenade_detonate": "he",
        "smokegrenade_detonate": "smoke",
        "flashbang_detonate": "flash",
        "decoy_detonate": "decoy",
        "molotov_detonate": "fire",
        "inferno_startburn": "fire",
    }[event_name]
    return {
        "round_number": _event_round_number(row),
        "tick": _int(row.get("tick")),
        "owner_steamid": _steam(row.get("user_steamid")),
        "owner_team": _int(row.get("user_team_num")),
        "utility_type": utility_type,
        "entity_id": _clean(row.get("entityid")),
        "source_event": event_name,
    }


def _presence_row(kind: str, row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": kind,
        "round_number": _event_round_number(row),
        "tick": _int(row.get("tick")),
        "steamid": _steam(row.get("user_steamid")),
        "team": _int(row.get("user_team_num") or row.get("team")),
        "warmup": row.get("is_warmup_period") is True,
    }


def _participation_ledger(
    evidence: Mapping[str, Any], owner: str, rounds: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], bool, list[str]]:
    participation = _mapping(evidence.get("participation"))
    roster = {str(item) for item in _sequence(participation.get("roster_steamids"))}
    spawns = [dict(row) for row in _sequence(participation.get("owner_spawns")) if isinstance(row, Mapping)]
    disconnects = [
        dict(row) for row in _sequence(participation.get("owner_disconnects")) if isinstance(row, Mapping)
    ]
    team_events = [
        dict(row) for row in _sequence(participation.get("owner_team_events")) if isinstance(row, Mapping)
    ]
    event_rows = [
        dict(row)
        for group in _mapping(evidence.get("events")).values()
        if isinstance(group, Sequence) and not isinstance(group, (str, bytes))
        for row in group
        if isinstance(row, Mapping)
    ]
    roster_proven = owner in roster or bool(spawns) or any(
        owner in {row.get("attacker_steamid"), row.get("victim_steamid"), row.get("player_steamid")}
        for row in event_rows
    )
    ledger = []
    complete = roster_proven
    for round_row in rounds:
        number = int(round_row["round_number"])
        start = int(round_row["start_tick"])
        end = int(round_row["end_tick"])
        disconnected = any(start <= int(row.get("tick") or -1) <= end for row in disconnects)
        side_candidates = [
            _side(row.get("team"))
            for row in [*spawns, *team_events]
            if row.get("round_number") == number and _side(row.get("team"))
        ]
        if not side_candidates:
            side_candidates = [
                _side(team)
                for row in event_rows
                if row.get("round_number") == number
                for steam, team in (
                    (row.get("attacker_steamid"), row.get("attacker_team")),
                    (row.get("victim_steamid"), row.get("victim_team")),
                    (row.get("player_steamid"), row.get("player_team")),
                    (row.get("owner_steamid"), row.get("owner_team")),
                )
                if steam == owner and _side(team)
            ]
        side = side_candidates[0] if side_candidates else None
        if disconnected or side is None:
            complete = False
        ledger.append(
            {
                "round_number": number,
                "participated": roster_proven and not disconnected,
                "side": side,
                "roster_proven": roster_proven,
                "disconnect_during_round": disconnected,
            }
        )
    reasons = ["roster_or_spawn_membership", "completed_round_boundaries", "quiet_rounds_retained"]
    if any(row["disconnect_during_round"] for row in ledger):
        reasons.append("disconnect_during_accepted_round")
    if any(row["side"] is None for row in ledger):
        reasons.append("round_side_unavailable")
    return ledger, complete, reasons


def _effective_damage_ledger(hurts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    remaining: dict[tuple[int, str], int] = {}
    ledger = []
    for row in sorted(hurts, key=lambda item: (int(item.get("round_number") or -1), int(item.get("tick") or -1))):
        victim = str(row.get("victim_steamid") or "")
        round_number = int(row["round_number"])
        key = (round_number, victim)
        before = remaining.get(key, 100)
        raw = max(int(row.get("damage_health") or 0), 0)
        effective = min(raw, max(before, 0))
        reported_after = max(int(row.get("victim_health_after") or 0), 0)
        calculated_after = max(before - effective, 0)
        remaining[key] = min(reported_after, calculated_after) if raw else reported_after
        relation = _relation_from_teams(row.get("attacker_team"), row.get("victim_team"))
        if row.get("attacker_steamid") == row.get("victim_steamid") and row.get("attacker_steamid"):
            relation = "self"
        if not row.get("attacker_steamid"):
            relation = "world"
        weapon = canonical_weapon_name(row.get("weapon")) or "unknown"
        ledger.append(
            {
                **dict(row),
                "raw_attempted_damage": raw,
                "effective_damage": effective,
                "victim_health_before": before,
                "victim_health_after_accepted": remaining[key],
                "relation": relation,
                "damage_class": (
                    "he"
                    if weapon in UTILITY_HE_WEAPONS
                    else "fire"
                    if weapon in UTILITY_FIRE_WEAPONS
                    else "weapon"
                ),
                "weapon_class": _weapon_class(weapon),
            }
        )
    return ledger


def _opening_duel_ledger(deaths: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_round: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in deaths:
        if _death_relation(row) == "enemy":
            by_round[int(row["round_number"])].append(row)
    return [dict(min(rows, key=lambda row: int(row["tick"]))) for _, rows in sorted(by_round.items()) if rows]


def _trade_ledger(
    deaths: Sequence[Mapping[str, Any]], owner: str, side_by_round: Mapping[int, str | None]
) -> dict[str, Any]:
    ordered = sorted(deaths, key=lambda row: (int(row["round_number"]), int(row["tick"])))
    opportunities = []
    trade_kills = []
    owner_deaths = []
    for death in ordered:
        if _death_relation(death) != "enemy":
            continue
        round_number = int(death["round_number"])
        tick = int(death["tick"])
        attacker = death.get("attacker_steamid")
        victim = death.get("victim_steamid")
        victim_team = death.get("victim_team")
        if victim != owner and victim_team in {2, 3}:
            owner_team = next(
                (
                    team
                    for row in ordered
                    if row.get("round_number") == round_number
                    for steam, team in (
                        (row.get("attacker_steamid"), row.get("attacker_team")),
                        (row.get("victim_steamid"), row.get("victim_team")),
                    )
                    if steam == owner
                ),
                2 if side_by_round.get(round_number) == "T" else 3 if side_by_round.get(round_number) == "CT" else None,
            )
            if owner_team == victim_team:
                opportunity = {
                    "round_number": round_number,
                    "teammate_death_tick": tick,
                    "teammate_steamid": victim,
                    "enemy_steamid": attacker,
                    "window_ticks": TRADE_WINDOW_TICKS,
                }
                trade = next(
                    (
                        candidate
                        for candidate in ordered
                        if candidate.get("round_number") == round_number
                        and candidate.get("attacker_steamid") == owner
                        and candidate.get("victim_steamid") == attacker
                        and 0 < int(candidate["tick"]) - tick <= TRADE_WINDOW_TICKS
                    ),
                    None,
                )
                opportunity["converted"] = trade is not None
                if trade is not None:
                    opportunity["trade_tick"] = trade["tick"]
                    trade_kills.append({**dict(trade), "traded_teammate_steamid": victim})
                opportunities.append(opportunity)
        if victim == owner:
            trade = next(
                (
                    candidate
                    for candidate in ordered
                    if candidate.get("round_number") == round_number
                    and candidate.get("victim_steamid") == attacker
                    and candidate.get("attacker_team") == victim_team
                    and 0 < int(candidate["tick"]) - tick <= TRADE_WINDOW_TICKS
                ),
                None,
            )
            owner_deaths.append(
                {
                    "round_number": round_number,
                    "death_tick": tick,
                    "killer_steamid": attacker,
                    "traded": trade is not None,
                    "trade_tick": trade.get("tick") if trade else None,
                    "trade_actor_steamid": trade.get("attacker_steamid") if trade else None,
                    "window_ticks": TRADE_WINDOW_TICKS,
                }
            )
    return {
        "window_ticks": TRADE_WINDOW_TICKS,
        "opportunities": opportunities,
        "trade_kills": trade_kills,
        "owner_deaths": owner_deaths,
    }


def _aim_metrics(
    owner: str,
    shots: Sequence[Mapping[str, Any]],
    damage_ledger: Sequence[Mapping[str, Any]],
    deaths: Sequence[Mapping[str, Any]],
    rounds: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    accepted_shots = [
        row
        for row in shots
        if _weapon_class(row.get("weapon")) not in {"utility", "melee", "objective", "other"}
    ]
    hits = [
        row
        for row in damage_ledger
        if row.get("attacker_steamid") == owner
        and row.get("relation") == "enemy"
        and row.get("damage_class") == "weapon"
        and _weapon_class(row.get("weapon")) not in {"melee", "other"}
    ]
    owner_kills = [row for row in deaths if row.get("attacker_steamid") == owner and _death_relation(row) == "enemy"]
    round_ends = {int(row["round_number"]): int(row["end_tick"]) for row in rounds}
    utility_ticks = [
        (int(row["round_number"]), int(row["tick"]))
        for row in damage_ledger
        if row.get("attacker_steamid") == owner and row.get("damage_class") in {"he", "fire"}
    ]
    engagements = _engagement_ledger(
        accepted_shots,
        hits,
        owner_kills,
        deaths,
        round_ends,
        owner,
        utility_ticks,
    )
    killed_engagements = [row for row in engagements if row.get("kill_tick") is not None]
    first_shot_kill_times = [int(row["first_shot_to_kill_ms"]) for row in killed_engagements]
    first_damage_kill_times = [
        int(row["first_damage_to_kill_ms"])
        for row in killed_engagements
        if row.get("first_damage_to_kill_ms") is not None
    ]
    weapon_dimensions: dict[str, Counter[str]] = defaultdict(Counter)
    for row in accepted_shots:
        weapon_dimensions[_weapon_class(row.get("weapon"))]["shots"] += 1
    for row in hits:
        bucket = weapon_dimensions[_weapon_class(row.get("weapon"))]
        bucket["hits"] += 1
        if str(row.get("hitgroup") or "").lower() == "head":
            bucket["head_hits"] += 1
    for row in owner_kills:
        weapon_dimensions[_weapon_class(row.get("weapon"))]["kills"] += 1
    aim = {
        "accepted_shots": len(accepted_shots),
        "accepted_hits": len(hits),
        "shot_accuracy": round(len(hits) / len(accepted_shots) * 100, 3) if accepted_shots else None,
        "head_hits": sum(1 for row in hits if str(row.get("hitgroup") or "").lower() == "head"),
        "hit_based_headshot_rate": (
            round(sum(1 for row in hits if str(row.get("hitgroup") or "").lower() == "head") / len(hits) * 100, 3)
            if hits
            else None
        ),
        "first_shots": len(engagements),
        "first_shot_hits": sum(1 for row in engagements if row["first_shot_hit"]),
        "first_bullet_accuracy": (
            round(sum(1 for row in engagements if row["first_shot_hit"]) / len(engagements) * 100, 3)
            if engagements
            else None
        ),
        "engagements_with_kill": len(killed_engagements),
        "first_shot_to_kill_ms": (
            round(sum(first_shot_kill_times) / len(first_shot_kill_times), 3) if first_shot_kill_times else None
        ),
        "first_damage_to_kill_ms": (
            round(sum(first_damage_kill_times) / len(first_damage_kill_times), 3)
            if first_damage_kill_times
            else None
        ),
        "_engagement_ledger": engagements,
        "_weapon_class_dimensions": {key: dict(value) for key, value in sorted(weapon_dimensions.items())},
    }
    return aim


def _engagement_ledger(
    shots: Sequence[Mapping[str, Any]],
    hits: Sequence[Mapping[str, Any]],
    kills: Sequence[Mapping[str, Any]],
    deaths: Sequence[Mapping[str, Any]],
    round_ends: Mapping[int, int],
    owner: str,
    utility_ticks: Sequence[tuple[int, int]],
) -> list[dict[str, Any]]:
    ordered_shots = sorted(shots, key=lambda row: (int(row["round_number"]), int(row["tick"])))
    groups: list[list[Mapping[str, Any]]] = []
    for shot in ordered_shots:
        if not groups:
            groups.append([shot])
            continue
        prior = groups[-1][-1]
        intervening_owner_death = any(
            row.get("victim_steamid") == owner
            and row.get("round_number") == prior.get("round_number")
            and int(prior["tick"]) < int(row["tick"]) < int(shot["tick"])
            for row in deaths
        )
        intervening_kill = any(
            row.get("attacker_steamid") == owner
            and row.get("round_number") == prior.get("round_number")
            and int(prior["tick"]) < int(row["tick"]) < int(shot["tick"])
            for row in kills
        )
        intervening_utility = any(
            round_number == prior.get("round_number") and int(prior["tick"]) < tick <= int(shot["tick"])
            for round_number, tick in utility_ticks
        )
        if (
            shot.get("round_number") != prior.get("round_number")
            or shot.get("weapon") != prior.get("weapon")
            or int(shot["tick"]) - int(prior["tick"]) > ENGAGEMENT_GAP_TICKS
            or intervening_owner_death
            or intervening_kill
            or intervening_utility
        ):
            groups.append([shot])
        else:
            groups[-1].append(shot)
    ledger = []
    for index, group in enumerate(groups):
        first = group[0]
        number = int(first["round_number"])
        start = int(first["tick"])
        next_start = (
            int(groups[index + 1][0]["tick"])
            if index + 1 < len(groups) and groups[index + 1][0].get("round_number") == number
            else round_ends[number] + 1
        )
        end = min(next_start - 1, round_ends[number])
        engagement_hits = [
            row
            for row in hits
            if row.get("round_number") == number and start <= int(row["tick"]) <= end
        ]
        engagement_kills = [
            row
            for row in kills
            if row.get("round_number") == number and start <= int(row["tick"]) <= end
        ]
        kill = min(engagement_kills, key=lambda row: int(row["tick"])) if engagement_kills else None
        victim = kill.get("victim_steamid") if kill else None
        victim_hits = [row for row in engagement_hits if victim is None or row.get("victim_steamid") == victim]
        first_damage = min(victim_hits, key=lambda row: int(row["tick"])) if victim_hits else None
        second_tick = int(group[1]["tick"]) if len(group) > 1 else min(start + SHOT_HIT_WINDOW_TICKS + 1, end + 1)
        first_hit = any(
            start <= int(row["tick"]) < second_tick
            and int(row["tick"]) - start <= SHOT_HIT_WINDOW_TICKS
            for row in engagement_hits
        )
        ledger.append(
            {
                "round_number": number,
                "start_tick": start,
                "end_tick": int(kill["tick"]) if kill else end,
                "weapon": first.get("weapon"),
                "weapon_class": _weapon_class(first.get("weapon")),
                "shot_count": len(group),
                "hit_count": len(engagement_hits),
                "enemy_count": len({row.get("victim_steamid") for row in engagement_hits if row.get("victim_steamid")}),
                "first_shot_hit": first_hit,
                "kill_tick": int(kill["tick"]) if kill else None,
                "killed_victim_steamid": victim,
                "first_shot_to_kill_ms": round((int(kill["tick"]) - start) / 64 * 1000) if kill else None,
                "first_damage_to_kill_ms": (
                    round((int(kill["tick"]) - int(first_damage["tick"])) / 64 * 1000)
                    if kill and first_damage
                    else None
                ),
            }
        )
    return ledger


def _side_dimensions(
    side_by_round: Mapping[int, str | None],
    *,
    performance: Mapping[str, Any],
    owner_kills: Sequence[Mapping[str, Any]],
    owner_deaths: Sequence[Mapping[str, Any]],
    enemy_damage: Sequence[Mapping[str, Any]],
    utility_damage: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    output = {}
    for side in ("T", "CT"):
        rounds = {number for number, value in side_by_round.items() if value == side}
        damage = sum(int(row["effective_damage"]) for row in enemy_damage if row.get("round_number") in rounds)
        utility = sum(int(row["effective_damage"]) for row in utility_damage if row.get("round_number") in rounds)
        output[side] = {
            "sample_rounds": len(rounds),
            "kills": sum(1 for row in owner_kills if row.get("round_number") in rounds),
            "deaths": sum(1 for row in owner_deaths if row.get("round_number") in rounds),
            "effective_enemy_damage": damage,
            "adr": round(damage / len(rounds), 3) if rounds else None,
            "effective_enemy_utility_damage": utility,
        }
    return output


def _dedupe_detonations(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen = set()
    result = []
    for row in sorted(rows, key=lambda item: (int(item["round_number"]), int(item["tick"]))):
        key = (row.get("round_number"), row.get("utility_type"), row.get("entity_id") or row.get("tick"))
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _death_relation(row: Mapping[str, Any], *, assister: bool = False) -> str:
    actor_team = row.get("assister_team") if assister else row.get("attacker_team")
    actor_steam = row.get("assister_steamid") if assister else row.get("attacker_steamid")
    if not actor_steam:
        return "world"
    if actor_steam == row.get("victim_steamid"):
        return "self"
    return _relation_from_teams(actor_team, row.get("victim_team"))


def _relation_from_teams(actor_team: Any, victim_team: Any) -> str:
    actor = _int(actor_team)
    victim = _int(victim_team)
    if actor not in {2, 3} or victim not in {2, 3}:
        return "unclassified"
    return "team" if actor == victim else "enemy"


def _weapon_class(value: Any) -> str:
    weapon = canonical_weapon_name(value) or "unknown"
    if weapon in UTILITY_WEAPONS:
        return "utility"
    if weapon.startswith("knife") or weapon in {"bayonet", "taser"}:
        return "melee"
    if weapon in {"c4"}:
        return "objective"
    if weapon in {"ak47", "aug", "famas", "galilar", "m4a1", "m4a1_silencer", "sg556"}:
        return "rifle"
    if weapon in {"awp", "g3sg1", "scar20", "ssg08"}:
        return "sniper"
    if weapon in {"bizon", "mac10", "mp5sd", "mp7", "mp9", "p90", "ump45"}:
        return "smg"
    if weapon in {"mag7", "nova", "sawedoff", "xm1014"}:
        return "shotgun"
    if weapon in {"m249", "negev"}:
        return "heavy"
    if weapon in {
        "cz75a", "deagle", "elite", "fiveseven", "glock", "hkp2000", "p250", "revolver", "tec9", "usp_silencer"
    }:
        return "pistol"
    return "other"


def _event_round_number(row: Mapping[str, Any]) -> int | None:
    value = _int(row.get("total_rounds_played"))
    if value is not None:
        return value
    value = _int(row.get("round_number") or row.get("round"))
    return value - 1 if value and value > 0 else value


def _round_end_number(row: Mapping[str, Any]) -> int | None:
    value = _int(row.get("total_rounds_played"))
    if value is not None and value > 0:
        return value - 1
    value = _int(row.get("round"))
    return value - 1 if value and value > 0 else value


def _owner_name(
    owner: str,
    player_info: Sequence[Mapping[str, Any]],
    *event_sets: Sequence[Mapping[str, Any]],
) -> str | None:
    for row in player_info:
        if _steam(row.get("steamid") or row.get("player_steamid")) == owner:
            return _clean(row.get("name") or row.get("player_name"))
    for rows in event_sets:
        for row in rows:
            for steam_key, name_key in (
                ("attacker_steamid", "attacker_name"),
                ("victim_steamid", "victim_name"),
                ("player_steamid", "player_name"),
            ):
                if row.get(steam_key) == owner and row.get(name_key):
                    return str(row[name_key])
    return None


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        try:
            return [dict(row) for row in value.to_dict("records")]
        except TypeError:
            pass
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [dict(row) for row in value if isinstance(row, Mapping)]
    return []


def _parser_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("demoparser2")
    except Exception:
        return None


def _sha1_file(path: Path) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _side(value: Any) -> str | None:
    team = _int(value)
    return "T" if team == 2 else "CT" if team == 3 else None


def _steam(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    return None if not text or text.lower() in {"nan", "none", "0"} else text.removesuffix(".0")


def _clean(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def _int(value: Any) -> int | None:
    clean = _clean(value)
    try:
        return int(clean) if clean is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _float(value: Any) -> float | None:
    clean = _clean(value)
    try:
        return float(clean) if clean is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _bool(value: Any) -> bool | None:
    clean = _clean(value)
    if isinstance(clean, bool):
        return clean
    if clean in {0, 1}:
        return bool(clean)
    return None


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def _json_default(value: Any) -> Any:
    clean = _clean(value)
    if clean is not value:
        return clean
    raise TypeError(f"not JSON serializable: {type(value).__name__}")
