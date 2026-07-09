from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import MetricSnapshot
from app.services.metric_snapshots import upsert_metric_snapshot

CORE_COMBAT_METRICS_VERSION = "core-combat-metrics-v1"
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
    known_players = _known_players(events, players=players)
    if not known_players:
        return []

    round_numbers = _round_numbers(events)
    inferred_rounds = False
    if not round_numbers:
        round_numbers = _combat_round_numbers(events)
        inferred_rounds = bool(round_numbers)

    kill_events = [event for event in events if event.get("event_type") == "player_kill"]
    death_events = [event for event in events if event.get("event_type") == "player_death"]
    kill_source_events = kill_events if kill_events else death_events
    kills_from_deaths = bool(death_events and not kill_events)
    damage_events = [event for event in events if event.get("event_type") == "damage"]
    survival_events = [event for event in events if event.get("event_type") == "round_survival"]
    opening_duel_events = [event for event in events if event.get("event_type") == "opening_duel"]
    traded_death_events = [event for event in events if event.get("event_type") == "traded_death"]
    assists_available = _assists_available(kill_source_events)

    results = []
    for player_key, player in sorted(known_players.items()):
        metrics: dict[str, Any] = {}
        confidence: dict[str, str] = {}
        caveats: list[str] = []

        if kill_source_events:
            metrics["kills"] = sum(1 for event in kill_source_events if _player_key(event.get("actor")) == player_key)
            confidence["kills"] = (
                "medium" if kills_from_deaths else _event_confidence(kill_source_events, "actor", player_key)
            )
            if kills_from_deaths:
                caveats.append("Kills derived from player_death actor because player_kill events were unavailable.")
        else:
            caveats.append("Kill events unavailable; kills are omitted instead of filled as zero.")

        if death_events:
            metrics["deaths"] = sum(1 for event in death_events if _player_key(event.get("victim")) == player_key)
            confidence["deaths"] = _event_confidence(death_events, "victim", player_key)
        else:
            caveats.append("Death events unavailable; deaths are omitted instead of filled as zero.")

        if assists_available:
            metrics["assists"] = sum(1 for event in kill_source_events if _player_key(_assister(event)) == player_key)
            confidence["assists"] = _event_confidence(kill_source_events, "assister", player_key)
        else:
            caveats.append("Assist source unavailable; assists are omitted instead of filled as zero.")

        player_damage_events = [event for event in damage_events if _player_key(event.get("actor")) == player_key]
        damage_values = [
            value for event in player_damage_events for value in [_damage_health(event)] if value is not None
        ]
        if damage_events:
            confidence["damage"] = _event_confidence(damage_events, "actor", player_key)
            missing_damage = any(_damage_health(event) is None for event in player_damage_events)
            if player_damage_events and not damage_values:
                caveats.append(
                    "Damage events for this player omitted health damage; damage and ADR-like metrics are omitted."
                )
            else:
                metrics["damage"] = sum(damage_values)
            if missing_damage:
                caveats.append("Some damage events omitted health damage; those rows were ignored.")
        else:
            caveats.append("Damage events unavailable; damage and ADR-like metrics are omitted.")

        player_rounds = _player_rounds(player_key, survival_events, round_numbers)
        if player_rounds:
            metrics["rounds"] = len(player_rounds)
            confidence["rounds"] = "low" if inferred_rounds else "medium"
            if inferred_rounds:
                caveats.append(
                    "Round count inferred from combat event round numbers because round events were unavailable."
                )
        else:
            caveats.append("Round events unavailable for this player; round count and ADR-like metrics are omitted.")

        if "damage" in metrics and metrics.get("rounds"):
            metrics["adr"] = round(metrics["damage"] / metrics["rounds"], 3)
            confidence["adr"] = (
                "medium" if confidence.get("damage") != "low" and confidence.get("rounds") != "low" else "low"
            )

        player_survival = [event for event in survival_events if _player_key(event.get("actor")) == player_key]
        survival_values = [event.get("context", {}).get("survived") for event in player_survival]
        survival_booleans = [value for value in survival_values if isinstance(value, bool)]
        if player_survival and len(survival_booleans) == len(player_survival):
            metrics["survived_rounds"] = sum(1 for survived in survival_booleans if survived)
            metrics["survival_rate"] = round(metrics["survived_rounds"] / len(player_survival), 3)
            confidence["survival"] = _event_confidence(player_survival, "actor", player_key)
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

        results.append(
            CoreCombatMetricsResult(
                player_key=player_key,
                player_name=_clean_text(player.get("name")),
                player_steamid=_clean_text(player.get("steamid")),
                metrics=metrics,
                confidence_baseline={
                    "source": CORE_COMBAT_METRICS_VERSION,
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
        )
        for result in results
    ]


def _add_opening_duel_metrics(
    metrics: dict[str, Any],
    confidence: dict[str, str],
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
        confidence["opening_death_rate"] = _event_confidence(player_duels, "victim", player_key)
    else:
        caveats.append("Round count unavailable; opening death rate is omitted.")

    if player_duels:
        metrics["opening_duel_win_rate"] = round(opening_duel_wins / len(player_duels), 3)
        confidence["opening_duel_win_rate"] = _event_confidence(player_duels, "actor", player_key)
        caveats.extend(_event_caveats(player_duels))
    else:
        caveats.append("Player had no derived opening duel events; opening duel win rate is omitted.")


def _add_trade_death_metrics(
    metrics: dict[str, Any],
    confidence: dict[str, str],
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
        confidence["traded_death_rate"] = _event_confidence(player_deaths, "victim", player_key)
        confidence["untraded_death_rate"] = _event_confidence(player_deaths, "victim", player_key)
    else:
        if player_deaths:
            confidence["traded_death_rate"] = "low"
            confidence["untraded_death_rate"] = "low"
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
