"""Accepted match-phase and round-ledger primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AcceptedMatchPhase:
    round_numbers: tuple[int, ...]
    final_round_end_tick: int | None
    classification: str
    participation_complete: bool
    participation_reason: str

    def accepts(self, event: Mapping[str, Any]) -> bool:
        round_number = event.get("round_number")
        if not isinstance(round_number, int) or round_number not in self.round_numbers:
            return False
        tick = event.get("tick")
        if self.final_round_end_tick is not None and isinstance(tick, int) and tick > self.final_round_end_tick:
            return False
        context = event.get("context")
        phase = str(context.get("phase") or "").lower() if isinstance(context, Mapping) else ""
        return phase not in {"warmup", "post_match", "postmatch"}


def accepted_match_phase(events: Sequence[Mapping[str, Any]]) -> AcceptedMatchPhase:
    completed: dict[int, int | None] = {}
    for event in events:
        if event.get("event_type") not in {"round_timing", "round_summary"}:
            continue
        context = event.get("context")
        boundary = context.get("boundary") if isinstance(context, Mapping) else None
        if boundary != "round_end" and event.get("source_event") != "round_end":
            continue
        round_number = event.get("round_number")
        if isinstance(round_number, int):
            tick = event.get("tick")
            completed[round_number] = tick if isinstance(tick, int) else None
    round_numbers = tuple(sorted(completed))
    end_ticks = [tick for tick in completed.values() if tick is not None]
    participation_events = [event for event in events if event.get("event_type") == "round_participation"]
    complete = bool(round_numbers) and len(participation_events) >= len(round_numbers)
    return AcceptedMatchPhase(
        round_numbers=round_numbers,
        final_round_end_tick=max(end_ticks) if end_ticks else None,
        classification="regulation_or_overtime_completed",
        participation_complete=complete,
        participation_reason=(
            "explicit_round_participation_evidence"
            if complete
            else "quiet_round_disconnect_reconnect_evidence_incomplete"
        ),
    )


def accepted_events(
    events: Sequence[Mapping[str, Any]], phase: AcceptedMatchPhase
) -> list[dict[str, Any]]:
    return [dict(event) for event in events if phase.accepts(event)]


def player_participation_rounds(
    player_key: str,
    events: Sequence[Mapping[str, Any]],
    phase: AcceptedMatchPhase,
) -> tuple[tuple[int, ...], bool]:
    explicit = {
        event["round_number"]
        for event in events
        if event.get("event_type") == "round_participation"
        and _player_key(event.get("actor")) == player_key
        and event.get("context", {}).get("participated") is True
        and isinstance(event.get("round_number"), int)
        and phase.accepts(event)
    }
    if explicit:
        return tuple(sorted(explicit)), len(explicit) == len(phase.round_numbers)
    # A roster-observed player is provisionally associated with every completed
    # round. This prevents activity rows from becoming a denominator, but the
    # returned false flag keeps participation-derived metrics quarantined.
    return phase.round_numbers, False


def kast_round_ledger(
    player_key: str,
    events: Sequence[Mapping[str, Any]],
    phase: AcceptedMatchPhase,
) -> tuple[list[dict[str, Any]], str]:
    rounds, participation_complete = player_participation_rounds(player_key, events, phase)
    ledger = []
    trade_complete = True
    for round_number in rounds:
        round_events = [
            event
            for event in events
            if event.get("round_number") == round_number and phase.accepts(event)
        ]
        killed = any(
            event.get("event_type") in {"player_kill", "player_death"}
            and _player_key(event.get("actor")) == player_key
            and _player_key(event.get("victim")) not in {None, player_key}
            for event in round_events
        )
        assisted = any(
            event.get("event_type") in {"player_kill", "player_death"}
            and _player_key(_assister(event)) == player_key
            for event in round_events
        )
        survival_values = [
            event.get("context", {}).get("survived")
            for event in round_events
            if event.get("event_type") == "round_survival" and _player_key(event.get("actor")) == player_key
        ]
        survived = survival_values[0] if survival_values and isinstance(survival_values[0], bool) else None
        trade_values = [
            event.get("context", {}).get("traded")
            for event in round_events
            if event.get("event_type") == "traded_death" and _player_key(event.get("victim")) == player_key
        ]
        traded = trade_values[0] if trade_values and isinstance(trade_values[0], bool) else None
        died = any(
            event.get("event_type") == "player_death" and _player_key(event.get("victim")) == player_key
            for event in round_events
        )
        if died and traded is None:
            trade_complete = False
        contribution = True if killed or assisted or survived is True or traded is True else (
            False if survived is False and (not died or traded is False) else None
        )
        ledger.append(
            {
                "round_number": round_number,
                "participated": True,
                "kill": killed,
                "assist": assisted,
                "survive": survived,
                "trade": traded,
                "kast": contribution,
            }
        )
    status = "validated" if participation_complete and trade_complete else "quarantined"
    return ledger, status


def _player_key(player: Any) -> str | None:
    if not isinstance(player, Mapping):
        return None
    steamid = player.get("steamid")
    if steamid:
        return f"steam:{steamid}"
    name = player.get("name")
    return f"name:{name}" if name else None


def _assister(event: Mapping[str, Any]) -> Any:
    context = event.get("context")
    if isinstance(context, Mapping) and context.get("assister") is not None:
        return context.get("assister")
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        return None
    if payload.get("assister_steamid") or payload.get("assister_name"):
        return {"steamid": payload.get("assister_steamid"), "name": payload.get("assister_name")}
    return None
