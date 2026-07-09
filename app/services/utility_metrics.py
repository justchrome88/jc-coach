from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import MetricSnapshot
from app.services.metric_confidence import confidence_record
from app.services.metric_snapshots import upsert_metric_snapshot

UTILITY_METRICS_VERSION = "utility-metrics-v1"
UTILITY_SNAPSHOT_SOURCE = "utility_metrics"

_FLASH_TYPES = {"flashbang"}
_HE_TYPES = {"hegrenade"}
_MOLOTOV_TYPES = {"incendiary", "inferno", "molotov"}
_SMOKE_TYPES = {"smoke", "smokegrenade"}
_SUPPORTED_UTILITY_TYPES = _FLASH_TYPES | _HE_TYPES | _MOLOTOV_TYPES | _SMOKE_TYPES


@dataclass(frozen=True)
class UtilityMetricsResult:
    player_key: str
    player_name: str | None
    player_steamid: str | None
    metrics: dict[str, Any]
    confidence_baseline: dict[str, Any]
    caveats: list[str]
    metadata: dict[str, Any]


def calculate_utility_metrics(
    normalized_events: Iterable[Mapping[str, Any]],
    *,
    players: Sequence[Mapping[str, Any]] | None = None,
) -> list[UtilityMetricsResult]:
    events = [dict(event) for event in normalized_events]
    known_players = _known_players(events, players=players)
    if not known_players:
        return []

    utility_damage_events = [event for event in events if event.get("event_type") == "utility_damage"]
    flash_events = [event for event in events if event.get("event_type") == "flash_effect"]
    detonation_events = [event for event in events if event.get("event_type") == "utility_detonation"]
    data_gap_events = [event for event in events if event.get("event_type") == "utility_data_gap"]
    data_gap_missing = _data_gap_missing_sources(data_gap_events)

    results = []
    for player_key, player in sorted(known_players.items()):
        metrics: dict[str, Any] = {}
        confidence: dict[str, dict[str, Any]] = {}
        caveats = _event_caveats(data_gap_events)

        player_damage_events = [
            event for event in utility_damage_events if _player_key(event.get("actor")) == player_key
        ]
        damage_facts = _deduped_damage_facts(player_damage_events)
        if damage_facts:
            by_type: dict[str, int] = {}
            for fact in damage_facts:
                by_type[fact["utility_type"]] = by_type.get(fact["utility_type"], 0) + fact["damage"]
            metrics["utility_damage"] = sum(by_type.values())
            confidence["utility_damage"] = _confidence(
                "utility_damage",
                player_damage_events,
                fallback="medium",
                reasons=["Utility damage is limited to C05 utility_damage events with positive damage."],
            )
            if by_type.get("hegrenade") is not None:
                metrics["he_damage"] = by_type["hegrenade"]
                confidence["he_damage"] = _confidence(
                    "he_damage",
                    [event for event in player_damage_events if _utility_type(event) == "hegrenade"],
                    fallback="medium",
                    reasons=["HE damage is limited to hegrenade utility_damage events."],
                )
            molotov_damage = sum(value for utility_type, value in by_type.items() if utility_type in _MOLOTOV_TYPES)
            if molotov_damage:
                metrics["molotov_damage"] = molotov_damage
                confidence["molotov_damage"] = _confidence(
                    "molotov_damage",
                    [event for event in player_damage_events if _utility_type(event) in _MOLOTOV_TYPES],
                    fallback="low",
                    reasons=["Molotov damage is parser-attributed utility damage and must remain caveated."],
                )
            caveats.extend(_event_caveats(player_damage_events))
        else:
            confidence["utility_damage"] = _unavailable(
                "utility_damage",
                "No supported utility_damage events for this player; utility damage is omitted instead of set to zero."
            )
            if "utility_damage" in data_gap_missing:
                caveats.append("Utility damage source data is missing; utility damage metrics are unavailable.")

        player_flash_events = [event for event in flash_events if _player_key(event.get("actor")) == player_key]
        enemies_flashed = _enemies_flashed(player_flash_events)
        if enemies_flashed is not None:
            metrics["enemies_flashed"] = enemies_flashed
            confidence["enemies_flashed"] = _confidence(
                "enemies_flashed",
                player_flash_events,
                weak=True,
                reasons=["Flash metrics are weak C05 facts; blind duration and kill impact are not exact value."],
            )
            caveats.extend(_event_caveats(player_flash_events))
        else:
            confidence["enemies_flashed"] = _unavailable(
                "enemies_flashed",
                "No flash_effect events for this player; enemies_flashed is omitted instead of set to zero."
            )

        confidence["flash_assists"] = _unavailable(
            "flash_assists",
            "Flash assists require accepted blind-to-kill correlation; C05 utility events do not support it."
        )
        caveats.append("Flash assists are omitted until accepted blind-to-kill correlation exists.")

        player_detonations = [
            event
            for event in detonation_events
            if _player_key(event.get("actor")) == player_key and _utility_type(event) in _SUPPORTED_UTILITY_TYPES
        ]
        _add_detonation_metric(
            metrics,
            confidence,
            player_detonations,
            metric_id="flash_detonations",
            utility_types=_FLASH_TYPES,
        )
        _add_detonation_metric(
            metrics,
            confidence,
            player_detonations,
            metric_id="smoke_detonations",
            utility_types=_SMOKE_TYPES,
        )
        _add_detonation_metric(
            metrics,
            confidence,
            player_detonations,
            metric_id="he_detonations",
            utility_types=_HE_TYPES,
        )
        _add_detonation_metric(
            metrics,
            confidence,
            player_detonations,
            metric_id="molotov_detonations",
            utility_types=_MOLOTOV_TYPES,
        )
        if player_detonations:
            caveats.extend(_event_caveats(player_detonations))

        confidence["grenade_rating"] = _unavailable(
            "grenade_rating",
            "Grenade rating is unsupported; detonation, damage and flash facts do not define tactical utility value."
        )
        caveats.append("Unsupported grenade_rating is omitted rather than inferred from weak utility events.")

        results.append(
            UtilityMetricsResult(
                player_key=player_key,
                player_name=_clean_text(player.get("name")),
                player_steamid=_clean_text(player.get("steamid")),
                metrics=metrics,
                confidence_baseline={
                    "source": UTILITY_METRICS_VERSION,
                    "confidence": _overall_confidence(confidence, metrics),
                    "metrics": confidence,
                    "event_coverage": {
                        "utility_damage_events": len(utility_damage_events),
                        "flash_effect_events": len(flash_events),
                        "utility_detonation_events": len(detonation_events),
                        "utility_data_gap_events": len(data_gap_events),
                    },
                },
                caveats=_ordered_unique(caveats),
                metadata={
                    "schema_version": UTILITY_METRICS_VERSION,
                    "input_event_schema": _input_schema(events),
                    "event_count": len(events),
                },
            )
        )
    return results


def calculate_and_store_utility_metrics(
    db: Session,
    *,
    match_id: int,
    normalized_events: Iterable[Mapping[str, Any]],
    players: Sequence[Mapping[str, Any]] | None = None,
    source: str = UTILITY_SNAPSHOT_SOURCE,
    source_parser_artifact_id: int | None = None,
    source_event_set_id: str | None = None,
) -> list[MetricSnapshot]:
    results = calculate_utility_metrics(normalized_events, players=players)
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


def _add_detonation_metric(
    metrics: dict[str, Any],
    confidence: dict[str, dict[str, Any]],
    events: Sequence[Mapping[str, Any]],
    *,
    metric_id: str,
    utility_types: set[str],
) -> None:
    matching = [event for event in events if _utility_type(event) in utility_types]
    if not matching:
        confidence[metric_id] = _unavailable(metric_id, f"No {metric_id} source events for this player.")
        return
    metrics[metric_id] = len(matching)
    confidence[metric_id] = _confidence(
        metric_id,
        matching,
        weak=True,
        reasons=["Detonation events prove utility was used, not that it produced tactical value."],
    )


def _deduped_damage_facts(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    player_hurt_keys: set[tuple[Any, ...]] = {
        dedupe_key
        for event in events
        for damage, utility_type, dedupe_key in [_damage_parts(event)]
        if event.get("source_event") == "player_hurt" and damage is not None and damage > 0 and utility_type
    }
    for event in events:
        damage, utility_type, dedupe_key = _damage_parts(event)
        if damage is None or damage <= 0 or utility_type is None:
            continue
        fact = {"damage": damage, "utility_type": utility_type, "source_event": event.get("source_event")}
        if event.get("source_event") == "player_hurt":
            facts.append(fact)
        elif dedupe_key not in player_hurt_keys:
            facts.append(fact)
    return facts


def _damage_parts(event: Mapping[str, Any]) -> tuple[int | None, str | None, tuple[Any, ...]]:
    damage = _damage(event)
    utility_type = _utility_type(event)
    return (
        damage,
        utility_type,
        (
            event.get("round_number"),
            event.get("tick"),
            _player_key(event.get("actor")),
            utility_type,
            damage,
        ),
    )


def _enemies_flashed(events: Sequence[Mapping[str, Any]]) -> int | None:
    player_blind = [event for event in events if event.get("source_event") == "player_blind"]
    if player_blind:
        return len([event for event in player_blind if _player_key(event.get("victim"))])
    flashed_counts = [_flashed_count(event) for event in events]
    flashed_counts = [value for value in flashed_counts if value is not None]
    if flashed_counts:
        return sum(flashed_counts)
    return None


def _known_players(
    events: Sequence[Mapping[str, Any]],
    *,
    players: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Mapping[str, Any]]:
    known: dict[str, Mapping[str, Any]] = {}
    for player in players or []:
        _add_player(known, player)
    for event in events:
        if event.get("category") == "utility":
            _add_player(known, event.get("actor"))
            _add_player(known, event.get("victim"))
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


def _confidence(
    metric_id: str,
    events: Sequence[Mapping[str, Any]],
    *,
    fallback: str = "medium",
    weak: bool = False,
    reasons: Sequence[str] = (),
) -> dict[str, Any]:
    values = [str(event.get("confidence")) for event in events if event.get("confidence")]
    if weak:
        level = "low"
    elif not values:
        level = fallback
    elif "low" in values or "unavailable" in values:
        level = "low"
    elif "medium" in values:
        level = "medium"
    else:
        level = "high"
    return confidence_record(
        metric_id,
        level,
        reasons=reasons,
        reason_codes=[
            f"event_confidence_{level}",
            "weak_event_support" if weak else "normalized_event_source",
        ],
        source_trust={
            "event_confidence": level,
            "event_count": len(events),
            "source_kinds": _source_kinds(events),
        },
    )


def _unavailable(metric_id: str, reason: str) -> dict[str, Any]:
    return confidence_record(
        metric_id,
        "unavailable",
        reasons=[reason],
        reason_codes=["source_data_unavailable"],
    )


def _data_gap_missing_sources(events: Sequence[Mapping[str, Any]]) -> set[str]:
    missing: set[str] = set()
    for event in events:
        context = event.get("context")
        values = context.get("missing_sources") if isinstance(context, Mapping) else None
        if isinstance(values, Sequence) and not isinstance(values, str):
            missing.update(str(value) for value in values)
    return missing


def _event_caveats(events: Sequence[Mapping[str, Any]]) -> list[str]:
    caveats: list[str] = []
    for event in events:
        values = event.get("caveats")
        if isinstance(values, Sequence) and not isinstance(values, str):
            caveats.extend(str(value) for value in values if value)
    return _ordered_unique(caveats)


def _source_kinds(events: Sequence[Mapping[str, Any]]) -> list[str]:
    kinds: set[str] = set()
    for event in events:
        source = event.get("source")
        if isinstance(source, Mapping) and source.get("kind"):
            kinds.add(str(source["kind"]))
    return sorted(kinds)


def _damage(event: Mapping[str, Any]) -> int | None:
    context = event.get("context")
    value = None
    if isinstance(context, Mapping):
        value = context.get("damage_health")
        if value is None:
            value = context.get("damage")
    if isinstance(value, bool) or value is None:
        return None
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return None


def _flashed_count(event: Mapping[str, Any]) -> int | None:
    context = event.get("context")
    value = context.get("flashed_count") if isinstance(context, Mapping) else None
    if isinstance(value, bool) or value is None:
        return None
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return None


def _utility_type(event: Mapping[str, Any]) -> str | None:
    context = event.get("context")
    if not isinstance(context, Mapping):
        return None
    value = _clean_text(context.get("utility_type") or context.get("grenade_type"))
    return value.lower() if value else None


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
