from __future__ import annotations

import hashlib
import importlib.metadata
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import (
    DemoDamageEvent,
    DemoDuel,
    DemoGrenadeEvent,
    DemoParseArtifact,
    DemoPlayerRound,
    DemoRound,
    DemoWeaponStat,
    Match,
)
from app.services.demo_retention import (
    ARTIFACT_CATEGORY_PARSER_ARTIFACT,
    ARTIFACT_CATEGORY_RAW_DEMO,
    artifact_retention_metadata,
    retention_metadata,
)
from app.services.demo_storage import store_demo_file
from app.services.recommendation_tracking import (
    compact_recommendation_evaluations,
    ensure_default_recommendation,
    evaluate_recommendations_for_match,
    recommendation_evaluation_metadata,
)
from app.services.steam_match_metadata import apply_steam_metadata_to_parsed_demo

PARSER_PAYLOAD_VERSION = "2026-07-02.1"
EARLY_DEATH_WINDOW_TICKS = 64 * 30
GRENADE_EVENTS = (
    "flashbang_detonate",
    "smokegrenade_detonate",
    "hegrenade_detonate",
    "inferno_startburn",
    "molotov_detonate",
    "decoy_detonate",
)
BOMB_EVENTS = ("bomb_planted", "bomb_defused", "bomb_exploded", "bomb_beginplant", "bomb_begindefuse")
MATCH_COLUMN_NAMES = frozenset(column.name for column in Match.__table__.columns)


class DemoParseError(RuntimeError):
    def __init__(self, message: str, retention: dict[str, Any] | None = None):
        super().__init__(message)
        self.retention = retention or {}


def list_inbox_demos() -> list[dict[str, Any]]:
    inbox = Path(get_settings().demo_inbox_dir)
    files = []
    for path in sorted(inbox.glob("*.dem"), key=lambda item: item.stat().st_mtime, reverse=True):
        stat = path.stat()
        files.append(
            {
                "name": path.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            }
        )
    return files


def import_inbox_demo(
    db: Session,
    filename: str,
    player_identifier: str | None = None,
) -> dict[str, Any]:
    path = _resolve_inbox_demo(filename)
    return import_demo_file(
        db,
        path,
        original_filename=path.name,
        player_identifier=player_identifier,
    )


def import_demo_file(
    db: Session,
    source_path: Path,
    original_filename: str | None = None,
    player_identifier: str | None = None,
    steam_metadata: dict[str, Any] | None = None,
    acquisition_metadata: dict[str, Any] | None = None,
    storage_budget: Any | None = None,
    evaluate_recommendations: bool = True,
) -> dict[str, Any]:
    stored = _store_demo(source_path, original_filename, storage_budget=storage_budget)
    stored_path = Path(stored["path"])
    try:
        parsed = parse_demo(stored_path, player_identifier=player_identifier)
    except DemoParseError as exc:
        exc.retention = retention_metadata(raw_demo_path=stored_path, parser_success=False)
        exc.retention["storage"] = stored
        raise
    if steam_metadata:
        apply_steam_metadata_to_parsed_demo(parsed, steam_metadata)
    storage_metadata = _storage_metadata(stored, acquisition_metadata=acquisition_metadata)
    parsed["file"] = storage_metadata["parser_handoff_path"]
    parsed["demo_sha1"] = storage_metadata["sha1"]
    parsed["storage"] = storage_metadata
    parsed["parser_handoff"] = {
        "kind": "raw_demo_file",
        "path": storage_metadata["parser_handoff_path"],
        "sha1": storage_metadata["sha1"],
        "retention": artifact_retention_metadata(
            ARTIFACT_CATEGORY_RAW_DEMO,
            path=storage_metadata["parser_handoff_path"],
        ),
    }
    retention = retention_metadata(raw_demo_path=stored_path, parser_success=True)
    parsed.update(retention)
    parsed["demo_retention"] = retention
    storage_links = storage_metadata["links"]
    match_data = parsed["match"]
    match_data["demo_file"] = str(stored_path)
    match_data["source"] = "demo"
    match_data["raw_json"] = json.dumps(parsed, ensure_ascii=False, default=str)
    match_model_data = _match_model_kwargs(match_data)
    match_model_data["user_id"] = _int_or_none(storage_links.get("user_id"))
    match_model_data["steam_account_id"] = _int_or_none(storage_links.get("steam_account_id"))
    match_model_data["import_job_id"] = _int_or_none(storage_links.get("import_job_id"))

    existing = db.scalar(
        select(Match).where(
            Match.source == match_model_data["source"],
            Match.external_match_id == match_model_data["external_match_id"],
        )
    )
    if existing:
        existing.played_at = match_model_data["played_at"]
        existing.raw_json = match_model_data["raw_json"]
        existing.demo_file = existing.demo_file or str(stored_path)
        existing.user_id = existing.user_id or match_model_data["user_id"]
        existing.steam_account_id = existing.steam_account_id or match_model_data["steam_account_id"]
        existing.import_job_id = existing.import_job_id or match_model_data["import_job_id"]
        db.commit()
        db.refresh(existing)
        _save_demo_parse_artifacts(db, existing, parsed)
        duplicate_retention = retention_metadata(raw_demo_path=existing.demo_file, parser_success=True)
        evaluation_metadata = recommendation_evaluation_metadata(
            status="duplicate",
            match_id=existing.id,
            reason="demo_already_imported",
        )
        return {
            "imported": 0,
            "skipped_duplicates": 1,
            "errors": 0,
            "match_id": existing.id,
            "recommendation_evaluations": evaluation_metadata["evaluations"],
            "recommendation_evaluation": evaluation_metadata,
            "player": parsed["player"],
            "stored_path": existing.demo_file,
            "match": parsed["match"],
            "available_players": parsed["available_players"],
            "event_counts": parsed["event_counts"],
            "metric_confidence": parsed["metric_confidence"],
            "parser_confidence": parsed["parser_confidence"],
            "warnings": parsed["warnings"],
            "storage": storage_metadata,
            "parser_handoff": parsed["parser_handoff"],
            **duplicate_retention,
            "message": "Demo already imported.",
        }

    match = Match(**match_model_data)
    db.add(match)
    db.commit()
    db.refresh(match)
    _save_demo_parse_artifacts(db, match, parsed)
    recommendation_evaluations = []
    if evaluate_recommendations:
        ensure_default_recommendation(db)
        recommendation_evaluations = evaluate_recommendations_for_match(db, match.id)
        evaluation_status = "created" if recommendation_evaluations else "not_eligible"
        evaluation_reason = None if recommendation_evaluations else "no_eligible_recommendation_or_match"
    else:
        evaluation_status = "deferred"
        evaluation_reason = "steam_date_truth_pending"
    evaluation_metadata = recommendation_evaluation_metadata(
        recommendation_evaluations,
        status=evaluation_status,
        match_id=match.id,
        reason=evaluation_reason,
    )
    return {
        "imported": 1,
        "skipped_duplicates": 0,
        "errors": 0,
        "match_id": match.id,
        "recommendation_evaluations": compact_recommendation_evaluations(recommendation_evaluations),
        "recommendation_evaluation": evaluation_metadata,
        "player": parsed["player"],
        "stored_path": str(stored_path),
        "match": parsed["match"],
        "available_players": parsed["available_players"],
        "event_counts": parsed["event_counts"],
        "metric_confidence": parsed["metric_confidence"],
        "parser_confidence": parsed["parser_confidence"],
        "warnings": parsed["warnings"],
        "storage": storage_metadata,
        "parser_handoff": parsed["parser_handoff"],
        **retention,
        "message": parsed["message"],
    }


def _match_model_kwargs(match_data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in match_data.items() if key in MATCH_COLUMN_NAMES}


def _resolve_inbox_demo(filename: str) -> Path:
    inbox = Path(get_settings().demo_inbox_dir).resolve()
    candidate = (inbox / Path(filename).name).resolve()
    if not candidate.is_file() or candidate.suffix.lower() != ".dem":
        raise DemoParseError(f"Demo `{filename}` was not found in inbox.")
    if inbox not in candidate.parents:
        raise DemoParseError("Invalid demo path.")
    return candidate


def parse_demo(path: Path, player_identifier: str | None = None) -> dict[str, Any]:
    try:
        from demoparser2 import DemoParser
    except ImportError as exc:
        raise DemoParseError("demoparser2 is not installed. Run `pip install -e .` and try again.") from exc

    try:
        parser = DemoParser(str(path))
        header = _safe_call(parser.parse_header, default={})
        player_info = _safe_call(parser.parse_player_info, default=[])
        death_events = _safe_event(parser, "player_death")
        hurt_events = _safe_event(parser, "player_hurt")
        round_end_events = _safe_event(parser, "round_end")
        player_team_events = _safe_event(parser, "player_team")
        round_start_events = _safe_optional_event(parser, "round_start")
        round_freeze_end_events = _safe_optional_event(parser, "round_freeze_end")
        weapon_fire_events = _safe_optional_event(parser, "weapon_fire")
        blind_events = _safe_optional_event(parser, "player_blind")
        item_pickup_events = _safe_optional_event(parser, "item_pickup")
        grenade_events = {event_name: _safe_optional_event(parser, event_name) for event_name in GRENADE_EVENTS}
        bomb_events = {event_name: _safe_optional_event(parser, event_name) for event_name in BOMB_EVENTS}
        grenade_trajectories = _safe_grenade_trajectories(parser, round_end_events)
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise DemoParseError(f"Could not parse .dem file with demoparser2: {exc}") from exc

    if not _records(death_events) and not _records(hurt_events):
        raise DemoParseError("Demo parsed, but no kill/damage events were found.")

    player = _select_player(death_events, hurt_events, player_info, player_identifier)
    stats = _player_stats(player, death_events, hurt_events)
    early_deaths = _early_deaths_from_timing(player, death_events, round_start_events, round_freeze_end_events)
    swing_summary = _swing_summary(
        player,
        player_info,
        death_events,
        hurt_events,
        blind_events,
        bomb_events,
        round_end_events,
    )
    deep_payload = _deep_parse_payload(
        player=player,
        player_info=player_info,
        death_events=death_events,
        hurt_events=hurt_events,
        round_start_events=round_start_events,
        round_freeze_end_events=round_freeze_end_events,
        round_end_events=round_end_events,
        weapon_fire_events=weapon_fire_events,
        blind_events=blind_events,
        item_pickup_events=item_pickup_events,
        grenade_events=grenade_events,
        bomb_events=bomb_events,
        grenade_trajectories=grenade_trajectories,
    )
    score = _score_for_player(player, player_info, player_team_events, round_end_events)
    rounds_count = _rounds_count(death_events, hurt_events)
    event_counts = {
        "player_info": len(_records(player_info)),
        "player_death": len(_records(death_events)),
        "player_hurt": len(_records(hurt_events)),
        "round_end": len(_records(round_end_events)),
        "player_team": len(_records(player_team_events)),
        "round_start": len(_records(round_start_events)),
        "round_freeze_end": len(_records(round_freeze_end_events)),
        "weapon_fire": len(_records(weapon_fire_events)),
        "player_blind": len(_records(blind_events)),
        "item_pickup": len(_records(item_pickup_events)),
        "bomb_events": sum(len(_records(rows)) for rows in bomb_events.values()),
        "grenade_events": sum(len(_records(rows)) for rows in grenade_events.values()),
        "grenade_trajectories": len(grenade_trajectories),
        "rounds": rounds_count,
    }
    adr = round(stats["damage"] / rounds_count, 2) if rounds_count else None
    map_name = _header_value(header, ("map_name", "map", "mapName"))
    header_played_at = _header_datetime(header)
    played_at_source = "demo_header" if header_played_at else "file_modified_fallback"
    played_at = header_played_at or datetime.fromtimestamp(path.stat().st_mtime, UTC).replace(tzinfo=None)
    external_id = _demo_external_id(path, player, stats)
    match = {
        "source": "demo",
        "external_match_id": external_id,
        "played_at": played_at,
        "map_name": map_name,
        "mode": "demo",
        "result": score["result"],
        "rounds_for": score["rounds_for"],
        "rounds_against": score["rounds_against"],
        "kills": stats["kills"],
        "deaths": stats["deaths"],
        "assists": stats["assists"],
        "kd": round(stats["kills"] / (stats["deaths"] or 1), 2),
        "adr": adr,
        "kast": stats["kast"],
        "rating": None,
        "swing_score": swing_summary["score"],
        "headshot_percent": round(stats["headshots"] / stats["kills"] * 100, 2) if stats["kills"] else 0,
        "entry_kills": stats["entry_kills"],
        "entry_deaths": stats["entry_deaths"],
        "early_deaths": early_deaths,
        "flash_assists": stats["flash_assists"],
        "utility_damage": stats["utility_damage"],
        "enemies_flashed": stats["enemies_flashed"],
        "clutches_won": None,
        "clutches_lost": None,
        "side_t_rounds_won": None,
        "side_t_rounds_lost": None,
        "side_ct_rounds_won": None,
        "side_ct_rounds_lost": None,
    }
    metric_confidence = _metric_confidence(event_counts, score, stats, adr, early_deaths)
    warnings = _parser_warnings(metric_confidence)
    return {
        "status": "parsed",
        "parser": "demoparser2",
        "parser_version": _parser_version(),
        "payload_version": PARSER_PAYLOAD_VERSION,
        "file": str(path),
        "demo_sha1": _file_sha1(path),
        "played_at": played_at.isoformat() if played_at else None,
        "played_at_source": played_at_source,
        "player": player,
        "match": match,
        "aim_summary": stats["aim_summary"],
        "weapon_breakdown": stats["weapon_breakdown"],
        "swing_summary": swing_summary,
        "deep": deep_payload,
        "aim_data_gaps": _aim_data_gaps(),
        "header": _jsonable(header),
        "event_counts": event_counts,
        "metric_confidence": metric_confidence,
        "parser_confidence": _overall_confidence(metric_confidence),
        "warnings": warnings,
        "available_players": _available_players(player_info, death_events, hurt_events),
        "message": "Demo imported with parser confidence metadata.",
    }


def _metric_confidence(
    event_counts: dict[str, int],
    score: dict[str, Any],
    stats: dict[str, Any],
    adr: float | None,
    early_deaths: int | None,
) -> dict[str, str]:
    confidence = {
        "kills_deaths_assists": "high" if event_counts["player_death"] else "low",
        "adr": "high" if adr is not None and event_counts["player_hurt"] and event_counts["rounds"] else "low",
        "entry_duels": "medium" if event_counts["player_death"] else "low",
        "kast": "medium" if stats.get("kast") is not None and event_counts["player_death"] else "low",
        "kast_trade_component": "low",
        "trade_kills": "low" if event_counts["player_death"] else "unavailable",
        "traded_deaths": "unavailable",
        "utility": "medium" if event_counts["player_hurt"] else "low",
        "flash": "medium" if event_counts.get("player_blind") else "low",
        "weapon_accuracy": "medium" if event_counts.get("weapon_fire") and event_counts.get("player_hurt") else "low",
        "grenades": "high" if event_counts.get("grenade_events") and event_counts.get("player_blind") else "medium"
        if event_counts.get("grenade_events")
        else "low",
        "bomb_round_context": "high" if event_counts.get("bomb_events") and event_counts.get("round_end") else "medium"
        if event_counts.get("round_end")
        else "low",
        "swing": "medium" if event_counts.get("player_death") and event_counts.get("round_end") else "low",
        "score": "medium" if score.get("rounds_for") is not None and event_counts["round_end"] else "low",
        "side_stats": "low",
        "early_deaths": "medium" if early_deaths is not None else "low",
    }
    if event_counts["player_team"] and score.get("rounds_for") is not None:
        confidence["score"] = "high"
    return confidence


def _overall_confidence(metric_confidence: dict[str, str]) -> str:
    weights = {"high": 2, "medium": 1, "low": 0}
    score = sum(weights.get(value, 0) for value in metric_confidence.values())
    maximum = len(metric_confidence) * 2
    ratio = score / maximum if maximum else 0
    if ratio >= 0.72:
        return "high"
    if ratio >= 0.42:
        return "medium"
    return "low"


def _parser_warnings(metric_confidence: dict[str, str]) -> list[str]:
    warnings = []
    if metric_confidence.get("score") != "high":
        warnings.append("Score/result are best-effort until more demos validate side switching.")
    if metric_confidence.get("early_deaths") == "low":
        warnings.append("Early deaths are unavailable unless round timing anchors are parsed.")
    if metric_confidence.get("kast_trade_component") == "low":
        warnings.append("KAST trade component is incomplete; KAST is best-effort.")
    if metric_confidence.get("traded_deaths") == "unavailable":
        warnings.append("Traded/untraded death facts are not available yet.")
    if metric_confidence.get("side_stats") == "low":
        warnings.append("T/CT side stats are not reliable yet.")
    if metric_confidence.get("utility") != "high" or metric_confidence.get("flash") != "high":
        warnings.append("Utility and flash metrics are best-effort because demo event fields vary.")
    if metric_confidence.get("weapon_accuracy") != "medium":
        warnings.append("Weapon accuracy requires both weapon_fire and damage events.")
    return warnings


def _safe_call(func, default):
    try:
        return func()
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return default


def _safe_event(parser, event_name: str):
    try:
        return parser.parse_event(event_name, other=["total_rounds_played"])
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        try:
            return parser.parse_event(event_name)
        except BaseException as fallback_exc:
            if isinstance(fallback_exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise DemoParseError(f"Could not read `{event_name}` from demo: {fallback_exc}") from fallback_exc


def _safe_optional_event(parser, event_name: str):
    try:
        return parser.parse_event(event_name, other=["total_rounds_played"])
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return []


def _safe_grenade_trajectories(parser, round_end_events) -> list[dict[str, Any]]:
    try:
        trajectories = parser.parse_grenades()
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return []
    records = _records(trajectories)
    if not records:
        return []
    round_by_tick = _round_by_tick_index(round_end_events)
    grouped: dict[Any, dict[str, Any]] = {}
    for row in records:
        entity_id = _first_present(row, ("grenade_entity_id", "entityid"))
        if entity_id is None:
            continue
        item = grouped.setdefault(
            entity_id,
            {
                "entity_id": entity_id,
                "grenade_type": row.get("grenade_type"),
                "player_name": row.get("name") or row.get("user_name"),
                "player_steamid": _string_or_none(row.get("steamid") or row.get("user_steamid")),
                "start_tick": None,
                "end_tick": None,
                "start_position": None,
                "end_position": None,
                "max_z": None,
                "sample_count": 0,
                "round_number": None,
            },
        )
        tick = _tick(row)
        position = _position(row)
        item["sample_count"] += 1
        if item["start_tick"] is None or tick < item["start_tick"]:
            item["start_tick"] = tick
            item["start_position"] = position
            item["round_number"] = _round_for_tick(tick, round_by_tick)
        if item["end_tick"] is None or tick > item["end_tick"]:
            item["end_tick"] = tick
            item["end_position"] = position
        z = _float_or_none(row.get("z"))
        if z is not None and (item["max_z"] is None or z > item["max_z"]):
            item["max_z"] = z
    return list(grouped.values())


def _store_demo(source_path: Path, original_filename: str | None, storage_budget: Any | None = None) -> dict[str, Any]:
    return store_demo_file(source_path, original_filename, storage_budget=storage_budget)


def _storage_metadata(
    stored: dict[str, Any],
    *,
    acquisition_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    links = dict(acquisition_metadata or {})
    return {
        "schema_version": stored["storage_schema_version"],
        "kind": stored["storage_kind"],
        "status": stored["storage_status"],
        "path": stored["path"],
        "relative_path": stored["relative_path"],
        "parser_handoff_path": stored["parser_handoff_path"],
        "sha1": stored["sha1"],
        "size_bytes": stored["size_bytes"],
        "original_filename": stored["original_filename"],
        "retention": stored["retention"],
        "temporary_source": stored["temporary_source"],
        "links": {
            "import_job_id": links.get("import_job_id"),
            "source_match_id": links.get("source_match_id"),
            "source_match_external_id": links.get("source_match_external_id"),
            "share_code": links.get("share_code"),
            "user_id": links.get("user_id"),
            "steam_account_id": links.get("steam_account_id"),
            "steam_id": links.get("steam_id"),
        },
    }


def _select_player(deaths, hurts, player_info, identifier: str | None) -> dict[str, str | None]:
    candidates = _available_players(player_info, deaths, hurts)
    if not candidates:
        raise DemoParseError("Could not identify players in demo.")
    configured = (identifier or get_settings().demo_player_identifier or "").strip().lower()
    if configured:
        for candidate in candidates:
            name = (candidate.get("name") or "").lower()
            steamid = str(candidate.get("steamid") or "").lower()
            if configured == name or configured == steamid or configured in name:
                return candidate
        raise DemoParseError(f"Player `{identifier}` was not found in demo. Available: {candidates[:10]}")
    jc_candidate = next((candidate for candidate in candidates if (candidate.get("name") or "").lower() == "jc"), None)
    if jc_candidate:
        return jc_candidate
    return max(candidates, key=lambda item: item.get("activity", 0) or 0)


def _available_players(player_info, deaths, hurts) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for row in _records(player_info):
        name = _first_present(row, ("name", "player_name", "Name"))
        steamid = _first_present(row, ("steamid", "steam_id", "xuid", "SteamID"))
        if name or steamid:
            key = str(steamid or name)
            by_key[key] = {"name": name, "steamid": str(steamid) if steamid else None, "activity": 0}

    activity = Counter()
    for row in _records(deaths):
        for field in ("attacker_name", "attacker", "assister_name", "assister", "user_name", "user"):
            value = row.get(field)
            if value:
                activity[str(value)] += 1
    for row in _records(hurts):
        for field in ("attacker_name", "attacker", "user_name", "user"):
            value = row.get(field)
            if value:
                activity[str(value)] += 1

    for name, count in activity.items():
        match = next((item for item in by_key.values() if item.get("name") == name), None)
        if match:
            match["activity"] += count
        else:
            by_key[name] = {"name": name, "steamid": None, "activity": count}
    return sorted(by_key.values(), key=lambda item: item.get("activity", 0), reverse=True)


def _player_stats(player: dict[str, str | None], deaths, hurts) -> dict[str, Any]:
    player_name = player.get("name")
    player_steamid = player.get("steamid")
    kills = deaths_count = assists = headshots = flash_assists = 0
    damage = utility_damage = enemies_flashed = 0
    round_kill = defaultdict(bool)
    round_death = defaultdict(bool)
    round_assist = defaultdict(bool)
    kills_by_round: Counter[Any] = Counter()
    first_death_by_round: dict[Any, dict[str, Any]] = {}
    weapon_breakdown: dict[str, dict[str, Any]] = {}

    for row in _records(deaths):
        round_id = _round_id(row)
        weapon = _weapon(row)
        attacker_match = _matches_player(
            row,
            player_name,
            player_steamid,
            ("attacker_name", "attacker_steamid", "attacker"),
        )
        victim_match = _matches_player(row, player_name, player_steamid, ("user_name", "user_steamid", "user"))
        assister_match = _matches_player(
            row,
            player_name,
            player_steamid,
            ("assister_name", "assister_steamid", "assister"),
        )
        if attacker_match and not victim_match:
            kills += 1
            kills_by_round[round_id] += 1
            round_kill[round_id] = True
            weapon_breakdown.setdefault(weapon, _empty_weapon(weapon))["kills"] += 1
            if bool(row.get("headshot")):
                headshots += 1
                weapon_breakdown.setdefault(weapon, _empty_weapon(weapon))["headshots"] += 1
        if victim_match:
            deaths_count += 1
            round_death[round_id] = True
            weapon_breakdown.setdefault(weapon, _empty_weapon(weapon))["deaths"] += 1
        if assister_match:
            assists += 1
            round_assist[round_id] = True
        if bool(row.get("assistedflash")) and assister_match:
            flash_assists += 1
        tick = _tick(row)
        current_first = first_death_by_round.get(round_id)
        if current_first is None or tick < current_first["tick"]:
            first_death_by_round[round_id] = {
                "tick": tick,
                "attacker_match": attacker_match and not victim_match,
                "victim_match": victim_match,
            }

    for row in _records(hurts):
        if not _matches_player(row, player_name, player_steamid, ("attacker_name", "attacker_steamid", "attacker")):
            continue
        amount = int(float(row.get("dmg_health") or row.get("health_damage") or row.get("damage") or 0))
        damage += max(0, amount)
        weapon = _weapon(row)
        weapon_breakdown.setdefault(weapon, _empty_weapon(weapon))["damage"] += max(0, amount)
        if any(part in weapon for part in ("hegrenade", "inferno", "molotov", "incgrenade", "flashbang", "smoke")):
            utility_damage += max(0, amount)
        if "flash" in weapon:
            enemies_flashed += 1

    entry_kills = sum(1 for item in first_death_by_round.values() if item["attacker_match"])
    entry_deaths = sum(1 for item in first_death_by_round.values() if item["victim_match"])
    rounds = set(round_kill) | set(round_death) | set(round_assist)
    kast_rounds = sum(
        1 for round_id in rounds if round_kill[round_id] or round_assist[round_id] or not round_death[round_id]
    )
    kast = round(kast_rounds / len(rounds) * 100, 2) if rounds else None
    multi_kill_rounds = sum(1 for count in kills_by_round.values() if count >= 2)
    for weapon_stats in weapon_breakdown.values():
        weapon_stats["headshot_percent"] = (
            round(weapon_stats["headshots"] / weapon_stats["kills"] * 100, 2) if weapon_stats["kills"] else None
        )
    return {
        "kills": kills,
        "deaths": deaths_count,
        "assists": assists,
        "headshots": headshots,
        "damage": damage,
        "utility_damage": utility_damage,
        "enemies_flashed": enemies_flashed,
        "flash_assists": flash_assists,
        "entry_kills": entry_kills,
        "entry_deaths": entry_deaths,
        "kast": kast,
        "aim_summary": {
            "damage_per_death": round(damage / deaths_count, 2) if deaths_count else damage,
            "opening_duel_success": round(entry_kills / (entry_kills + entry_deaths) * 100, 2)
            if entry_kills + entry_deaths
            else None,
            "multi_kill_rounds": multi_kill_rounds,
        },
        "weapon_breakdown": weapon_breakdown,
    }


def _early_deaths_from_timing(
    player: dict[str, str | None],
    death_events,
    round_start_events,
    round_freeze_end_events,
) -> int | None:
    anchors = _round_anchor_ticks(round_freeze_end_events) or _round_anchor_ticks(round_start_events)
    if not anchors:
        return None
    player_name = player.get("name")
    player_steamid = player.get("steamid")
    early_deaths = 0
    for row in _records(death_events):
        if not _matches_player(row, player_name, player_steamid, ("user_name", "user_steamid", "user")):
            continue
        tick = _tick_or_none(row)
        anchor = anchors.get(_round_number(row))
        if tick is None or anchor is None:
            continue
        if anchor <= tick <= anchor + EARLY_DEATH_WINDOW_TICKS:
            early_deaths += 1
    return early_deaths


def _round_anchor_ticks(events) -> dict[int, int]:
    anchors = {}
    for row in _records(events):
        tick = _tick_or_none(row)
        if tick is None:
            continue
        anchors.setdefault(_round_number(row), tick)
    return anchors


def _weapon(row: dict[str, Any]) -> str:
    weapon = str(row.get("weapon") or row.get("weapon_name") or row.get("attacker_weapon") or "unknown").lower()
    return weapon or "unknown"


def _empty_weapon(weapon: str) -> dict[str, Any]:
    return {"weapon": weapon, "kills": 0, "headshots": 0, "deaths": 0, "damage": 0, "headshot_percent": None}


def _aim_data_gaps() -> list[str]:
    return [
        "accuracy is estimated from weapon_fire and player_hurt events, not bullet trajectory",
        "first_bullet_accuracy requires shot timeline",
        "spray_control requires bullet trajectory data",
        "ttk requires precise damage/death timing",
        "crosshair_placement requires view angles and position timeline",
    ]


def _deep_parse_payload(
    *,
    player: dict[str, str | None],
    player_info,
    death_events,
    hurt_events,
    round_start_events,
    round_freeze_end_events,
    round_end_events,
    weapon_fire_events,
    blind_events,
    item_pickup_events,
    grenade_events: dict[str, Any],
    bomb_events: dict[str, Any],
    grenade_trajectories: list[dict[str, Any]],
) -> dict[str, Any]:
    players = _player_lookup(player_info, death_events, hurt_events, weapon_fire_events, blind_events)
    rounds = _round_summaries(round_start_events, round_freeze_end_events, round_end_events, bomb_events)
    duels = _duel_events(death_events)
    damage_events = _damage_events(hurt_events)
    blind_rows = _blind_events(blind_events)
    grenade_rows = _grenade_event_rows(grenade_events, hurt_events, blind_events)
    weapon_stats = _weapon_stats(death_events, hurt_events, weapon_fire_events)
    player_rounds = _player_rounds(players, death_events, hurt_events, blind_events)
    economy = _economy_summary(item_pickup_events)
    target_key = _player_key(player.get("steamid"), player.get("name"))
    return {
        "players": list(players.values()),
        "target_player_key": target_key,
        "rounds": rounds,
        "player_rounds": player_rounds,
        "duels": duels,
        "damage_events": damage_events,
        "blind_events": blind_rows,
        "grenade_events": grenade_rows,
        "grenade_trajectories": grenade_trajectories,
        "weapon_stats": weapon_stats,
        "economy_summary": economy,
        "target_player_summary": _target_player_summary(target_key, player_rounds, weapon_stats, duels, damage_events),
        "data_gaps": _deep_data_gaps(weapon_fire_events, grenade_trajectories),
    }


def _player_lookup(*event_sets) -> dict[str, dict[str, Any]]:
    players: dict[str, dict[str, Any]] = {}

    def add(name: Any, steamid: Any) -> None:
        steam = _string_or_none(steamid)
        player_name = str(name) if name not in (None, "") else None
        if not steam and not player_name:
            return
        key = _player_key(steam, player_name)
        item = players.setdefault(key, {"key": key, "name": player_name, "steamid": steam, "activity": 0})
        if player_name and not item.get("name"):
            item["name"] = player_name
        if steam and not item.get("steamid"):
            item["steamid"] = steam
        item["activity"] += 1

    for rows in event_sets:
        for row in _records(rows):
            add(
                _first_present(row, ("name", "player_name", "user_name", "user")),
                _first_present(row, ("steamid", "user_steamid")),
            )
            add(row.get("attacker_name"), row.get("attacker_steamid"))
            add(row.get("assister_name"), row.get("assister_steamid"))
    return players


def _round_summaries(
    round_start_events,
    round_freeze_end_events,
    round_end_events,
    bomb_events,
) -> list[dict[str, Any]]:
    rounds: dict[int, dict[str, Any]] = defaultdict(lambda: {"bomb_events": []})
    for row in _records(round_start_events):
        number = _round_number(row)
        rounds[number]["round_number"] = number
        rounds[number]["start_tick"] = _tick_or_none(row)
    for row in _records(round_freeze_end_events):
        number = _round_number(row)
        rounds[number]["round_number"] = number
        rounds[number]["freeze_end_tick"] = _tick_or_none(row)
    for row in _records(round_end_events):
        number = _round_number(row)
        rounds[number]["round_number"] = number
        rounds[number]["end_tick"] = _tick_or_none(row)
        rounds[number]["winner_side"] = row.get("winner")
        rounds[number]["end_reason"] = row.get("reason")
        rounds[number]["raw_round_end"] = _compact_row(row)
    for event_name, rows in bomb_events.items():
        for row in _records(rows):
            number = _round_number(row)
            event = {
                "event_type": event_name,
                "tick": _tick_or_none(row),
                "player_name": row.get("user_name") or row.get("user"),
                "player_steamid": _string_or_none(row.get("user_steamid")),
                "site": _bomb_site(row.get("site")),
                "raw": _compact_row(row),
            }
            rounds[number]["round_number"] = number
            rounds[number]["bomb_events"].append(event)
            if event_name == "bomb_planted":
                rounds[number]["bomb_planted_tick"] = event["tick"]
                rounds[number]["bomb_site"] = event["site"]
            if event_name in {"bomb_defused", "bomb_exploded"}:
                rounds[number]["bomb_outcome"] = event_name.removeprefix("bomb_")
    return [rounds[key] for key in sorted(rounds)]


def _duel_events(death_events) -> list[dict[str, Any]]:
    rows = sorted(_records(death_events), key=lambda row: (_round_number(row), _tick(row)))
    first_tick_by_round: dict[int, int] = {}
    last_death_by_victim_side: dict[tuple[int, str | None], dict[str, Any]] = {}
    duels = []
    for row in rows:
        round_number = _round_number(row)
        tick = _tick_or_none(row)
        if tick is not None and round_number not in first_tick_by_round:
            first_tick_by_round[round_number] = tick
        attacker_key = _player_key(row.get("attacker_steamid"), row.get("attacker_name") or row.get("attacker"))
        victim_key = _player_key(row.get("user_steamid"), row.get("user_name") or row.get("user"))
        trade_key = (round_number, attacker_key)
        previous = last_death_by_victim_side.get(trade_key)
        trade_kill = bool(
            previous and tick is not None and previous.get("tick") is not None and tick - previous["tick"] <= 640
        )
        item = {
            "round_number": round_number,
            "tick": tick,
            "attacker_name": row.get("attacker_name") or row.get("attacker"),
            "attacker_steamid": _string_or_none(row.get("attacker_steamid")),
            "victim_name": row.get("user_name") or row.get("user"),
            "victim_steamid": _string_or_none(row.get("user_steamid")),
            "assister_name": row.get("assister_name") or row.get("assister"),
            "assister_steamid": _string_or_none(row.get("assister_steamid")),
            "weapon": _weapon(row),
            "headshot": bool(row.get("headshot")),
            "opening_duel": tick == first_tick_by_round.get(round_number),
            "trade_kill": trade_kill,
            "distance": _float_or_none(row.get("distance")),
            "attacker_blind": bool(row.get("attackerblind")),
            "through_smoke": bool(row.get("thrusmoke")),
            "noscope": bool(row.get("noscope")),
            "penetrated": _int_or_zero(row.get("penetrated")),
            "hitgroup": row.get("hitgroup"),
            "raw": _compact_row(row),
        }
        duels.append(item)
        last_death_by_victim_side[(round_number, victim_key)] = item
    return duels


def _damage_events(hurt_events) -> list[dict[str, Any]]:
    events = []
    for row in _records(hurt_events):
        events.append(
            {
                "round_number": _round_number(row),
                "tick": _tick_or_none(row),
                "attacker_name": row.get("attacker_name") or row.get("attacker"),
                "attacker_steamid": _string_or_none(row.get("attacker_steamid")),
                "victim_name": row.get("user_name") or row.get("user"),
                "victim_steamid": _string_or_none(row.get("user_steamid")),
                "weapon": _weapon(row),
                "hitgroup": row.get("hitgroup"),
                "damage_health": _int_or_zero(row.get("dmg_health") or row.get("health_damage") or row.get("damage")),
                "damage_armor": _int_or_zero(row.get("dmg_armor")),
                "victim_health_after": _int_or_none(row.get("health")),
                "victim_armor_after": _int_or_none(row.get("armor")),
                "raw": _compact_row(row),
            }
        )
    return events


def _blind_events(blind_events) -> list[dict[str, Any]]:
    rows = []
    for row in _records(blind_events):
        rows.append(
            {
                "round_number": _round_number(row),
                "tick": _tick_or_none(row),
                "attacker_name": row.get("attacker_name"),
                "attacker_steamid": _string_or_none(row.get("attacker_steamid")),
                "victim_name": row.get("user_name") or row.get("user"),
                "victim_steamid": _string_or_none(row.get("user_steamid")),
                "blind_duration": _float_or_none(row.get("blind_duration")),
                "entity_id": _first_present(row, ("entityid", "entity_id")),
                "raw": _compact_row(row),
            }
        )
    return rows


def _grenade_event_rows(grenade_events: dict[str, Any], hurt_events, blind_events) -> list[dict[str, Any]]:
    flashed_by_entity = Counter()
    for row in _records(blind_events):
        entity_id = _first_present(row, ("entityid", "entity_id"))
        if entity_id is not None:
            flashed_by_entity[entity_id] += 1
    damage_by_round_player_weapon = Counter()
    for row in _records(hurt_events):
        weapon = _weapon(row)
        if _is_utility_weapon(weapon):
            damage_by_round_player_weapon[(_round_number(row), row.get("attacker_steamid"), weapon)] += _int_or_zero(
                row.get("dmg_health") or row.get("health_damage") or row.get("damage")
            )
    rows = []
    for event_name, event_rows in grenade_events.items():
        for row in _records(event_rows):
            weapon = _grenade_weapon(event_name)
            entity_id = _first_present(row, ("entityid", "entity_id"))
            rows.append(
                {
                    "round_number": _round_number(row),
                    "tick": _tick_or_none(row),
                    "event_type": event_name,
                    "grenade_type": weapon,
                    "player_name": row.get("user_name") or row.get("user"),
                    "player_steamid": _string_or_none(row.get("user_steamid")),
                    "x": _float_or_none(row.get("x")),
                    "y": _float_or_none(row.get("y")),
                    "z": _float_or_none(row.get("z")),
                    "flashed_count": int(flashed_by_entity.get(entity_id, 0)),
                    "damage": int(
                        damage_by_round_player_weapon.get((_round_number(row), row.get("user_steamid"), weapon), 0)
                    ),
                    "entity_id": entity_id,
                    "raw": _compact_row(row),
                }
            )
    return rows


def _weapon_stats(death_events, hurt_events, weapon_fire_events) -> list[dict[str, Any]]:
    stats: dict[tuple[str, str], dict[str, Any]] = {}

    def bucket(name: Any, steamid: Any, weapon: Any) -> dict[str, Any]:
        player_key = _player_key(steamid, name)
        weapon_name = str(weapon or "unknown").lower()
        item = stats.setdefault(
            (player_key, weapon_name),
            {
                "player_key": player_key,
                "player_name": str(name) if name not in (None, "") else None,
                "player_steamid": _string_or_none(steamid),
                "weapon": weapon_name,
                "shots": 0,
                "hits": 0,
                "kills": 0,
                "deaths": 0,
                "damage": 0,
                "headshots": 0,
            },
        )
        return item

    for row in _records(weapon_fire_events):
        bucket(row.get("user_name") or row.get("user"), row.get("user_steamid"), _weapon(row))["shots"] += 1
    for row in _records(hurt_events):
        item = bucket(row.get("attacker_name") or row.get("attacker"), row.get("attacker_steamid"), _weapon(row))
        item["hits"] += 1
        item["damage"] += _int_or_zero(row.get("dmg_health") or row.get("health_damage") or row.get("damage"))
    for row in _records(death_events):
        attacker = bucket(row.get("attacker_name") or row.get("attacker"), row.get("attacker_steamid"), _weapon(row))
        attacker["kills"] += 1
        if bool(row.get("headshot")):
            attacker["headshots"] += 1
        bucket(row.get("user_name") or row.get("user"), row.get("user_steamid"), _weapon(row))["deaths"] += 1
    for item in stats.values():
        item["accuracy"] = round(item["hits"] / item["shots"] * 100, 2) if item["shots"] else None
        item["headshot_percent"] = round(item["headshots"] / item["kills"] * 100, 2) if item["kills"] else None
    return sorted(stats.values(), key=lambda item: (item["player_name"] or "", item["weapon"]))


def _player_rounds(players, death_events, hurt_events, blind_events) -> list[dict[str, Any]]:
    rounds: dict[tuple[int, str], dict[str, Any]] = {}

    def bucket(round_number: int, name: Any, steamid: Any) -> dict[str, Any]:
        key = _player_key(steamid, name)
        player = players.get(key, {"name": name, "steamid": _string_or_none(steamid)})
        item = rounds.setdefault(
            (round_number, key),
            {
                "round_number": round_number,
                "player_key": key,
                "player_name": player.get("name"),
                "player_steamid": player.get("steamid"),
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "damage": 0,
                "utility_damage": 0,
                "headshots": 0,
                "flash_assists": 0,
                "enemies_flashed": 0,
                "opening_kill": 0,
                "opening_death": 0,
                "survived": 1,
                "kast": 0,
            },
        )
        return item

    first_deaths = {}
    for row in sorted(_records(death_events), key=lambda row: (_round_number(row), _tick(row))):
        round_number = _round_number(row)
        first_deaths.setdefault(round_number, row)
        attacker = bucket(round_number, row.get("attacker_name") or row.get("attacker"), row.get("attacker_steamid"))
        victim = bucket(round_number, row.get("user_name") or row.get("user"), row.get("user_steamid"))
        attacker["kills"] += 1
        victim["deaths"] += 1
        victim["survived"] = 0
        if bool(row.get("headshot")):
            attacker["headshots"] += 1
        if row.get("assister_name") or row.get("assister_steamid"):
            assister = bucket(
                round_number,
                row.get("assister_name") or row.get("assister"),
                row.get("assister_steamid"),
            )
            assister["assists"] += 1
            if bool(row.get("assistedflash")):
                assister["flash_assists"] += 1
    for round_number, row in first_deaths.items():
        bucket(round_number, row.get("attacker_name") or row.get("attacker"), row.get("attacker_steamid"))[
            "opening_kill"
        ] = 1
        bucket(round_number, row.get("user_name") or row.get("user"), row.get("user_steamid"))["opening_death"] = 1
    for row in _records(hurt_events):
        item = bucket(_round_number(row), row.get("attacker_name") or row.get("attacker"), row.get("attacker_steamid"))
        damage = _int_or_zero(row.get("dmg_health") or row.get("health_damage") or row.get("damage"))
        item["damage"] += damage
        if _is_utility_weapon(_weapon(row)):
            item["utility_damage"] += damage
    for row in _records(blind_events):
        bucket(_round_number(row), row.get("attacker_name") or row.get("attacker"), row.get("attacker_steamid"))[
            "enemies_flashed"
        ] += 1
    for item in rounds.values():
        item["kast"] = 1 if item["kills"] or item["assists"] or item["survived"] else 0
    return sorted(rounds.values(), key=lambda item: (item["round_number"], item["player_name"] or ""))


def _economy_summary(item_pickup_events) -> list[dict[str, Any]]:
    counts = Counter()
    for row in _records(item_pickup_events):
        counts[(row.get("user_name"), _string_or_none(row.get("user_steamid")), str(row.get("item") or "unknown"))] += 1
    return [
        {"player_name": name, "player_steamid": steamid, "item": item, "count": count}
        for (name, steamid, item), count in counts.most_common(200)
    ]


def _target_player_summary(target_key, player_rounds, weapon_stats, duels, damage_events) -> dict[str, Any]:
    target_rounds = [row for row in player_rounds if row.get("player_key") == target_key]
    target_weapons = [row for row in weapon_stats if row.get("player_key") == target_key]
    target_duels = [
        row
        for row in duels
        if _player_key(row.get("attacker_steamid"), row.get("attacker_name")) == target_key
        or _player_key(row.get("victim_steamid"), row.get("victim_name")) == target_key
    ]
    total_damage = sum(row["damage"] for row in target_rounds)
    total_shots = sum(row["shots"] for row in target_weapons)
    total_hits = sum(row["hits"] for row in target_weapons)
    return {
        "rounds_tracked": len(target_rounds),
        "damage": total_damage,
        "utility_damage": sum(row["utility_damage"] for row in target_rounds),
        "opening_kills": sum(row["opening_kill"] for row in target_rounds),
        "opening_deaths": sum(row["opening_death"] for row in target_rounds),
        "estimated_accuracy": round(total_hits / total_shots * 100, 2) if total_shots else None,
        "duels": len(target_duels),
        "damage_events": sum(
            1
            for row in damage_events
            if _player_key(row.get("attacker_steamid"), row.get("attacker_name")) == target_key
        ),
    }


def _deep_data_gaps(weapon_fire_events, grenade_trajectories) -> list[str]:
    gaps = []
    if not _records(weapon_fire_events):
        gaps.append("weapon_fire events are missing, so accuracy cannot be estimated.")
    if not grenade_trajectories:
        gaps.append("grenade trajectories were not parsed; only detonation/blind/damage events are available.")
    gaps.append("full per-tick movement/view-angle timeline is intentionally not stored yet to avoid database bloat.")
    return gaps


def _swing_summary(
    player: dict[str, str | None],
    player_info,
    death_events,
    hurt_events,
    blind_events,
    bomb_events: dict[str, Any],
    round_end_events,
) -> dict[str, Any]:
    team = _team_context(player, player_info)
    rounds = sorted(
        {_round_number(row) for row in _records(round_end_events)}
        | {_round_number(row) for row in _records(death_events)}
    )
    rounds = [round_number for round_number in rounds if round_number is not None]
    if not team["target_team_players"] or not team["enemy_players"] or not rounds:
        return {
            "score": None,
            "total_percentage_points": None,
            "rounds": len(rounds),
            "events": 0,
            "confidence": "low",
            "formula": "jc_swing_v1",
            "data_gaps": ["player team mapping or round events are missing"],
        }

    damage_by_round_victim = _damage_share_by_round_victim(hurt_events)
    flashes_by_round_victim = _flash_by_round_victim(blind_events)
    events = _swing_events(death_events, bomb_events)
    total_delta = 0.0
    credited_events = []
    for round_number in rounds:
        state = {
            "own_alive": len(team["target_team_players"]),
            "enemy_alive": len(team["enemy_players"]),
            "bomb_planted": False,
        }
        for event in [item for item in events if item["round_number"] == round_number]:
            before = _round_win_probability(state, team["target_side"])
            delta = 0.0
            if event["event_type"] == "death":
                victim_own = event["victim_key"] in team["target_team_players"]
                if victim_own:
                    state["own_alive"] = max(0, state["own_alive"] - 1)
                else:
                    state["enemy_alive"] = max(0, state["enemy_alive"] - 1)
                after = _round_win_probability(state, team["target_side"])
                round_delta = after - before
                if event["attacker_key"] == team["target_key"] and not victim_own:
                    damage_share = damage_by_round_victim.get(
                        (round_number, event["victim_key"], team["target_key"]),
                        0,
                    )
                    delta += round_delta * (0.7 + min(0.3, damage_share * 0.3))
                if event["assister_key"] == team["target_key"] and not victim_own:
                    delta += max(0.0, round_delta) * 0.25
                if (round_number, event["victim_key"], team["target_key"]) in flashes_by_round_victim:
                    delta += max(0.0, round_delta) * 0.15
                if event["victim_key"] == team["target_key"]:
                    delta += round_delta
            elif event["event_type"] == "bomb_planted":
                state["bomb_planted"] = True
                after = _round_win_probability(state, team["target_side"])
                if event["player_key"] == team["target_key"]:
                    delta += after - before
            elif event["event_type"] in {"bomb_defused", "bomb_exploded"}:
                after = 1.0 if _bomb_event_helps_target(event["event_type"], team["target_side"]) else 0.0
                if event["player_key"] == team["target_key"]:
                    delta += after - before
            if delta:
                total_delta += delta
                credited_events.append(
                    {
                        "round_number": round_number,
                        "tick": event.get("tick"),
                        "event_type": event["event_type"],
                        "delta_percentage_points": round(delta * 100, 2),
                    }
                )

    score = round(total_delta * 100 / len(rounds), 2) if rounds else None
    return {
        "score": score,
        "total_percentage_points": round(total_delta * 100, 2),
        "rounds": len(rounds),
        "events": len(credited_events),
        "confidence": "medium",
        "formula": "jc_swing_v1",
        "description": "Estimated average round win probability contribution in percentage points per round.",
        "top_events": sorted(credited_events, key=lambda item: abs(item["delta_percentage_points"]), reverse=True)[:20],
        "data_gaps": [
            "FACEIT/HLTV model constants are proprietary; this is a transparent approximation.",
            "Economy and exact map win-probability model are not included yet.",
        ],
    }


def _team_context(player: dict[str, str | None], player_info) -> dict[str, Any]:
    target_key = _player_key(player.get("steamid"), player.get("name"))
    target_team = None
    players_by_team: dict[int, set[str]] = defaultdict(set)
    for row in _records(player_info):
        key = _player_key(row.get("steamid"), row.get("name") or row.get("player_name"))
        team_number = _int_or_none(row.get("team_number") or row.get("team"))
        if team_number is None or team_number not in {2, 3}:
            continue
        players_by_team[team_number].add(key)
        if key == target_key:
            target_team = team_number
    enemy_team = 3 if target_team == 2 else 2 if target_team == 3 else None
    return {
        "target_key": target_key,
        "target_team": target_team,
        "target_side": _team_number_to_side(target_team),
        "target_team_players": players_by_team.get(target_team or 0, set()),
        "enemy_players": players_by_team.get(enemy_team or 0, set()),
    }


def _damage_share_by_round_victim(hurt_events) -> dict[tuple[int, str, str], float]:
    totals: Counter[tuple[int, str]] = Counter()
    by_attacker: Counter[tuple[int, str, str]] = Counter()
    for row in _records(hurt_events):
        round_number = _round_number(row)
        victim_key = _player_key(row.get("user_steamid"), row.get("user_name") or row.get("user"))
        attacker_key = _player_key(row.get("attacker_steamid"), row.get("attacker_name") or row.get("attacker"))
        damage = _int_or_zero(row.get("dmg_health") or row.get("health_damage") or row.get("damage"))
        totals[(round_number, victim_key)] += damage
        by_attacker[(round_number, victim_key, attacker_key)] += damage
    shares = {}
    for key, damage in by_attacker.items():
        total = totals[(key[0], key[1])]
        shares[key] = damage / total if total else 0
    return shares


def _flash_by_round_victim(blind_events) -> set[tuple[int, str, str]]:
    flashes = set()
    for row in _records(blind_events):
        round_number = _round_number(row)
        victim_key = _player_key(row.get("user_steamid"), row.get("user_name") or row.get("user"))
        attacker_key = _player_key(row.get("attacker_steamid"), row.get("attacker_name") or row.get("attacker"))
        if _float_or_none(row.get("blind_duration")) and _float_or_none(row.get("blind_duration")) >= 0.5:
            flashes.add((round_number, victim_key, attacker_key))
    return flashes


def _swing_events(death_events, bomb_events: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for row in _records(death_events):
        events.append(
            {
                "event_type": "death",
                "round_number": _round_number(row),
                "tick": _tick_or_none(row),
                "attacker_key": _player_key(
                    row.get("attacker_steamid"),
                    row.get("attacker_name") or row.get("attacker"),
                ),
                "victim_key": _player_key(row.get("user_steamid"), row.get("user_name") or row.get("user")),
                "assister_key": _player_key(
                    row.get("assister_steamid"),
                    row.get("assister_name") or row.get("assister"),
                ),
            }
        )
    for event_name in ("bomb_planted", "bomb_defused", "bomb_exploded"):
        for row in _records(bomb_events.get(event_name)):
            events.append(
                {
                    "event_type": event_name,
                    "round_number": _round_number(row),
                    "tick": _tick_or_none(row),
                    "player_key": _player_key(row.get("user_steamid"), row.get("user_name") or row.get("user")),
                }
            )
    return sorted(events, key=lambda item: (item["round_number"], item.get("tick") or 0))


def _round_win_probability(state: dict[str, Any], target_side: str | None) -> float:
    own_alive = max(0, int(state.get("own_alive") or 0))
    enemy_alive = max(0, int(state.get("enemy_alive") or 0))
    if own_alive <= 0:
        return 0.01
    if enemy_alive <= 0:
        return 0.99
    alive_component = own_alive / (own_alive + enemy_alive)
    advantage = (own_alive - enemy_alive) * 0.055
    bomb_bonus = 0.0
    if state.get("bomb_planted"):
        bomb_bonus = 0.16 if target_side == "T" else -0.16
    return round(min(0.99, max(0.01, alive_component + advantage + bomb_bonus)), 4)


def _bomb_event_helps_target(event_type: str, target_side: str | None) -> bool:
    return (event_type == "bomb_exploded" and target_side == "T") or (
        event_type == "bomb_defused" and target_side == "CT"
    )


def _score_for_player(
    player: dict[str, str | None],
    player_info,
    player_team_events,
    round_end_events,
) -> dict[str, Any]:
    team_by_round = _player_team_by_round(player, player_info, player_team_events)
    rounds_for = 0
    rounds_against = 0
    for row in _records(round_end_events):
        winner = row.get("winner")
        if winner not in ("T", "CT"):
            continue
        round_number = int(row.get("round") or row.get("total_rounds_played") or 0)
        player_side = team_by_round.get(round_number)
        if player_side is None:
            continue
        if player_side == winner:
            rounds_for += 1
        else:
            rounds_against += 1
    if rounds_for == rounds_against == 0:
        return {"rounds_for": None, "rounds_against": None, "result": None}
    result = "win" if rounds_for > rounds_against else "loss" if rounds_for < rounds_against else "draw"
    return {"rounds_for": rounds_for, "rounds_against": rounds_against, "result": result}


def _player_team_by_round(player: dict[str, str | None], player_info, player_team_events) -> dict[int, str]:
    player_name = player.get("name")
    player_steamid = player.get("steamid")
    switches = [
        row
        for row in _records(player_team_events)
        if _matches_player(row, player_name, player_steamid, ("user_name", "user_steamid", "user"))
    ]
    rounds = range(1, 80)
    if switches:
        first_switch = min(switches, key=lambda row: int(row.get("total_rounds_played") or 0))
        switch_round = int(first_switch.get("total_rounds_played") or 0)
        old_team = _team_number_to_side(first_switch.get("oldteam"))
        new_team = _team_number_to_side(first_switch.get("team"))
        return {round_number: old_team if round_number <= switch_round else new_team for round_number in rounds}

    team_number = None
    for row in _records(player_info):
        if _matches_player(row, player_name, player_steamid, ("name", "steamid")):
            team_number = row.get("team_number")
            break
    side = _team_number_to_side(team_number)
    return {round_number: side for round_number in rounds}


def _team_number_to_side(team_number: Any) -> str:
    try:
        number = int(team_number)
    except (TypeError, ValueError):
        return "T"
    return "T" if number == 2 else "CT" if number == 3 else "T"


def _matches_player(row: dict[str, Any], player_name: str | None, steamid: str | None, fields: tuple[str, ...]) -> bool:
    values = {str(row.get(field)) for field in fields if row.get(field) is not None}
    if player_name and player_name in values:
        return True
    return bool(steamid and steamid in values)


def _rounds_count(deaths, hurts) -> int:
    rounds = {_round_id(row) for row in _records(deaths)}
    rounds.update(_round_id(row) for row in _records(hurts))
    rounds.discard(None)
    return len(rounds)


def _records(data) -> list[dict[str, Any]]:
    if data is None:
        return []
    if hasattr(data, "to_dicts"):
        return data.to_dicts()
    if hasattr(data, "to_dict"):
        return data.to_dict("records")
    if isinstance(data, list):
        return data
    return []


def _round_id(row: dict[str, Any]) -> Any:
    return _first_present(row, ("total_rounds_played", "round", "round_num", "round_number")) or 0


def _tick(row: dict[str, Any]) -> int:
    return int(row.get("tick") or row.get("game_time") or row.get("game_tick") or 0)


def _first_present(row: dict[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        if row.get(field) not in (None, ""):
            return row.get(field)
    return None


def _header_value(header: Any, fields: tuple[str, ...]) -> str | None:
    if isinstance(header, dict):
        return next((str(header[field]) for field in fields if header.get(field)), None)
    return None


def _header_datetime(header: Any) -> datetime | None:
    if not isinstance(header, dict):
        return None
    value = _first_present(header, ("playback_time", "server_time", "demo_time"))
    if not value:
        return None
    try:
        return datetime.fromtimestamp(float(value), UTC).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None


def _demo_external_id(path: Path, player: dict[str, str | None], stats: dict[str, Any]) -> str:
    payload = f"{_file_sha1(path)}:{player.get('steamid') or player.get('name')}:{stats['kills']}:{stats['deaths']}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _save_demo_parse_artifacts(db: Session, match: Match, parsed: dict[str, Any]) -> None:
    deep = parsed.get("deep") or {}
    for model in (
        DemoParseArtifact,
        DemoRound,
        DemoPlayerRound,
        DemoWeaponStat,
        DemoDamageEvent,
        DemoDuel,
        DemoGrenadeEvent,
    ):
        db.execute(delete(model).where(model.match_id == match.id))
    db.add(
        DemoParseArtifact(
            match_id=match.id,
            import_job_id=match.import_job_id,
            parser_name=str(parsed.get("parser") or "demoparser2"),
            parser_version=parsed.get("parser_version"),
            payload_version=str(parsed.get("payload_version") or PARSER_PAYLOAD_VERSION),
            status=str(parsed.get("status") or "parsed"),
            source_demo_file=parsed.get("file"),
            demo_sha1=parsed.get("demo_sha1"),
            event_counts_json=_to_json(parsed.get("event_counts") or {}),
            confidence_json=_to_json(
                {
                    "metric_confidence": parsed.get("metric_confidence") or {},
                    "parser_confidence": parsed.get("parser_confidence"),
                }
            ),
            data_gaps_json=_to_json(
                {
                    "aim": parsed.get("aim_data_gaps") or [],
                    "deep": deep.get("data_gaps") or [],
                    "warnings": parsed.get("warnings") or [],
                }
            ),
            payload_json=_to_json(
                {
                    "header": parsed.get("header") or {},
                    "player": parsed.get("player") or {},
                    "aim_summary": parsed.get("aim_summary") or {},
                    "weapon_breakdown": parsed.get("weapon_breakdown") or {},
                    "swing_summary": parsed.get("swing_summary") or {},
                    "available_players": parsed.get("available_players") or [],
                    "deep": deep,
                    "artifact_retention": artifact_retention_metadata(ARTIFACT_CATEGORY_PARSER_ARTIFACT),
                }
            ),
        )
    )
    for row in deep.get("rounds") or []:
        db.add(
            DemoRound(
                match_id=match.id,
                round_number=_int_or_zero(row.get("round_number")),
                start_tick=_int_or_none(row.get("start_tick")),
                freeze_end_tick=_int_or_none(row.get("freeze_end_tick")),
                end_tick=_int_or_none(row.get("end_tick")),
                winner_side=row.get("winner_side"),
                end_reason=row.get("end_reason"),
                bomb_planted_tick=_int_or_none(row.get("bomb_planted_tick")),
                bomb_site=row.get("bomb_site"),
                bomb_outcome=row.get("bomb_outcome"),
                raw_json=_to_json(row),
            )
        )
    for row in deep.get("player_rounds") or []:
        db.add(
            DemoPlayerRound(
                match_id=match.id,
                round_number=_int_or_zero(row.get("round_number")),
                player_name=row.get("player_name"),
                player_steamid=row.get("player_steamid"),
                team_side=row.get("team_side"),
                kills=_int_or_zero(row.get("kills")),
                deaths=_int_or_zero(row.get("deaths")),
                assists=_int_or_zero(row.get("assists")),
                damage=_int_or_zero(row.get("damage")),
                utility_damage=_int_or_zero(row.get("utility_damage")),
                headshots=_int_or_zero(row.get("headshots")),
                flash_assists=_int_or_zero(row.get("flash_assists")),
                enemies_flashed=_int_or_zero(row.get("enemies_flashed")),
                opening_kill=_int_or_zero(row.get("opening_kill")),
                opening_death=_int_or_zero(row.get("opening_death")),
                survived=_int_or_zero(row.get("survived")),
                kast=_int_or_zero(row.get("kast")),
                raw_json=_to_json(row),
            )
        )
    for row in deep.get("weapon_stats") or []:
        db.add(
            DemoWeaponStat(
                match_id=match.id,
                player_name=row.get("player_name"),
                player_steamid=row.get("player_steamid"),
                weapon=str(row.get("weapon") or "unknown"),
                shots=_int_or_zero(row.get("shots")),
                hits=_int_or_zero(row.get("hits")),
                kills=_int_or_zero(row.get("kills")),
                deaths=_int_or_zero(row.get("deaths")),
                damage=_int_or_zero(row.get("damage")),
                headshots=_int_or_zero(row.get("headshots")),
                accuracy=_float_or_none(row.get("accuracy")),
                headshot_percent=_float_or_none(row.get("headshot_percent")),
                raw_json=_to_json(row),
            )
        )
    for row in deep.get("damage_events") or []:
        db.add(
            DemoDamageEvent(
                match_id=match.id,
                round_number=_int_or_zero(row.get("round_number")),
                tick=_int_or_none(row.get("tick")),
                attacker_name=row.get("attacker_name"),
                attacker_steamid=row.get("attacker_steamid"),
                victim_name=row.get("victim_name"),
                victim_steamid=row.get("victim_steamid"),
                weapon=row.get("weapon"),
                hitgroup=row.get("hitgroup"),
                damage_health=_int_or_zero(row.get("damage_health")),
                damage_armor=_int_or_zero(row.get("damage_armor")),
                victim_health_after=_int_or_none(row.get("victim_health_after")),
                raw_json=_to_json(row),
            )
        )
    for row in deep.get("duels") or []:
        db.add(
            DemoDuel(
                match_id=match.id,
                round_number=_int_or_zero(row.get("round_number")),
                tick=_int_or_none(row.get("tick")),
                attacker_name=row.get("attacker_name"),
                attacker_steamid=row.get("attacker_steamid"),
                victim_name=row.get("victim_name"),
                victim_steamid=row.get("victim_steamid"),
                assister_name=row.get("assister_name"),
                assister_steamid=row.get("assister_steamid"),
                weapon=row.get("weapon"),
                headshot=1 if row.get("headshot") else 0,
                opening_duel=1 if row.get("opening_duel") else 0,
                trade_kill=1 if row.get("trade_kill") else 0,
                distance=_float_or_none(row.get("distance")),
                raw_json=_to_json(row),
            )
        )
    for row in deep.get("grenade_events") or []:
        db.add(
            DemoGrenadeEvent(
                match_id=match.id,
                round_number=_int_or_zero(row.get("round_number")),
                tick=_int_or_none(row.get("tick")),
                event_type=str(row.get("event_type") or "grenade"),
                grenade_type=row.get("grenade_type"),
                player_name=row.get("player_name"),
                player_steamid=row.get("player_steamid"),
                x=_float_or_none(row.get("x")),
                y=_float_or_none(row.get("y")),
                z=_float_or_none(row.get("z")),
                flashed_count=_int_or_zero(row.get("flashed_count")),
                damage=_int_or_zero(row.get("damage")),
                raw_json=_to_json(row),
            )
        )
    db.commit()


def _file_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value, default=str)
        return value
    except TypeError:
        return str(value)


def _to_json(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, default=str)


def _parser_version() -> str | None:
    try:
        return importlib.metadata.version("demoparser2")
    except importlib.metadata.PackageNotFoundError:
        return None


def _round_number(row: dict[str, Any]) -> int:
    value = _first_present(row, ("total_rounds_played", "round", "round_num", "round_number"))
    return _int_or_zero(value)


def _tick_or_none(row: dict[str, Any]) -> int | None:
    tick = _tick(row)
    return tick if tick else None


def _player_key(steamid: Any, name: Any) -> str:
    steam = _string_or_none(steamid)
    if steam:
        return f"steam:{steam}"
    if name not in (None, ""):
        return f"name:{str(name).lower()}"
    return "unknown"


def _string_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _int_or_zero(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:
        return None
    return result


def _position(row: dict[str, Any]) -> dict[str, float | None]:
    return {"x": _float_or_none(row.get("x")), "y": _float_or_none(row.get("y")), "z": _float_or_none(row.get("z"))}


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _jsonable(value) for key, value in row.items() if value not in (None, "")}


def _is_utility_weapon(weapon: str) -> bool:
    return any(part in weapon for part in ("hegrenade", "inferno", "molotov", "incgrenade", "flashbang", "smoke"))


def _grenade_weapon(event_name: str) -> str:
    if event_name == "inferno_startburn":
        return "inferno"
    return event_name.removesuffix("_detonate")


def _bomb_site(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if str(value) in {"168", "A"}:
        return "A"
    if str(value) in {"169", "B"}:
        return "B"
    return str(value)


def _round_by_tick_index(round_end_events) -> list[tuple[int, int]]:
    return sorted(
        (
            (int(row.get("total_rounds_played") or row.get("round") or 0), _tick(row))
            for row in _records(round_end_events)
        ),
        key=lambda item: item[1],
    )


def _round_for_tick(tick: int, round_by_tick: list[tuple[int, int]]) -> int | None:
    for round_number, end_tick in round_by_tick:
        if tick <= end_tick:
            return round_number
    return round_by_tick[-1][0] if round_by_tick else None
