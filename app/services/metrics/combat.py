"""Canonical core-combat metric computation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Match, MetricSnapshot
from app.services.metrics.confidence import confidence_record
from app.services.metrics.snapshots import deterministic_input_hash, upsert_metric_snapshot
from app.services.parsing.match_phase import (
    accepted_events,
    accepted_match_phase,
    kast_round_ledger,
    player_participation_rounds,
)

CORE_COMBAT_METRICS_VERSION = "core-combat-metrics-v2"
CORE_COMBAT_SEMANTIC_VERSION = "2.0.0"
CORE_COMBAT_SNAPSHOT_SOURCE = "core_combat_metrics"


@dataclass(frozen=True)
class CoreCombatMetricsResult:
    player_key: str
    player_name: str | None
    player_steamid: str | None
    metrics: dict[str, Any]
    confidence_baseline: dict[str, Any]
    caveats: list[str]
    metadata: dict[str, Any]


def calculate_core_combat_metrics(
    normalized_events: Iterable[Mapping[str, Any]],
    *,
    players: Sequence[Mapping[str, Any]] | None = None,
) -> list[CoreCombatMetricsResult]:
    events = [dict(event) for event in normalized_events]
    phase = accepted_match_phase(events)
    phase_events = accepted_events(events, phase)
    known_players = _known_players(events, players=players)
    if not known_players:
        return []

    round_numbers = set(phase.round_numbers)
    inferred_rounds = False

    kill_events = [event for event in phase_events if event.get("event_type") == "player_kill"]
    death_events = [event for event in phase_events if event.get("event_type") == "player_death"]
    kill_source_events = kill_events if kill_events else death_events
    kills_from_deaths = bool(death_events and not kill_events)
    damage_events = [event for event in phase_events if event.get("event_type") == "damage"]
    survival_events = [event for event in phase_events if event.get("event_type") == "round_survival"]
    opening_duel_events = [event for event in phase_events if event.get("event_type") == "opening_duel"]
    traded_death_events = [event for event in phase_events if event.get("event_type") == "traded_death"]
    assists_available = _assists_available(kill_source_events)
    inferred_opponents = _inferred_opponents(kill_source_events)

    results = []
    for player_key, player in sorted(known_players.items()):
        metrics: dict[str, Any] = {}
        confidence: dict[str, dict[str, Any]] = {}
        caveats: list[str] = []
        validation: dict[str, dict[str, Any]] = {}
        player_kill_events: list[Mapping[str, Any]] = []

        if kill_source_events:
            player_kill_events = [
                event
                for event in kill_source_events
                if _player_key(event.get("actor")) == player_key
                and _player_key(event.get("victim")) not in {None, player_key}
                and _relation(event.get("actor"), event.get("victim"), player_key, inferred_opponents)
                != "team"
            ]
            kills_relation_proven = all(
                _relation(event.get("actor"), event.get("victim"), player_key, inferred_opponents) == "enemy"
                for event in player_kill_events
            )
            metrics["kills"] = len(player_kill_events)
            confidence["kills"] = _confidence(
                "kills",
                "medium" if kills_from_deaths else _event_confidence(kill_source_events, "actor", player_key),
                kill_source_events,
                reasons=(
                    ["Kills derived from player_death actor because player_kill events were unavailable."]
                    if kills_from_deaths
                    else ["Kills are counted from supported kill/death events."]
                ),
            )
            if kills_from_deaths:
                caveats.append("Kills derived from player_death actor because player_kill events were unavailable.")
            validation["kills"] = {
                "status": "validated" if kills_relation_proven else "quarantined",
                "reason_codes": [
                    "accepted_phase_enemy_kill_events"
                    if kills_relation_proven
                    else "victim_team_relation_unproven"
                ],
            }
        else:
            caveats.append("Kill events unavailable; kills are omitted instead of filled as zero.")

        if death_events:
            metrics["deaths"] = sum(1 for event in death_events if _player_key(event.get("victim")) == player_key)
            confidence["deaths"] = _confidence(
                "deaths",
                _event_confidence(death_events, "victim", player_key),
                death_events,
                reasons=["Deaths are counted from supported death events."],
            )
            validation["deaths"] = {"status": "validated", "reason_codes": ["accepted_phase_victim_events"]}
        else:
            caveats.append("Death events unavailable; deaths are omitted instead of filled as zero.")

        if assists_available:
            player_assists = [event for event in kill_source_events if _player_key(_assister(event)) == player_key]
            assists_relation_proven = all(
                _relation(_assister(event), event.get("victim"), player_key, inferred_opponents) == "enemy"
                for event in player_assists
            )
            flash_assists = sum(1 for event in player_assists if _is_flash_assist(event))
            metrics["ordinary_assists"] = len(player_assists) - flash_assists
            metrics["flash_assists"] = flash_assists
            metrics["combined_assists"] = len(player_assists)
            metrics["assists"] = len(player_assists)
            confidence["assists"] = _confidence(
                "assists",
                _event_confidence(kill_source_events, "assister", player_key),
                kill_source_events,
                reasons=["Assists depend on source assister fields."],
            )
            for key in ("ordinary_assists", "flash_assists", "combined_assists", "assists"):
                validation[key] = {
                    "status": "validated" if assists_relation_proven else "quarantined",
                    "reason_codes": [
                        "accepted_phase_assister_events"
                        if assists_relation_proven
                        else "assisted_victim_team_relation_unproven"
                    ],
                }
        else:
            caveats.append("Assist source unavailable; assists are omitted instead of filled as zero.")

        player_damage_events = [event for event in damage_events if _player_key(event.get("actor")) == player_key]
        damage_values = [
            value for event in player_damage_events for value in [_damage_health(event)] if value is not None
        ]
        if damage_events:
            confidence["damage"] = _confidence(
                "damage",
                _event_confidence(damage_events, "actor", player_key),
                damage_events,
                reasons=["Damage is summed only from populated damage_health facts."],
            )
            missing_damage = any(_damage_health(event) is None for event in player_damage_events)
            if player_damage_events and not damage_values:
                caveats.append(
                    "Damage events for this player omitted health damage; damage and ADR-like metrics are omitted."
                )
            else:
                damage_classes: dict[str, int] = {}
                for event in player_damage_events:
                    value = _damage_health(event)
                    if value is None:
                        continue
                    relation = _damage_relation(event, player_key)
                    key = {
                        "enemy": "raw_attempted_enemy_damage",
                        "team": "team_damage",
                        "self_world": "self_world_damage",
                        "unknown": "unclassified_raw_attempted_damage",
                    }[relation]
                    damage_classes[key] = damage_classes.get(key, 0) + value
                metrics.update(damage_classes)
                for key in damage_classes:
                    validation[key] = {
                        "status": "quarantined" if key == "unclassified_raw_attempted_damage" else "validated",
                        "reason_codes": [
                            "victim_relation_missing"
                            if key == "unclassified_raw_attempted_damage"
                            else "explicit_victim_relation"
                        ],
                    }
            if missing_damage:
                caveats.append("Some damage events omitted health damage; those rows were ignored.")
        else:
            caveats.append("Damage events unavailable; damage and ADR-like metrics are omitted.")

        player_rounds, participation_complete = player_participation_rounds(player_key, events, phase)
        kast_ledger, kast_status = kast_round_ledger(player_key, events, phase)
        if player_rounds:
            metrics["rounds"] = len(player_rounds)
            confidence["rounds"] = _confidence(
                "rounds",
                "low" if inferred_rounds else "medium",
                survival_events,
                reasons=(
                    ["Round count inferred from combat events."]
                    if inferred_rounds
                    else ["Round count uses supported round or survival events."]
                ),
            )
            if inferred_rounds:
                caveats.append(
                    "Round count inferred from combat event round numbers because round events were unavailable."
                )
            validation["rounds"] = {
                "status": "validated" if participation_complete else "quarantined",
                "reason_codes": [phase.participation_reason],
            }
        else:
            caveats.append("Round events unavailable for this player; round count and ADR-like metrics are omitted.")

        validation["adr"] = {
            "status": "quarantined",
            "reason_codes": ["effective_enemy_damage_unproven", "participation_incomplete"],
        }
        validation["kast"] = {
            "status": kast_status,
            "reason_codes": ["trade_evidence_incomplete", "participation_incomplete"],
        }
        if kast_status == "validated" and kast_ledger:
            metrics["kast"] = round(
                sum(1 for row in kast_ledger if row["kast"] is True) / len(kast_ledger) * 100,
                3,
            )
            validation["kast"]["reason_codes"] = ["complete_per_round_kast_ledger"]

        player_survival = [event for event in survival_events if _player_key(event.get("actor")) == player_key]
        survival_values = [event.get("context", {}).get("survived") for event in player_survival]
        survival_booleans = [value for value in survival_values if isinstance(value, bool)]
        if player_survival and len(survival_booleans) == len(player_survival):
            metrics["survived_rounds"] = sum(1 for survived in survival_booleans if survived)
            metrics["survival_rate"] = round(metrics["survived_rounds"] / len(player_survival), 3)
            confidence["survival_rate"] = _confidence(
                "survival_rate",
                _event_confidence(player_survival, "actor", player_key),
                player_survival,
                reasons=["Survival rate is calculated from round_survival facts."],
            )
            validation["survived_rounds"] = validation["survival_rate"] = {
                "status": "quarantined",
                "reason_codes": ["participation_incomplete"],
            }
        else:
            caveats.append("Round survival events unavailable or incomplete; survival metrics are omitted.")

        _add_opening_duel_metrics(
            metrics,
            confidence,
            caveats,
            player_key=player_key,
            opening_duel_events=opening_duel_events,
            player_round_count=metrics.get("rounds"),
        )
        _add_trade_death_metrics(
            metrics,
            confidence,
            caveats,
            player_key=player_key,
            traded_death_events=traded_death_events,
        )

        accepted_kills = metrics.get("kills")
        accepted_deaths = metrics.get("deaths")
        if isinstance(accepted_kills, int) and isinstance(accepted_deaths, int):
            metrics["kd_ratio"] = None if accepted_deaths == 0 else round(accepted_kills / accepted_deaths, 3)
            validation["kd_ratio"] = {
                "status": validation["kills"]["status"],
                "reason_codes": ["derived_from_same_version_accepted_counts", "zero_deaths_is_null"],
            }
        headshot_kills = sum(
            1
            for event in player_kill_events
            if _is_headshot(event)
        )
        if kill_source_events:
            metrics["headshot_kills"] = headshot_kills
            metrics["headshot_kill_rate"] = (
                round(headshot_kills / accepted_kills * 100, 3)
                if isinstance(accepted_kills, int) and accepted_kills
                else 0.0
            )
            validation["headshot_kills"] = validation["headshot_kill_rate"] = {
                "status": validation["kills"]["status"],
                "reason_codes": ["headshot_kills_divided_by_accepted_kills"],
            }

        results.append(
            CoreCombatMetricsResult(
                player_key=player_key,
                player_name=_clean_text(player.get("name")),
                player_steamid=_clean_text(player.get("steamid")),
                metrics=metrics,
                confidence_baseline={
                    "source": CORE_COMBAT_METRICS_VERSION,
                    "confidence": _overall_confidence(confidence, metrics),
                    "metrics": confidence,
                    "event_coverage": {
                        "kill_events": len(kill_events),
                        "death_events": len(death_events),
                        "damage_events": len(damage_events),
                        "rounds": len(round_numbers),
                        "survival_events": len(survival_events),
                        "opening_duel_events": len(opening_duel_events),
                        "traded_death_events": len(traded_death_events),
                        "assists_available": assists_available,
                    },
                },
                caveats=_ordered_unique(caveats),
                metadata={
                    "schema_version": CORE_COMBAT_METRICS_VERSION,
                    "input_event_schema": _input_schema(events),
                    "event_count": len(events),
                    "input_event_hash": deterministic_input_hash(events),
                    "accepted_phase": {
                        "round_numbers": list(phase.round_numbers),
                        "final_round_end_tick": phase.final_round_end_tick,
                        "participation_complete": phase.participation_complete,
                    },
                    "metric_validation": validation,
                    "kast_round_ledger": kast_ledger,
                },
            )
        )
    return results


def calculate_and_store_core_combat_metrics(
    db: Session,
    *,
    match_id: int,
    normalized_events: Iterable[Mapping[str, Any]],
    players: Sequence[Mapping[str, Any]] | None = None,
    source: str = CORE_COMBAT_SNAPSHOT_SOURCE,
    source_parser_artifact_id: int | None = None,
    source_event_set_id: str | None = None,
) -> list[MetricSnapshot]:
    results = calculate_core_combat_metrics(normalized_events, players=players)
    match = db.get(Match, match_id)
    validated_snapshot = bool(match and match.user_id is not None and source_event_set_id)
    return [
        upsert_metric_snapshot(
            db,
            match_id=match_id,
            player_key=result.player_key,
            player_name=result.player_name,
            player_steamid=result.player_steamid,
            source=source,
            source_parser_artifact_id=source_parser_artifact_id,
            source_event_set_id=source_event_set_id,
            metrics=result.metrics,
            confidence_baseline=result.confidence_baseline,
            caveats=result.caveats,
            metadata=result.metadata,
            owner_user_id=match.user_id if match else None,
            metric_domain="core_combat",
            semantic_version=CORE_COMBAT_SEMANTIC_VERSION,
            validation_status="validated" if validated_snapshot else "legacy_unverified",
            implementation_version=CORE_COMBAT_METRICS_VERSION,
            input_event_hash=result.metadata.get("input_event_hash"),
        )
        for result in results
    ]


def _add_opening_duel_metrics(
    metrics: dict[str, Any],
    confidence: dict[str, dict[str, Any]],
    caveats: list[str],
    *,
    player_key: str,
    opening_duel_events: Sequence[Mapping[str, Any]],
    player_round_count: Any,
) -> None:
    if not opening_duel_events:
        caveats.append("Opening duel events unavailable; opening duel rates are omitted.")
        return

    player_duels = [
        event
        for event in opening_duel_events
        if _player_key(event.get("actor")) == player_key or _player_key(event.get("victim")) == player_key
    ]
    opening_duel_wins = sum(1 for event in player_duels if _player_key(event.get("actor")) == player_key)
    opening_deaths = sum(1 for event in player_duels if _player_key(event.get("victim")) == player_key)
    metrics["opening_duels"] = len(player_duels)
    metrics["opening_duel_wins"] = opening_duel_wins
    metrics["opening_deaths"] = opening_deaths

    if isinstance(player_round_count, int) and player_round_count > 0:
        metrics["opening_death_rate"] = round(opening_deaths / player_round_count, 3)
        confidence["opening_death_rate"] = _confidence(
            "opening_death_rate",
            _event_confidence(player_duels, "victim", player_key),
            player_duels,
            reasons=["Opening death rate depends on parser opening duel event order."],
        )
    else:
        caveats.append("Round count unavailable; opening death rate is omitted.")

    if player_duels:
        metrics["opening_duel_win_rate"] = round(opening_duel_wins / len(player_duels), 3)
        confidence["opening_duel_win_rate"] = _confidence(
            "opening_duel_win_rate",
            _event_confidence(player_duels, "actor", player_key),
            player_duels,
            reasons=["Opening duel win rate depends on parser opening duel event order."],
        )
        caveats.extend(_event_caveats(player_duels))
    else:
        caveats.append("Player had no derived opening duel events; opening duel win rate is omitted.")


def _add_trade_death_metrics(
    metrics: dict[str, Any],
    confidence: dict[str, dict[str, Any]],
    caveats: list[str],
    *,
    player_key: str,
    traded_death_events: Sequence[Mapping[str, Any]],
) -> None:
    if not traded_death_events:
        caveats.append("Traded death events unavailable; trade death rates are omitted.")
        return

    player_deaths = [event for event in traded_death_events if _player_key(event.get("victim")) == player_key]
    traded_deaths = sum(1 for event in player_deaths if _trade_status(event) == "traded")
    untraded_deaths = sum(1 for event in player_deaths if _trade_status(event) == "untraded")
    ambiguous_deaths = sum(1 for event in player_deaths if _trade_status(event) == "ambiguous")
    known_trade_deaths = traded_deaths + untraded_deaths

    metrics["traded_deaths"] = traded_deaths
    metrics["untraded_deaths"] = untraded_deaths
    metrics["ambiguous_traded_deaths"] = ambiguous_deaths
    metrics["trade_status_known_deaths"] = known_trade_deaths

    if known_trade_deaths:
        metrics["traded_death_rate"] = round(traded_deaths / known_trade_deaths, 3)
        metrics["untraded_death_rate"] = round(untraded_deaths / known_trade_deaths, 3)
        confidence["traded_death_rate"] = _confidence(
            "traded_death_rate",
            _event_confidence(player_deaths, "victim", player_key),
            player_deaths,
            reasons=["Traded death rate depends on parser trade window and side inference."],
        )
        confidence["untraded_death_rate"] = _confidence(
            "untraded_death_rate",
            _event_confidence(player_deaths, "victim", player_key),
            player_deaths,
            reasons=["Untraded death rate depends on parser trade window and side inference."],
        )
    else:
        if player_deaths:
            confidence["traded_death_rate"] = _confidence(
                "traded_death_rate",
                "low",
                player_deaths,
                reasons=["No deaths with known trade status for this player."],
            )
            confidence["untraded_death_rate"] = _confidence(
                "untraded_death_rate",
                "low",
                player_deaths,
                reasons=["No deaths with known trade status for this player."],
            )
        caveats.append("No deaths with known trade status for this player; trade death rates are omitted.")

    if ambiguous_deaths:
        caveats.append("Ambiguous traded death events were excluded from traded/untraded death rates.")
    caveats.extend(_event_caveats(player_deaths))


def _known_players(
    events: Sequence[Mapping[str, Any]],
    *,
    players: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Mapping[str, Any]]:
    known: dict[str, Mapping[str, Any]] = {}
    for player in players or []:
        _add_player(known, player)
    for event in events:
        _add_player(known, event.get("actor"))
        _add_player(known, event.get("victim"))
        _add_player(known, _assister(event))
    return known


def _overall_confidence(confidence: Mapping[str, Any], metrics: Mapping[str, Any]) -> str:
    levels = [
        str(record.get("level"))
        for metric_name, record in confidence.items()
        if metric_name in metrics and isinstance(record, Mapping) and record.get("level")
    ]
    if not levels:
        return "unavailable"
    if "low" in levels or "unavailable" in levels:
        return "low"
    if "medium" in levels:
        return "medium"
    return "high"


def _add_player(known: dict[str, Mapping[str, Any]], player: Any) -> None:
    if not isinstance(player, Mapping):
        return
    key = _player_key(player)
    if key and key not in known:
        known[key] = dict(player)


def _round_numbers(events: Sequence[Mapping[str, Any]]) -> set[int]:
    return {
        event["round_number"]
        for event in events
        if event.get("event_type") in {"round_summary", "round_timing", "round_survival"}
        and isinstance(event.get("round_number"), int)
    }


def _combat_round_numbers(events: Sequence[Mapping[str, Any]]) -> set[int]:
    return {
        event["round_number"]
        for event in events
        if event.get("event_type") in {"player_kill", "player_death", "damage"}
        and isinstance(event.get("round_number"), int)
    }


def _player_rounds(player_key: str, survival_events: Sequence[Mapping[str, Any]], rounds: set[int]) -> set[int]:
    survival_rounds = {
        event["round_number"]
        for event in survival_events
        if _player_key(event.get("actor")) == player_key and isinstance(event.get("round_number"), int)
    }
    return survival_rounds or rounds


def _assists_available(events: Sequence[Mapping[str, Any]]) -> bool:
    return any(_has_assister_field(event) for event in events)


def _has_assister_field(event: Mapping[str, Any]) -> bool:
    context = event.get("context")
    payload = event.get("payload")
    return (isinstance(context, Mapping) and "assister" in context) or (
        isinstance(payload, Mapping) and ("assister_name" in payload or "assister_steamid" in payload)
    )


def _assister(event: Mapping[str, Any]) -> Mapping[str, Any] | None:
    context = event.get("context")
    if isinstance(context, Mapping) and isinstance(context.get("assister"), Mapping):
        return context["assister"]
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        return None
    name = _clean_text(payload.get("assister_name") or payload.get("assister"))
    steamid = _clean_text(payload.get("assister_steamid"))
    if not name and not steamid:
        return None
    return {"name": name, "steamid": steamid}


def _is_flash_assist(event: Mapping[str, Any]) -> bool:
    context = event.get("context")
    payload = event.get("payload")
    value = context.get("assistedflash") if isinstance(context, Mapping) else None
    if value is None and isinstance(payload, Mapping):
        value = payload.get("assistedflash")
    return value is True or value == 1 or str(value).lower() == "true"


def _is_headshot(event: Mapping[str, Any]) -> bool:
    context = event.get("context")
    payload = event.get("payload")
    value = context.get("headshot") if isinstance(context, Mapping) else None
    if value is None and isinstance(payload, Mapping):
        value = payload.get("headshot")
    return value is True or value == 1 or str(value).lower() == "true"


def _damage_health(event: Mapping[str, Any]) -> int | None:
    context = event.get("context")
    value = context.get("damage_health") if isinstance(context, Mapping) else None
    if value is None:
        payload = event.get("payload")
        value = (
            payload.get("damage_health") or payload.get("dmg_health") or payload.get("health_damage")
            if isinstance(payload, Mapping)
            else None
        )
    if isinstance(value, bool) or value is None:
        return None
    try:
        damage = int(value)
    except (TypeError, ValueError):
        return None
    return max(damage, 0)


def _damage_relation(event: Mapping[str, Any], player_key: str) -> str:
    victim = event.get("victim")
    victim_key = _player_key(victim)
    if victim_key is None or victim_key == player_key:
        return "self_world"
    actor = event.get("actor")
    actor_team = _player_team(actor)
    victim_team = _player_team(victim)
    if actor_team and victim_team:
        return "team" if actor_team == victim_team else "enemy"
    return "unknown"


def _player_team(player: Any) -> str | None:
    if not isinstance(player, Mapping):
        return None
    value = player.get("team") or player.get("side") or player.get("team_name")
    text = str(value).strip().lower() if value is not None else ""
    return text or None


def _relation(
    actor: Any,
    victim: Any,
    actor_key: str,
    inferred_opponents: Mapping[str, set[str]],
) -> str:
    victim_key = _player_key(victim)
    if victim_key is None or victim_key == actor_key:
        return "self_world"
    actor_team = _player_team(actor)
    victim_team = _player_team(victim)
    if actor_team and victim_team:
        return "team" if actor_team == victim_team else "enemy"
    if victim_key in inferred_opponents.get(actor_key, set()):
        return "enemy"
    return "unknown"


def _inferred_opponents(events: Sequence[Mapping[str, Any]]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for event in events:
        actor = _player_key(event.get("actor"))
        victim = _player_key(event.get("victim"))
        if actor and victim and actor != victim:
            graph.setdefault(actor, set()).add(victim)
            graph.setdefault(victim, set()).add(actor)
    if len(graph) != 10:
        return {}
    colors: dict[str, int] = {}
    for start in graph:
        if start in colors:
            continue
        colors[start] = 0
        pending = [start]
        while pending:
            player = pending.pop()
            for opponent in graph[player]:
                expected = 1 - colors[player]
                if opponent in colors and colors[opponent] != expected:
                    return {}
                if opponent not in colors:
                    colors[opponent] = expected
                    pending.append(opponent)
    if list(colors.values()).count(0) != 5 or list(colors.values()).count(1) != 5:
        return {}
    teams = ({player for player, color in colors.items() if color == value} for value in (0, 1))
    first, second = teams
    return {
        player: (second if player in first else first)
        for player in graph
    }


def _trade_status(event: Mapping[str, Any]) -> str | None:
    context = event.get("context")
    if not isinstance(context, Mapping):
        return None
    status = _clean_text(context.get("trade_status"))
    if status in {"traded", "untraded", "ambiguous"}:
        return status
    traded = context.get("traded")
    if traded is True:
        return "traded"
    if traded is False:
        return "untraded"
    return "ambiguous"


def _event_confidence(events: Sequence[Mapping[str, Any]], role: str, player_key: str) -> str:
    values = []
    for event in events:
        player = _assister(event) if role == "assister" else event.get(role)
        if _player_key(player) == player_key:
            values.append(event.get("confidence"))
    if not values:
        return "medium"
    if "low" in values or "unavailable" in values:
        return "low"
    if "medium" in values:
        return "medium"
    return "high"


def _confidence(
    metric_id: str,
    level: str,
    events: Sequence[Mapping[str, Any]],
    *,
    reasons: Sequence[str],
) -> dict[str, Any]:
    return confidence_record(
        metric_id,
        level,
        reasons=reasons,
        reason_codes=[f"event_confidence_{level}", "normalized_event_source"],
        source_trust={
            "event_confidence": level,
            "event_count": len(events),
            "source_kinds": _source_kinds(events),
        },
    )


def _source_kinds(events: Sequence[Mapping[str, Any]]) -> list[str]:
    kinds: set[str] = set()
    for event in events:
        source = event.get("source")
        if isinstance(source, Mapping) and source.get("kind"):
            kinds.add(str(source["kind"]))
    return sorted(kinds)


def _event_caveats(events: Sequence[Mapping[str, Any]]) -> list[str]:
    caveats: list[str] = []
    for event in events:
        values = event.get("caveats")
        if isinstance(values, Sequence) and not isinstance(values, str):
            caveats.extend(str(value) for value in values if value)
    return _ordered_unique(caveats)


def _player_key(player: Any) -> str | None:
    if not isinstance(player, Mapping):
        return None
    steamid = _clean_text(player.get("steamid"))
    if steamid:
        return f"steam:{steamid}"
    name = _clean_text(player.get("name"))
    if name:
        return f"name:{name}"
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _input_schema(events: Sequence[Mapping[str, Any]]) -> str | None:
    schemas = {_clean_text(event.get("schema_version")) for event in events}
    schemas.discard(None)
    return sorted(schemas)[0] if len(schemas) == 1 else None


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered
