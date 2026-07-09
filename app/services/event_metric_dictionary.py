from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

EventCategory = Literal[
    "round",
    "kill",
    "death",
    "damage",
    "opening_duel",
    "trade",
    "survival",
    "utility",
    "objective",
    "aim",
]
EventSupport = Literal["supported", "weak", "unsupported"]

EVENT_METRIC_DICTIONARY_VERSION = "event-metric-dictionary-v0.10"

V0_10_REQUIRED_EVENT_CATEGORIES: tuple[EventCategory, ...] = (
    "round",
    "kill",
    "death",
    "damage",
    "opening_duel",
    "trade",
    "survival",
    "utility",
)

NORMALIZED_EVENT_SCHEMA: dict[str, str] = {
    "schema_version": "Normalized event schema version.",
    "event_type": "Canonical event type from EVENT_METRIC_DICTIONARY.",
    "category": "High-level CS2 event category.",
    "support": "supported, weak or unsupported from EVENT_METRIC_DICTIONARY.",
    "source": "Parser artifact identity and retained demo handoff reference.",
    "round_number": "Round number when available; null for match-level aggregates.",
    "tick": "Demo tick when available; null for aggregate or source-only facts.",
    "time_seconds": "Demo time in seconds when available; null when unavailable.",
    "actor": "Primary actor object with name/steamid when available; null otherwise.",
    "victim": "Victim/target object with name/steamid when available; null otherwise.",
    "context": "Typed event context that is useful to downstream consumers.",
    "source_event": "Parser event or aggregate that produced the normalized fact.",
    "confidence": "high, medium, low or unavailable.",
    "caveats": "Event caveats inherited from EVENT_METRIC_DICTIONARY and source confidence.",
    "payload": "Event-specific source fields preserved without inventing missing precision.",
}


@dataclass(frozen=True)
class EventMetricDefinition:
    event_type: str
    category: EventCategory
    support: EventSupport
    parser_source_events: tuple[str, ...]
    metric_consumers: tuple[str, ...]
    caveats: tuple[str, ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["parser_source_events"] = list(self.parser_source_events)
        payload["metric_consumers"] = list(self.metric_consumers)
        payload["caveats"] = list(self.caveats)
        return payload


EVENT_METRIC_DICTIONARY: dict[str, EventMetricDefinition] = {
    "round_summary": EventMetricDefinition(
        "round_summary",
        "round",
        "supported",
        ("rounds", "round_end"),
        ("result", "round_score", "kills_per_round", "deaths_per_round"),
        ("Side-specific round attribution remains separate from total score confidence.",),
    ),
    "round_timing": EventMetricDefinition(
        "round_timing",
        "round",
        "supported",
        ("round_start", "round_freeze_end", "round_end"),
        ("early_deaths",),
        ("Early-death timing requires round timing anchors; missing anchors must not fall back to entry deaths.",),
    ),
    "side_team_assignment": EventMetricDefinition(
        "side_team_assignment",
        "round",
        "weak",
        ("player_team", "round_end"),
        ("side_split_metrics",),
        ("Team/side switching inference is low confidence until parser hardening.",),
    ),
    "player_kill": EventMetricDefinition(
        "player_kill",
        "kill",
        "supported",
        ("player_death",),
        ("kills", "assists", "kd_ratio", "kills_per_round", "kast"),
        ("Assist and KAST participation depend on parser event fields and round attribution.",),
    ),
    "player_death": EventMetricDefinition(
        "player_death",
        "death",
        "supported",
        ("player_death",),
        ("deaths", "kd_ratio", "deaths_per_round", "kast", "entry_deaths", "early_deaths"),
        ("Opening and early death labels require source event order and timing anchors.",),
    ),
    "damage": EventMetricDefinition(
        "damage",
        "damage",
        "supported",
        ("player_hurt",),
        ("adr",),
        ("ADR is reliable only when damage events and round counts are both present.",),
    ),
    "weapon_accuracy": EventMetricDefinition(
        "weapon_accuracy",
        "damage",
        "weak",
        ("weapon_fire", "player_hurt"),
        ("accuracy",),
        ("Accuracy is estimated from weapon_fire and player_hurt events, not bullet trajectory.",),
    ),
    "opening_duel": EventMetricDefinition(
        "opening_duel",
        "opening_duel",
        "supported",
        ("player_death",),
        ("entry_kills", "entry_deaths"),
        ("Opening duel detection depends on parser/source event order.",),
    ),
    "trade_kill": EventMetricDefinition(
        "trade_kill",
        "trade",
        "weak",
        ("player_death",),
        ("trade_kills", "kast"),
        ("Trade window and team-side inference are not hard recommendation evidence.",),
    ),
    "round_survival": EventMetricDefinition(
        "round_survival",
        "survival",
        "weak",
        ("player_death", "round_end"),
        ("kast",),
        ("KAST survival can be displayed with caveats; the trade component is incomplete.",),
    ),
    "utility_damage": EventMetricDefinition(
        "utility_damage",
        "utility",
        "supported",
        ("player_hurt", "grenade_events"),
        ("utility_damage",),
        ("Utility attribution depends on parser support for utility weapon names and damage events.",),
    ),
    "flash_effect": EventMetricDefinition(
        "flash_effect",
        "utility",
        "weak",
        ("player_blind", "grenade_events"),
        ("flash_assists", "enemies_flashed"),
        ("Blind duration and kill correlation are best-effort; do not claim exact flash value.",),
    ),
    "grenade_path": EventMetricDefinition(
        "grenade_path",
        "utility",
        "weak",
        ("grenade_trajectories", "grenade_events"),
        ("grenade_rating",),
        ("Trajectory data may be absent; grenade_rating has no stable formula yet.",),
    ),
    "objective_event": EventMetricDefinition(
        "objective_event",
        "objective",
        "weak",
        ("bomb_events",),
        ("swing_score",),
        ("Bomb context is available only as coarse round context, not full strategy evidence.",),
    ),
    "inventory_context": EventMetricDefinition(
        "inventory_context",
        "utility",
        "unsupported",
        ("item_pickup",),
        (),
        ("Item pickup is counted by the parser but has no accepted v0.10 metric consumer.",),
    ),
    "traded_death": EventMetricDefinition(
        "traded_death",
        "trade",
        "unsupported",
        (),
        ("traded_deaths",),
        ("Traded/untraded death facts are unavailable and must remain a data gap.",),
    ),
    "view_angle": EventMetricDefinition(
        "view_angle",
        "aim",
        "unsupported",
        (),
        ("crosshair_placement", "aim_rating"),
        ("View-angle and positioning timelines are not accepted stable parser facts.",),
    ),
}


def event_metric_dictionary_payload() -> dict[str, object]:
    return {
        "version": EVENT_METRIC_DICTIONARY_VERSION,
        "normalized_event_schema": dict(NORMALIZED_EVENT_SCHEMA),
        "events": [definition.to_dict() for definition in EVENT_METRIC_DICTIONARY.values()],
    }


def event_definition(event_type: str) -> EventMetricDefinition | None:
    return EVENT_METRIC_DICTIONARY.get(event_type)


def event_types(*, support: EventSupport | None = None) -> tuple[str, ...]:
    return tuple(
        event_type
        for event_type, definition in EVENT_METRIC_DICTIONARY.items()
        if support is None or definition.support == support
    )


def parser_source_event_names() -> set[str]:
    return {
        source_event
        for definition in EVENT_METRIC_DICTIONARY.values()
        for source_event in definition.parser_source_events
    }
