from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.services.event_metric_dictionary import EVENT_METRIC_DICTIONARY, event_definition
from app.services.parser_evidence import CONFIDENCE_LEVELS

NORMALIZED_EVENT_SCHEMA_VERSION = "normalized-parser-events-v1"
SUPPORTED_ARTIFACT_READER_INPUTS = {
    "parser_artifact_json": "JSON artifact containing the current parser payload or DemoParseArtifact fields.",
    "parser_handoff_with_artifact": "Retained .dem parser handoff path plus an existing parser artifact JSON.",
}


class ParserArtifactReaderError(ValueError):
    def __init__(self, issues: list[str]):
        super().__init__("Parser artifact reader failed: " + ", ".join(issues))
        self.issues = issues


class NormalizedEventValidationError(ValueError):
    def __init__(self, issues: list[str]):
        super().__init__("Normalized event failed validation: " + ", ".join(issues))
        self.issues = issues


def read_normalized_events(
    input_path: str | Path,
    *,
    parser_artifact_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Read normalized events from an artifact path or a retained demo handoff plus artifact path.

    A raw .dem handoff path is accepted only as the source boundary. This reader does not invoke the
    parser; callers must provide an existing parser artifact when the input path is a retained demo.
    """
    path = Path(input_path)
    if parser_artifact_path is not None:
        return read_normalized_events_from_artifact_file(parser_artifact_path, parser_handoff_path=path)
    if path.suffix.lower() != ".json":
        raise ParserArtifactReaderError(["parser_artifact_required_for_raw_demo_handoff"])
    return read_normalized_events_from_artifact_file(path)


def read_normalized_events_from_artifact_file(
    artifact_path: str | Path,
    *,
    parser_handoff_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    try:
        artifact = json.loads(Path(artifact_path).read_text())
    except json.JSONDecodeError as exc:
        raise ParserArtifactReaderError(["invalid_artifact_json"]) from exc
    return normalized_events_from_parser_artifact(artifact, parser_handoff_path=parser_handoff_path)


def normalized_events_from_parser_artifact(
    artifact: Any,
    *,
    parser_handoff_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    document = _artifact_document(artifact)
    payload = document["payload"]
    deep = payload.get("deep")
    if not isinstance(deep, Mapping):
        raise ParserArtifactReaderError(["missing_deep_payload"])

    source = _source_descriptor(document, payload, parser_handoff_path)
    confidence = _confidence_descriptor(document, payload)
    events: list[dict[str, Any]] = []

    events.extend(_raw_round_boundary_events(deep, source, confidence))
    events.extend(_raw_player_death_events(deep, source, confidence))
    events.extend(_raw_player_hurt_events(deep, source, confidence))
    events.extend(_raw_player_blind_events(deep, source, confidence))
    events.extend(_round_events(deep, source, confidence))
    events.extend(_duel_events(deep, source, confidence))
    events.extend(_damage_events(deep, source, confidence))
    events.extend(_blind_events(deep, source, confidence))
    events.extend(_grenade_events(deep, source, confidence))
    events.extend(_utility_data_gap_events(deep, source, confidence))
    events.extend(_weapon_accuracy_events(deep, source, confidence))
    events.extend(_survival_events(deep, source, confidence))

    return [validate_normalized_event(event) for event in sorted(events, key=_event_sort_key)]


def validate_normalized_event(event: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    required_fields = {
        "schema_version",
        "event_type",
        "category",
        "support",
        "source",
        "round_number",
        "tick",
        "time_seconds",
        "actor",
        "victim",
        "context",
        "source_event",
        "confidence",
        "caveats",
        "payload",
    }
    missing = sorted(required_fields.difference(event))
    issues.extend(f"missing_{field}" for field in missing)

    event_type = event.get("event_type")
    definition = event_definition(str(event_type)) if isinstance(event_type, str) else None
    if definition is None:
        issues.append("unknown_event_type")
    else:
        if event.get("category") != definition.category:
            issues.append("category_mismatch")
        if event.get("support") != definition.support:
            issues.append("support_mismatch")
        source_event = event.get("source_event")
        if definition.parser_source_events and source_event not in definition.parser_source_events:
            issues.append("source_event_mismatch")

    if event.get("schema_version") != NORMALIZED_EVENT_SCHEMA_VERSION:
        issues.append("unsupported_schema_version")
    if event.get("confidence") not in CONFIDENCE_LEVELS:
        issues.append("invalid_confidence")
    for field in ("source", "context", "payload"):
        if field in event and not isinstance(event.get(field), Mapping):
            issues.append(f"invalid_{field}")
    for field in ("actor", "victim"):
        value = event.get(field)
        if value is not None and not isinstance(value, Mapping):
            issues.append(f"invalid_{field}")
    for field in ("round_number", "tick"):
        value = event.get(field)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            issues.append(f"invalid_{field}")
    time_seconds = event.get("time_seconds")
    if time_seconds is not None and (
        isinstance(time_seconds, bool) or not isinstance(time_seconds, int | float) or time_seconds < 0
    ):
        issues.append("invalid_time_seconds")
    caveats = event.get("caveats")
    if not isinstance(caveats, list) or any(not isinstance(item, str) or not item.strip() for item in caveats):
        issues.append("invalid_caveats")

    if issues:
        raise NormalizedEventValidationError(_ordered_unique(issues))
    return dict(event)


def _artifact_document(artifact: Any) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        artifact = _artifact_from_object(artifact)
    if not isinstance(artifact, Mapping):
        raise ParserArtifactReaderError(["artifact_must_be_object"])

    if isinstance(artifact.get("payload_json"), str):
        payload = _json_object(artifact["payload_json"], "invalid_payload_json")
        return {**dict(artifact), "payload": payload}

    payload = artifact.get("payload")
    if isinstance(payload, Mapping) and ("deep" in payload or "match" in payload):
        return {**dict(artifact), "payload": dict(payload)}
    if "deep" in artifact or "match" in artifact:
        return {"payload": dict(artifact)}

    raise ParserArtifactReaderError(["missing_parser_payload"])


def _artifact_from_object(artifact: Any) -> dict[str, Any] | None:
    if not hasattr(artifact, "payload_json"):
        return None
    return {
        "parser_name": getattr(artifact, "parser_name", None),
        "parser_version": getattr(artifact, "parser_version", None),
        "payload_version": getattr(artifact, "payload_version", None),
        "status": getattr(artifact, "status", None),
        "source_demo_file": getattr(artifact, "source_demo_file", None),
        "demo_sha1": getattr(artifact, "demo_sha1", None),
        "event_counts_json": getattr(artifact, "event_counts_json", None),
        "confidence_json": getattr(artifact, "confidence_json", None),
        "data_gaps_json": getattr(artifact, "data_gaps_json", None),
        "payload_json": getattr(artifact, "payload_json", None),
    }


def _json_object(raw: str, issue: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ParserArtifactReaderError([issue]) from exc
    if not isinstance(value, dict):
        raise ParserArtifactReaderError([issue])
    return value


def _source_descriptor(
    document: Mapping[str, Any],
    payload: Mapping[str, Any],
    parser_handoff_path: str | Path | None,
) -> dict[str, Any]:
    handoff_path = str(parser_handoff_path) if parser_handoff_path is not None else None
    source_demo_file = (
        handoff_path
        or _string_or_none(document.get("source_demo_file"))
        or _string_or_none(payload.get("file"))
        or _string_or_none((payload.get("parser_handoff") or {}).get("path"))
    )
    artifact_source_demo_file = _string_or_none(document.get("source_demo_file")) or _string_or_none(
        payload.get("file")
    )
    if handoff_path and artifact_source_demo_file and handoff_path != artifact_source_demo_file:
        raise ParserArtifactReaderError(["parser_handoff_path_mismatch"])
    return {
        "kind": "parser_artifact",
        "parser_name": _string_or_none(document.get("parser_name")) or _string_or_none(payload.get("parser")),
        "parser_version": _string_or_none(document.get("parser_version"))
        or _string_or_none(payload.get("parser_version")),
        "payload_version": _string_or_none(document.get("payload_version"))
        or _string_or_none(payload.get("payload_version")),
        "source_demo_file": source_demo_file,
        "demo_sha1": _string_or_none(document.get("demo_sha1")) or _string_or_none(payload.get("demo_sha1")),
    }


def _confidence_descriptor(document: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    confidence_json = document.get("confidence_json")
    persisted = _json_object(confidence_json, "invalid_confidence_json") if isinstance(confidence_json, str) else {}
    metric_confidence = (
        persisted.get("metric_confidence") if isinstance(persisted.get("metric_confidence"), dict) else None
    )
    return {
        "parser_confidence": _confidence_or_unavailable(
            persisted.get("parser_confidence") or payload.get("parser_confidence")
        ),
        "metric_confidence": metric_confidence or _dict_or_empty(payload.get("metric_confidence")),
    }


def _round_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for row in _rows(deep, "rounds"):
        round_number = _int_or_none(row.get("round_number"))
        events.append(
            _event(
                "round_summary",
                "rounds",
                source,
                confidence,
                round_number=round_number,
                tick=_int_or_none(row.get("end_tick")),
                context={
                    "winner_side": row.get("winner_side"),
                    "end_reason": row.get("end_reason"),
                    "start_tick": _int_or_none(row.get("start_tick")),
                    "freeze_end_tick": _int_or_none(row.get("freeze_end_tick")),
                    "end_tick": _int_or_none(row.get("end_tick")),
                },
                payload=row,
            )
        )
        if any(row.get(field) is not None for field in ("start_tick", "freeze_end_tick", "end_tick")):
            events.append(
                _event(
                    "round_timing",
                    "round_end",
                    source,
                    confidence,
                    round_number=round_number,
                    tick=_int_or_none(row.get("end_tick") or row.get("freeze_end_tick") or row.get("start_tick")),
                    context={
                        "start_tick": _int_or_none(row.get("start_tick")),
                        "freeze_end_tick": _int_or_none(row.get("freeze_end_tick")),
                        "end_tick": _int_or_none(row.get("end_tick")),
                    },
                    payload=row,
                )
            )
        if any(row.get(field) is not None for field in ("bomb_planted_tick", "bomb_site", "bomb_outcome")):
            events.append(
                _event(
                    "objective_event",
                    "bomb_events",
                    source,
                    confidence,
                    round_number=round_number,
                    tick=_int_or_none(row.get("bomb_planted_tick") or row.get("end_tick")),
                    context={
                        "bomb_site": row.get("bomb_site"),
                        "bomb_outcome": row.get("bomb_outcome"),
                    },
                    payload=row,
                )
            )
    return events


def _duel_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for row in _rows(deep, "duels"):
        actor = _player(row, "attacker")
        victim = _player(row, "victim")
        context = {
            "weapon": row.get("weapon"),
            "headshot": bool(row.get("headshot")),
            "assister": _player(row, "assister"),
            "distance": row.get("distance"),
        }
        for event_type in ("player_kill", "player_death"):
            events.append(
                _event(
                    event_type,
                    "player_death",
                    source,
                    confidence,
                    round_number=_int_or_none(row.get("round_number")),
                    tick=_int_or_none(row.get("tick")),
                    actor=actor,
                    victim=victim,
                    context=context,
                    payload=row,
                )
            )
        if row.get("opening_duel"):
            events.append(
                _event(
                    "opening_duel",
                    "player_death",
                    source,
                    confidence,
                    round_number=_int_or_none(row.get("round_number")),
                    tick=_int_or_none(row.get("tick")),
                    actor=actor,
                    victim=victim,
                    context=context,
                    payload=row,
                )
            )
        if row.get("trade_kill"):
            events.append(
                _event(
                    "trade_kill",
                    "player_death",
                    source,
                    confidence,
                    round_number=_int_or_none(row.get("round_number")),
                    tick=_int_or_none(row.get("tick")),
                    actor=actor,
                    victim=victim,
                    context=context,
                    payload=row,
                )
            )
    return events


def _damage_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        _event(
            "damage",
            "player_hurt",
            source,
            confidence,
            round_number=_int_or_none(row.get("round_number")),
            tick=_int_or_none(row.get("tick")),
            actor=_player(row, "attacker"),
            victim=_player(row, "victim"),
            context={
                "weapon": row.get("weapon"),
                "hitgroup": row.get("hitgroup"),
                "damage_health": _int_or_none(row.get("damage_health")),
                "damage_armor": _int_or_none(row.get("damage_armor")),
                "victim_health_after": _int_or_none(row.get("victim_health_after")),
            },
            payload=row,
        )
        for row in _rows(deep, "damage_events")
    ]


def _grenade_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for row in _rows(deep, "grenade_events"):
        context = {
            "grenade_type": row.get("grenade_type"),
            "utility_type": _utility_type(row.get("grenade_type") or row.get("event_type")),
            "parser_event_type": row.get("event_type"),
            "entity_id": row.get("entity_id") or row.get("entityid"),
            "flashed_count": _int_or_none(row.get("flashed_count")),
            "damage": _int_or_none(row.get("damage")),
            "position": _position(row),
        }
        events.append(
            _grenade_event(
                "utility_detonation",
                row,
                source,
                confidence,
                context,
                caveats=["Utility detonation does not prove damage, flash value or lineup quality."],
            )
        )
        if _int_or_none(row.get("flashed_count")):
            events.append(_grenade_event("flash_effect", row, source, confidence, context))
        if _int_or_none(row.get("damage")):
            events.append(_grenade_event("utility_damage", row, source, confidence, context))
        if _position(row):
            events.append(_grenade_event("grenade_path", row, source, confidence, context))
    return events


def _utility_data_gap_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    grenade_rows = _rows(deep, "grenade_events")
    blind_rows = [
        *_rows(deep, "blind_events"),
        *[row for row, _ in _raw_rows(deep, ("player_blind_events", "player_blind"), {})],
    ]
    trajectory_rows = _rows(deep, "grenade_trajectories")
    utility_damage_rows = [
        row
        for row in [
            *_rows(deep, "damage_events"),
            *[row for row, _ in _raw_rows(deep, ("player_hurt_events", "player_hurt"), {})],
        ]
        if _utility_type(row.get("weapon"))
        and (_int_or_none(row.get("damage_health") or row.get("dmg_health")) or 0) > 0
    ]
    missing_sources = []
    if not grenade_rows:
        missing_sources.append("grenade_events")
    if not blind_rows:
        missing_sources.append("player_blind")
    if not trajectory_rows:
        missing_sources.append("grenade_trajectories")
    if not utility_damage_rows and not any((_int_or_none(row.get("damage")) or 0) > 0 for row in grenade_rows):
        missing_sources.append("utility_damage")

    if not missing_sources:
        return []

    data_gaps = deep.get("data_gaps") if isinstance(deep.get("data_gaps"), list) else []
    return [
        _event(
            "utility_data_gap",
            "data_gaps",
            source,
            confidence,
            context={
                "missing_sources": missing_sources,
                "available_sources": {
                    "grenade_events": bool(grenade_rows),
                    "player_blind": bool(blind_rows),
                    "grenade_trajectories": bool(trajectory_rows),
                    "utility_damage": bool(utility_damage_rows)
                    or any((_int_or_none(row.get("damage")) or 0) > 0 for row in grenade_rows),
                },
                "unsupported_metrics": ["grenade_rating"],
            },
            payload={"data_gaps": data_gaps},
            caveats=[
                "Unsupported utility metrics are represented as a data gap, not as inferred performance.",
                "Downstream coach and metrics layers must not infer grenade quality from missing utility data.",
            ],
        )
    ]


def _weapon_accuracy_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for row in _rows(deep, "weapon_stats"):
        if _int_or_none(row.get("shots")) is None:
            continue
        events.append(
            _event(
                "weapon_accuracy",
                "weapon_fire",
                source,
                confidence,
                actor={"name": row.get("player_name"), "steamid": row.get("player_steamid")},
                context={
                    "weapon": row.get("weapon"),
                    "shots": _int_or_none(row.get("shots")),
                    "hits": _int_or_none(row.get("hits")),
                    "accuracy": row.get("accuracy"),
                    "headshot_percent": row.get("headshot_percent"),
                },
                payload=row,
            )
        )
    return events


def _survival_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for row in _rows(deep, "player_rounds"):
        survived = row.get("survived")
        if survived is None:
            continue
        events.append(
            _event(
                "round_survival",
                "round_end",
                source,
                confidence,
                round_number=_int_or_none(row.get("round_number")),
                actor={"name": row.get("player_name"), "steamid": row.get("player_steamid")},
                context={
                    "team_side": row.get("team_side"),
                    "survived": bool(survived),
                    "kast": bool(row.get("kast")),
                },
                payload=row,
            )
        )
    return events


def _raw_round_boundary_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows = _raw_rows(
        deep,
        ("round_boundaries",),
        {
            "round_start_events": "round_start",
            "round_freeze_end_events": "round_freeze_end",
            "round_end_events": "round_end",
        },
    )
    events = []
    for row, fallback_source_event in rows:
        source_event = _round_boundary_source_event(row, fallback_source_event)
        round_number = _int_or_none(row.get("round_number") or row.get("round") or row.get("total_rounds_played"))
        tick = _int_or_none(row.get("tick"))
        events.append(
            _event(
                "round_timing",
                source_event,
                source,
                confidence,
                round_number=round_number,
                tick=tick,
                context={
                    "boundary": source_event,
                    "winner_side": row.get("winner_side") or row.get("winner"),
                    "end_reason": row.get("end_reason") or row.get("reason"),
                },
                payload=row,
                caveats=_availability_caveats(round_number=round_number, tick=tick),
            )
        )
    return events


def _raw_player_death_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for row, _source_event in _raw_rows(deep, ("player_death_events", "player_death"), {}):
        actor = _player_from_fields(row, ("attacker_name", "attacker"), ("attacker_steamid",))
        victim = _player_from_fields(row, ("victim_name", "user_name", "user"), ("victim_steamid", "user_steamid"))
        round_number = _int_or_none(row.get("round_number") or row.get("round") or row.get("total_rounds_played"))
        tick = _int_or_none(row.get("tick"))
        context = {
            "weapon": row.get("weapon"),
            "headshot": bool(row.get("headshot")),
            "assister": _player_from_fields(row, ("assister_name", "assister"), ("assister_steamid",)),
            "attacker_blind": _bool_or_none(row.get("attackerblind") or row.get("attacker_blind")),
            "through_smoke": _bool_or_none(row.get("thrusmoke") or row.get("through_smoke")),
            "noscope": _bool_or_none(row.get("noscope")),
            "penetrated": _int_or_none(row.get("penetrated")),
            "hitgroup": row.get("hitgroup"),
        }
        caveats = _availability_caveats(round_number=round_number, tick=tick, actor=actor, victim=victim)
        for event_type in ("player_kill", "player_death"):
            events.append(
                _event(
                    event_type,
                    "player_death",
                    source,
                    confidence,
                    round_number=round_number,
                    tick=tick,
                    actor=actor,
                    victim=victim,
                    context=context,
                    payload=row,
                    caveats=caveats,
                )
            )
    return events


def _raw_player_hurt_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for row, _source_event in _raw_rows(deep, ("player_hurt_events", "player_hurt"), {}):
        actor = _player_from_fields(row, ("attacker_name", "attacker"), ("attacker_steamid",))
        victim = _player_from_fields(row, ("victim_name", "user_name", "user"), ("victim_steamid", "user_steamid"))
        round_number = _int_or_none(row.get("round_number") or row.get("round") or row.get("total_rounds_played"))
        tick = _int_or_none(row.get("tick"))
        damage_health = _int_or_none(row.get("damage_health") or row.get("dmg_health") or row.get("health_damage"))
        damage_armor = _int_or_none(row.get("damage_armor") or row.get("dmg_armor"))
        context = {
            "weapon": row.get("weapon"),
            "hitgroup": row.get("hitgroup"),
            "damage_health": damage_health,
            "damage_armor": damage_armor,
            "victim_health_after": _int_or_none(row.get("victim_health_after") or row.get("health")),
            "victim_armor_after": _int_or_none(row.get("victim_armor_after") or row.get("armor")),
        }
        caveats = [
            *_availability_caveats(round_number=round_number, tick=tick, actor=actor, victim=victim),
            *(
                ["Source row omitted health damage; ADR consumers must ignore this row."]
                if damage_health is None
                else []
            ),
        ]
        events.append(
            _event(
                "damage",
                "player_hurt",
                source,
                confidence,
                round_number=round_number,
                tick=tick,
                actor=actor,
                victim=victim,
                context=context,
                payload=row,
                caveats=caveats,
            )
        )
        utility_type = _utility_type(row.get("weapon"))
        if utility_type and damage_health is not None and damage_health > 0:
            events.append(
                _event(
                    "utility_damage",
                    "player_hurt",
                    source,
                    confidence,
                    round_number=round_number,
                    tick=tick,
                    actor=actor,
                    victim=victim,
                    context={**context, "utility_type": utility_type},
                    payload=row,
                    caveats=[
                        *caveats,
                        "Utility damage is inferred from parser weapon name on player_hurt.",
                    ],
                )
            )
    return events


def _raw_player_blind_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for row, _source_event in _raw_rows(deep, ("player_blind_events", "player_blind"), {}):
        actor = _player_from_fields(row, ("attacker_name", "attacker"), ("attacker_steamid",))
        victim = _player_from_fields(row, ("victim_name", "user_name", "user"), ("victim_steamid", "user_steamid"))
        round_number = _int_or_none(row.get("round_number") or row.get("round") or row.get("total_rounds_played"))
        tick = _int_or_none(row.get("tick"))
        blind_duration = _float_or_none(row.get("blind_duration"))
        events.append(
            _event(
                "flash_effect",
                "player_blind",
                source,
                confidence,
                round_number=round_number,
                tick=tick,
                actor=actor,
                victim=victim,
                context={
                    "utility_type": "flashbang",
                    "blind_duration": blind_duration,
                    "entity_id": row.get("entity_id") or row.get("entityid"),
                },
                payload=row,
                caveats=[
                    *_availability_caveats(round_number=round_number, tick=tick, actor=actor, victim=victim),
                    *(
                        ["Source row omitted blind duration; flash value must remain low-confidence."]
                        if blind_duration is None
                        else []
                    ),
                ],
            )
        )
    return events


def _blind_events(
    deep: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    events = []
    for row in _rows(deep, "blind_events"):
        actor = _player(row, "attacker")
        victim = _player(row, "victim")
        round_number = _int_or_none(row.get("round_number"))
        tick = _int_or_none(row.get("tick"))
        blind_duration = _float_or_none(row.get("blind_duration"))
        events.append(
            _event(
                "flash_effect",
                "player_blind",
                source,
                confidence,
                round_number=round_number,
                tick=tick,
                actor=actor,
                victim=victim,
                context={
                    "utility_type": "flashbang",
                    "blind_duration": blind_duration,
                    "entity_id": row.get("entity_id") or row.get("entityid"),
                },
                payload=row,
                caveats=[
                    *_availability_caveats(round_number=round_number, tick=tick, actor=actor, victim=victim),
                    *(
                        ["Source row omitted blind duration; flash value must remain low-confidence."]
                        if blind_duration is None
                        else []
                    ),
                ],
            )
        )
    return events


def _grenade_event(
    event_type: str,
    row: Mapping[str, Any],
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    return _event(
        event_type,
        "grenade_events",
        source,
        confidence,
        round_number=_int_or_none(row.get("round_number")),
        tick=_int_or_none(row.get("tick")),
        actor={"name": row.get("player_name"), "steamid": row.get("player_steamid")},
        context=context,
        payload=row,
        caveats=caveats,
    )


def _event(
    event_type: str,
    source_event: str,
    source: Mapping[str, Any],
    confidence: Mapping[str, Any],
    *,
    round_number: int | None = None,
    tick: int | None = None,
    actor: Mapping[str, Any] | None = None,
    victim: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    definition = EVENT_METRIC_DICTIONARY[event_type]
    return {
        "schema_version": NORMALIZED_EVENT_SCHEMA_VERSION,
        "event_type": event_type,
        "category": definition.category,
        "support": definition.support,
        "source": dict(source),
        "round_number": round_number,
        "tick": tick,
        "time_seconds": _seconds_from_tick(tick),
        "actor": _clean_player(actor),
        "victim": _clean_player(victim),
        "context": _clean_mapping(context or {}),
        "source_event": source_event,
        "confidence": _event_confidence(event_type, confidence),
        "caveats": _ordered_unique([*definition.caveats, *(caveats or [])]),
        "payload": _clean_mapping(payload or {}),
    }


def _event_confidence(event_type: str, confidence: Mapping[str, Any]) -> str:
    if EVENT_METRIC_DICTIONARY[event_type].support == "unsupported":
        return "low"
    metric_key = {
        "round_summary": None,
        "round_timing": "early_deaths",
        "player_kill": "kills",
        "player_death": "deaths",
        "damage": "adr",
        "weapon_accuracy": "weapon_accuracy",
        "opening_duel": "entry_duels",
        "trade_kill": "trade_kills",
        "round_survival": "kast",
        "utility_damage": "utility",
        "flash_effect": "flash",
        "utility_detonation": "grenades",
        "grenade_path": "utility",
        "objective_event": "swing",
    }.get(event_type)
    metric_confidence = confidence.get("metric_confidence")
    if metric_key and isinstance(metric_confidence, Mapping):
        return _confidence_or_unavailable(metric_confidence.get(metric_key))
    return _confidence_or_unavailable(confidence.get("parser_confidence"))


def _rows(deep: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    rows = deep.get(key) or []
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise ParserArtifactReaderError([f"invalid_deep_{key}"])
    return rows


def _raw_rows(
    deep: Mapping[str, Any],
    direct_keys: tuple[str, ...],
    keyed_sources: Mapping[str, str],
) -> list[tuple[Mapping[str, Any], str | None]]:
    rows = []
    for key in direct_keys:
        rows.extend((row, None) for row in _rows(deep, key))
    for key, source_event in keyed_sources.items():
        rows.extend((row, source_event) for row in _rows(deep, key))
    return rows


def _round_boundary_source_event(row: Mapping[str, Any], fallback: str | None) -> str:
    raw = str(row.get("source_event") or row.get("event_name") or row.get("event_type") or fallback or "").lower()
    if raw in {"round_start", "start"}:
        return "round_start"
    if raw in {"round_freeze_end", "freeze_end", "freezetime_end"}:
        return "round_freeze_end"
    return "round_end"


def _player(row: Mapping[str, Any], prefix: str) -> dict[str, Any] | None:
    player = {
        "name": row.get(f"{prefix}_name"),
        "steamid": row.get(f"{prefix}_steamid"),
    }
    return _clean_player(player)


def _player_from_fields(
    row: Mapping[str, Any],
    name_fields: tuple[str, ...],
    steamid_fields: tuple[str, ...],
) -> dict[str, Any] | None:
    return _clean_player(
        {
            "name": _first_present(row, name_fields),
            "steamid": _first_present(row, steamid_fields),
        }
    )


def _clean_player(player: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not player:
        return None
    cleaned = {
        key: str(value)
        for key, value in {"name": player.get("name"), "steamid": player.get("steamid")}.items()
        if value is not None
    }
    return cleaned or None


def _clean_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in value.items() if item is not None}


def _position(row: Mapping[str, Any]) -> dict[str, float] | None:
    position = {axis: _float_or_none(row.get(axis)) for axis in ("x", "y", "z")}
    if any(value is None for value in position.values()):
        return None
    return {axis: float(value) for axis, value in position.items() if value is not None}


def _event_sort_key(event: Mapping[str, Any]) -> tuple[int, int, str]:
    return (
        event.get("round_number") if isinstance(event.get("round_number"), int) else 9999,
        event.get("tick") if isinstance(event.get("tick"), int) else 999999999,
        str(event.get("event_type")),
    )


def _seconds_from_tick(tick: int | None) -> float | None:
    if tick is None:
        return None
    return round(tick / 64, 3)


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _first_present(row: Mapping[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        value = row.get(field)
        if value not in (None, ""):
            return value
    return None


def _utility_type(value: Any) -> str | None:
    text = str(value or "").lower()
    if "flash" in text:
        return "flashbang"
    if "smoke" in text:
        return "smoke"
    if "hegrenade" in text or text == "he":
        return "hegrenade"
    if "molotov" in text:
        return "molotov"
    if "incgrenade" in text or "inferno" in text:
        return "incendiary"
    if "decoy" in text:
        return "decoy"
    return None


def _availability_caveats(
    *,
    round_number: int | None,
    tick: int | None,
    actor: Mapping[str, Any] | None = None,
    victim: Mapping[str, Any] | None = None,
) -> list[str]:
    caveats = []
    if round_number is None:
        caveats.append("Source row omitted round number; round attribution is unavailable.")
    if tick is None:
        caveats.append("Source row omitted tick; time_seconds is unavailable.")
    if actor is None:
        caveats.append("Source row omitted actor identity; actor metrics must ignore this row.")
    elif not actor.get("steamid"):
        caveats.append("Source row omitted actor steamid; player joins may require name fallback.")
    if victim is None:
        caveats.append("Source row omitted victim identity; victim metrics must ignore this row.")
    elif not victim.get("steamid"):
        caveats.append("Source row omitted victim steamid; player joins may require name fallback.")
    return caveats


def _confidence_or_unavailable(value: Any) -> str:
    return str(value) if value in CONFIDENCE_LEVELS else "unavailable"


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
