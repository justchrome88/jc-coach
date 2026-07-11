"""Normalized combat-event derivation from parser evidence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from app.services.parsing.artifact_reader import NORMALIZED_EVENT_SCHEMA_VERSION, validate_normalized_event
from app.services.parsing.event_dictionary import EVENT_METRIC_DICTIONARY

DEFAULT_TRADE_WINDOW_SECONDS = 5.0
DEMO_TICK_RATE = 64.0


def derive_combat_events(
    normalized_events: Iterable[Mapping[str, Any]],
    *,
    trade_window_seconds: float = DEFAULT_TRADE_WINDOW_SECONDS,
    tracked_players: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Derive C04 combat coaching facts from already-normalized parser events.

    Trade timing uses a configurable default five-second window. The derivation does not parse raw
    demos; it only consumes normalized C03-style player_death and round events.
    """
    events = [dict(event) for event in normalized_events]
    deaths = [event for event in events if event.get("event_type") == "player_death"]
    derived: list[dict[str, Any]] = []
    derived.extend(_derive_opening_duels(deaths))
    derived.extend(_derive_traded_deaths(deaths, trade_window_seconds=trade_window_seconds))
    derived.extend(_derive_round_survival(events, deaths, tracked_players=tracked_players))
    return sorted((validate_normalized_event(event) for event in derived), key=_derived_sort_key)


def _derive_opening_duels(deaths: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    derived = []
    for round_number, round_deaths in _deaths_by_round(deaths).items():
        with_ticks = [event for event in round_deaths if isinstance(event.get("tick"), int)]
        missing_tick = len(with_ticks) != len(round_deaths)
        first = min(with_ticks or round_deaths, key=lambda event: _tick_or_large(event.get("tick")))
        caveats = list(first.get("caveats") or [])
        if missing_tick:
            caveats.append("Some death events in this round omitted tick; opening duel order is ambiguous.")
        if first.get("actor") is None or first.get("victim") is None:
            caveats.append("Opening duel participant identity is incomplete.")
        derived.append(
            _event(
                "opening_duel",
                "player_death",
                first,
                round_number=round_number,
                tick=first.get("tick"),
                actor=first.get("actor"),
                victim=first.get("victim"),
                context={
                    **dict(first.get("context") or {}),
                    "derivation": "first_player_death_per_round",
                    "opening_death": True,
                    "actor_outcome": "opening_duel_win",
                    "victim_outcome": "opening_duel_loss",
                    "opening_winner": first.get("actor"),
                    "opening_loser": first.get("victim"),
                },
                confidence=_derived_confidence(first, low=missing_tick),
                caveats=caveats,
                payload={"derived_from": _source_pointer(first)},
            )
        )
    return derived


def _derive_traded_deaths(
    deaths: Sequence[Mapping[str, Any]],
    *,
    trade_window_seconds: float,
) -> list[dict[str, Any]]:
    derived = []
    trade_window_ticks = max(0, round(trade_window_seconds * DEMO_TICK_RATE))
    for death in deaths:
        caveats = list(death.get("caveats") or [])
        trade = _find_trade(death, deaths, trade_window_ticks=trade_window_ticks)
        caveats.extend(trade["caveats"])
        status = "ambiguous" if trade["traded"] is None else "traded" if trade["traded"] else "untraded"
        derived.append(
            _event(
                "traded_death",
                "player_death",
                death,
                round_number=death.get("round_number"),
                tick=death.get("tick"),
                actor=death.get("actor"),
                victim=death.get("victim"),
                context={
                    "derivation": "same_round_refrag_window",
                    "trade_window_seconds": trade_window_seconds,
                    "trade_window_ticks": trade_window_ticks,
                    "traded": trade["traded"],
                    "trade_status": status,
                    "trade_tick": trade.get("trade_tick"),
                    "trade_delay_seconds": trade.get("trade_delay_seconds"),
                    "trade_actor": trade.get("trade_actor"),
                    "trade_victim": trade.get("trade_victim"),
                },
                confidence=_derived_confidence(death, low=trade["traded"] is None),
                caveats=caveats,
                payload={"derived_from": _source_pointer(death), "trade_candidate": trade.get("source_pointer")},
            )
        )
    return derived


def _derive_round_survival(
    events: Sequence[Mapping[str, Any]],
    deaths: Sequence[Mapping[str, Any]],
    *,
    tracked_players: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    round_numbers = sorted(
        {
            event.get("round_number")
            for event in events
            if isinstance(event.get("round_number"), int)
            and event.get("event_type") in {"player_death", "round_timing", "round_summary"}
        }
    )
    explicit_players = tracked_players is not None
    players = [_clean_player(player) for player in (tracked_players or _players_from_deaths(deaths))]
    players = [player for player in players if player]
    derived = []
    for round_number in round_numbers:
        round_deaths = [event for event in deaths if event.get("round_number") == round_number]
        dead_ids = {_player_key(event.get("victim")) for event in round_deaths if _player_key(event.get("victim"))}
        missing_victim = any(_player_key(event.get("victim")) is None for event in round_deaths)
        source_event = _round_source_event(events, round_number)
        for player in players:
            player_id = _player_key(player)
            if player_id is None:
                continue
            player_death = next(
                (event for event in round_deaths if _player_key(event.get("victim")) == player_id),
                None,
            )
            caveats = []
            if not explicit_players:
                caveats.append(
                    "Survival derived only for players present in combat events; silent players are unavailable."
                )
            if missing_victim:
                caveats.append("At least one death in this round omitted victim identity; survival is ambiguous.")
            derived.append(
                _event(
                    "round_survival",
                    "round_end",
                    source_event,
                    round_number=round_number,
                    tick=source_event.get("tick"),
                    actor=player,
                    context={
                        "derivation": "no_player_death_for_tracked_player_in_round",
                        "survived": player_id not in dead_ids,
                        "died": player_id in dead_ids,
                        "death_tick": player_death.get("tick") if player_death else None,
                        "tracked_players_explicit": explicit_players,
                        "team_side": player.get("team_side"),
                    },
                    confidence="medium" if explicit_players and not missing_victim else "low",
                    caveats=caveats,
                    payload={"derived_from": _source_pointer(source_event)},
                )
            )
    return derived


def _find_trade(
    death: Mapping[str, Any],
    deaths: Sequence[Mapping[str, Any]],
    *,
    trade_window_ticks: int,
) -> dict[str, Any]:
    round_number = death.get("round_number")
    death_tick = death.get("tick")
    actor_id = _player_key(death.get("actor"))
    victim_id = _player_key(death.get("victim"))
    if not isinstance(round_number, int) or not isinstance(death_tick, int) or not actor_id or not victim_id:
        return {
            "traded": None,
            "caveats": ["Death event omitted round, tick or participant identity; trade status is ambiguous."],
        }

    maybe_trade_without_team = None
    for candidate in sorted(deaths, key=lambda event: _tick_or_large(event.get("tick"))):
        candidate_tick = candidate.get("tick")
        if candidate is death or candidate.get("round_number") != round_number or not isinstance(candidate_tick, int):
            continue
        delay_ticks = candidate_tick - death_tick
        if delay_ticks <= 0 or delay_ticks > trade_window_ticks:
            continue
        if _player_key(candidate.get("victim")) != actor_id:
            continue

        teams = _trade_teams(death, candidate)
        if teams is None:
            maybe_trade_without_team = candidate
            continue
        if teams["candidate_actor_team"] == teams["original_victim_team"] and (
            teams["candidate_victim_team"] == teams["original_actor_team"]
        ):
            return {
                "traded": True,
                "trade_tick": candidate_tick,
                "trade_delay_seconds": round(delay_ticks / DEMO_TICK_RATE, 3),
                "trade_actor": candidate.get("actor"),
                "trade_victim": candidate.get("victim"),
                "source_pointer": _source_pointer(candidate),
                "caveats": [],
            }

    if maybe_trade_without_team is not None:
        candidate_tick = maybe_trade_without_team.get("tick")
        return {
            "traded": None,
            "trade_tick": candidate_tick,
            "trade_delay_seconds": round((candidate_tick - death_tick) / DEMO_TICK_RATE, 3)
            if isinstance(candidate_tick, int)
            else None,
            "trade_actor": maybe_trade_without_team.get("actor"),
            "trade_victim": maybe_trade_without_team.get("victim"),
            "source_pointer": _source_pointer(maybe_trade_without_team),
            "caveats": ["Source events do not include both actor/victim team side; traded death is ambiguous."],
        }
    return {"traded": False, "caveats": []}


def _trade_teams(death: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, str] | None:
    teams = {
        "original_actor_team": _team_side(death, "actor"),
        "original_victim_team": _team_side(death, "victim"),
        "candidate_actor_team": _team_side(candidate, "actor"),
        "candidate_victim_team": _team_side(candidate, "victim"),
    }
    if any(value is None for value in teams.values()):
        return None
    return {key: value for key, value in teams.items() if value is not None}


def _deaths_by_round(deaths: Sequence[Mapping[str, Any]]) -> dict[int, list[Mapping[str, Any]]]:
    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for death in deaths:
        round_number = death.get("round_number")
        if isinstance(round_number, int):
            grouped[round_number].append(death)
    return dict(grouped)


def _players_from_deaths(deaths: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    players: dict[str, Mapping[str, Any]] = {}
    for death in deaths:
        for role in ("actor", "victim"):
            player = _clean_player(death.get(role))
            player_id = _player_key(player)
            if player_id and player_id not in players:
                team_side = _team_side(death, role)
                players[player_id] = {**player, **({"team_side": team_side} if team_side else {})}
    return list(players.values())


def _round_source_event(events: Sequence[Mapping[str, Any]], round_number: int) -> Mapping[str, Any]:
    round_events = [
        event
        for event in events
        if event.get("round_number") == round_number and event.get("event_type") in {"round_timing", "round_summary"}
    ]
    if round_events:
        return max(round_events, key=lambda event: _tick_or_large(event.get("tick")))
    return next(event for event in events if event.get("round_number") == round_number)


def _event(
    event_type: str,
    source_event_name: str,
    source_event: Mapping[str, Any],
    *,
    round_number: Any,
    tick: Any,
    actor: Any = None,
    victim: Any = None,
    context: Mapping[str, Any] | None = None,
    confidence: str,
    caveats: Sequence[str],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    definition = EVENT_METRIC_DICTIONARY[event_type]
    clean_tick = tick if isinstance(tick, int) else None
    return {
        "schema_version": NORMALIZED_EVENT_SCHEMA_VERSION,
        "event_type": event_type,
        "category": definition.category,
        "support": definition.support,
        "source": dict(source_event.get("source") or {}),
        "round_number": round_number if isinstance(round_number, int) else None,
        "tick": clean_tick,
        "time_seconds": round(clean_tick / DEMO_TICK_RATE, 3) if clean_tick is not None else None,
        "actor": _clean_player(actor),
        "victim": _clean_player(victim),
        "context": _clean_mapping(context or {}, keep_none=True),
        "source_event": source_event_name,
        "confidence": confidence,
        "caveats": _ordered_unique([*definition.caveats, *caveats]),
        "payload": _clean_mapping(payload),
    }


def _team_side(event: Mapping[str, Any], role: str) -> str | None:
    context = event.get("context") if isinstance(event.get("context"), Mapping) else {}
    for key in (f"{role}_team_side", f"{role}_team", f"{role}_side"):
        value = context.get(key)
        if value:
            return str(value)
    player = event.get(role)
    if isinstance(player, Mapping) and player.get("team_side"):
        return str(player["team_side"])
    return None


def _player_key(player: Any) -> str | None:
    clean = _clean_player(player)
    if not clean:
        return None
    return clean.get("steamid") or clean.get("name")


def _clean_player(player: Any) -> dict[str, Any] | None:
    if not isinstance(player, Mapping):
        return None
    cleaned = {
        key: str(value)
        for key, value in {
            "name": player.get("name"),
            "steamid": player.get("steamid"),
            "team_side": player.get("team_side"),
        }.items()
        if value is not None
    }
    return cleaned or None


def _source_pointer(event: Mapping[str, Any]) -> dict[str, Any]:
    return _clean_mapping(
        {
            "event_type": event.get("event_type"),
            "round_number": event.get("round_number"),
            "tick": event.get("tick"),
            "actor": event.get("actor"),
            "victim": event.get("victim"),
        }
    )


def _derived_confidence(event: Mapping[str, Any], *, low: bool) -> str:
    if low:
        return "low"
    confidence = event.get("confidence")
    return confidence if confidence in {"high", "medium", "low", "unavailable"} else "unavailable"


def _clean_mapping(value: Mapping[str, Any], *, keep_none: bool = False) -> dict[str, Any]:
    return {str(key): item for key, item in value.items() if keep_none or item is not None}


def _ordered_unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _tick_or_large(value: Any) -> int:
    return value if isinstance(value, int) else 999999999


def _derived_sort_key(event: Mapping[str, Any]) -> tuple[int, int, str, str]:
    return (
        event.get("round_number") if isinstance(event.get("round_number"), int) else 9999,
        event.get("tick") if isinstance(event.get("tick"), int) else 999999999,
        str(event.get("event_type")),
        str((event.get("actor") or {}).get("steamid") if isinstance(event.get("actor"), Mapping) else ""),
    )
