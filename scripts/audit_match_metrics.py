#!/usr/bin/env python3
"""Read-only deterministic metric ledger for a persisted parser artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def _load_artifact(db_path: Path, artifact_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT id, match_id, parser_name, parser_version, payload_version, demo_sha1, payload_json "
            "FROM demo_parse_artifacts WHERE id = ?",
            (artifact_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError(f"parser artifact {artifact_id} was not found")
    metadata = {key: row[key] for key in row.keys() if key != "payload_json"}
    return metadata, json.loads(row["payload_json"])


def _player_key(row: dict[str, Any], prefix: str) -> str | None:
    value = row.get(f"{prefix}_steamid")
    return str(value) if value and str(value) != "nan" else None


def _team_partition(duels: list[dict[str, Any]], owner_steamid: str) -> tuple[set[str], set[str]]:
    """Infer fixed rosters from enemy kill edges; fail if the graph is not bipartite."""
    graph: dict[str, set[str]] = defaultdict(set)
    for row in duels:
        attacker = _player_key(row, "attacker")
        victim = _player_key(row, "victim")
        if attacker and victim and attacker != victim:
            graph[attacker].add(victim)
            graph[victim].add(attacker)
    colors = {owner_steamid: 0}
    queue = deque([owner_steamid])
    while queue:
        player = queue.popleft()
        for opponent in graph[player]:
            expected = 1 - colors[player]
            if opponent in colors and colors[opponent] != expected:
                raise ValueError("kill graph is not bipartite; team damage or roster change requires manual review")
            if opponent not in colors:
                colors[opponent] = expected
                queue.append(opponent)
    if len(colors) != 10:
        raise ValueError(f"team inference reached {len(colors)} players instead of 10")
    owner_team = {player for player, color in colors.items() if color == 0}
    opponents = {player for player, color in colors.items() if color == 1}
    if len(owner_team) != 5 or len(opponents) != 5:
        raise ValueError("team inference did not produce a 5v5 roster")
    return owner_team, opponents


def build_ledger(payload: dict[str, Any], owner_steamid: str) -> dict[str, Any]:
    deep = payload["deep"]
    duels = deep["duels"]
    damage_events = deep["damage_events"]
    player_rounds = {
        int(row["round_number"]): row
        for row in deep["player_rounds"]
        if str(row.get("player_steamid")) == owner_steamid
    }
    owner_team, opponents = _team_partition(duels, owner_steamid)
    round_end_ticks = {
        int(row["round_number"]): row.get("end_tick") for row in deep["rounds"] if row.get("end_tick") is not None
    }
    final_round_end_tick = max(int(value) for value in round_end_ticks.values())
    ledger: dict[int, dict[str, Any]] = {}
    for round_number in range(21):
        status = "regulation" if round_number <= 19 else "post_match"
        ledger[round_number] = {
            "round_number": round_number,
            "round_classification": status,
            "player_participation": "event_observed" if round_number in player_rounds else "not_proven",
            "kills": 0,
            "deaths": 0,
            "assists": 0,
            "flash_assists": int(player_rounds.get(round_number, {}).get("flash_assists") or 0),
            "headshot_kills": 0,
            "enemy_damage_raw": 0,
            "enemy_damage_effective_reconstruction": 0,
            "team_damage_raw": 0,
            "self_world_damage_raw": 0,
            "utility_damage_raw": 0,
            "survived": None,
            "traded": None,
            "kast_contribution_without_trade": None,
            "first_kill_death_state": "none",
            "source_event_ids": [],
        }

    for index, row in enumerate(duels):
        round_number = int(row["round_number"])
        item = ledger.setdefault(round_number, {"round_number": round_number})
        attacker = _player_key(row, "attacker")
        victim = _player_key(row, "victim")
        assister = _player_key(row, "assister")
        post_match = int(row.get("tick") or 0) > final_round_end_tick
        if post_match:
            item["round_classification"] = "post_match"
        if attacker == owner_steamid and victim != owner_steamid:
            item["kills"] += 1
            item["headshot_kills"] += int(bool(row.get("headshot")))
            item["source_event_ids"].append(f"duel:{index}")
        if victim == owner_steamid:
            item["deaths"] += 1
            item["source_event_ids"].append(f"duel:{index}")
        if assister == owner_steamid:
            item["assists"] += 1
            item["source_event_ids"].append(f"duel:{index}")
        if row.get("opening_duel") and attacker == owner_steamid and victim != owner_steamid:
            item["first_kill_death_state"] = "first_kill"
        elif row.get("opening_duel") and victim == owner_steamid:
            item["first_kill_death_state"] = "first_death"

    health: dict[tuple[int, str], int] = {}
    damage_rows = sorted(
        enumerate(damage_events),
        key=lambda pair: (pair[1]["round_number"], pair[1].get("tick") or 0, pair[0]),
    )
    for index, row in damage_rows:
        round_number = int(row["round_number"])
        victim = _player_key(row, "victim")
        raw_damage = max(0, int(row.get("damage_health") or 0))
        key = (round_number, victim or "unknown")
        before = health.get(key, 100)
        effective_damage = min(raw_damage, before)
        after = row.get("victim_health_after")
        health[key] = int(after) if after is not None else max(0, before - raw_damage)
        if _player_key(row, "attacker") != owner_steamid:
            continue
        item = ledger[round_number]
        if victim in opponents:
            item["enemy_damage_raw"] += raw_damage
            item["enemy_damage_effective_reconstruction"] += effective_damage
        elif victim in owner_team and victim != owner_steamid:
            item["team_damage_raw"] += raw_damage
        else:
            item["self_world_damage_raw"] += raw_damage
        if str(row.get("weapon") or "").lower() in {"hegrenade", "inferno", "molotov", "incgrenade"}:
            item["utility_damage_raw"] += raw_damage
        item["source_event_ids"].append(f"damage:{index}")

    for round_number, row in player_rounds.items():
        item = ledger[round_number]
        item["survived"] = bool(row.get("survived"))
        item["kast_contribution_without_trade"] = bool(
            item["kills"] or item["assists"] or item["survived"]
        )

    rows = [ledger[number] for number in sorted(ledger)]
    regulation = [row for row in rows if row["round_classification"] == "regulation"]
    totals = {
        key: sum(int(row[key] or 0) for row in regulation)
        for key in (
            "kills",
            "deaths",
            "assists",
            "flash_assists",
            "headshot_kills",
            "enemy_damage_raw",
            "enemy_damage_effective_reconstruction",
            "team_damage_raw",
            "self_world_damage_raw",
            "utility_damage_raw",
        )
    }
    totals["regulation_rounds"] = len(regulation)
    totals["observed_participation_rounds"] = sum(row["player_participation"] == "event_observed" for row in regulation)
    totals["kast_without_trade_known_rounds"] = sum(
        row["kast_contribution_without_trade"] is True for row in regulation
    )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "owner_steamid": owner_steamid,
        "owner_team_steamids": sorted(owner_team),
        "opponent_steamids": sorted(opponents),
        "rows": rows,
        "totals": totals,
        "ledger_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/cs2_coach.db"))
    parser.add_argument("--artifact-id", type=int, default=91)
    parser.add_argument("--owner-steamid", default="76561198056634139")
    parser.add_argument("--expect-sha256")
    args = parser.parse_args()
    metadata, payload = _load_artifact(args.db, args.artifact_id)
    result = {"artifact": metadata, "ledger": build_ledger(payload, args.owner_steamid)}
    if args.expect_sha256 and result["ledger"]["ledger_sha256"] != args.expect_sha256:
        raise SystemExit("forensic ledger determinism check failed")
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
