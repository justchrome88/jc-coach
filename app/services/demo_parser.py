from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Match
from app.services.recommendation_tracking import ensure_default_recommendation, evaluate_new_matches


class DemoParseError(RuntimeError):
    pass


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
) -> dict[str, Any]:
    stored_path = _store_demo(source_path, original_filename)
    parsed = parse_demo(stored_path, player_identifier=player_identifier)
    match_data = parsed["match"]
    match_data["demo_file"] = str(stored_path)
    match_data["source"] = "demo"
    match_data["raw_json"] = json.dumps(parsed, ensure_ascii=False, default=str)

    existing = db.scalar(
        select(Match).where(
            Match.source == match_data["source"],
            Match.external_match_id == match_data["external_match_id"],
        )
    )
    if existing:
        if stored_path.exists() and str(stored_path) != existing.demo_file:
            stored_path.unlink()
        return {
            "imported": 0,
            "skipped_duplicates": 1,
            "errors": 0,
            "match_id": existing.id,
            "player": parsed["player"],
            "stored_path": existing.demo_file,
            "match": parsed["match"],
            "available_players": parsed["available_players"],
            "event_counts": parsed["event_counts"],
            "metric_confidence": parsed["metric_confidence"],
            "parser_confidence": parsed["parser_confidence"],
            "warnings": parsed["warnings"],
            "message": "Demo already imported.",
        }

    match = Match(**match_data)
    db.add(match)
    db.commit()
    db.refresh(match)
    ensure_default_recommendation(db)
    evaluate_new_matches(db)
    return {
        "imported": 1,
        "skipped_duplicates": 0,
        "errors": 0,
        "match_id": match.id,
        "player": parsed["player"],
        "stored_path": str(stored_path),
        "match": parsed["match"],
        "available_players": parsed["available_players"],
        "event_counts": parsed["event_counts"],
        "metric_confidence": parsed["metric_confidence"],
        "parser_confidence": parsed["parser_confidence"],
        "warnings": parsed["warnings"],
        "message": parsed["message"],
    }


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
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise DemoParseError(f"Could not parse .dem file with demoparser2: {exc}") from exc

    if not _records(death_events) and not _records(hurt_events):
        raise DemoParseError("Demo parsed, but no kill/damage events were found.")

    player = _select_player(death_events, hurt_events, player_info, player_identifier)
    stats = _player_stats(player, death_events, hurt_events)
    score = _score_for_player(player, player_info, player_team_events, round_end_events)
    rounds_count = _rounds_count(death_events, hurt_events)
    event_counts = {
        "player_info": len(_records(player_info)),
        "player_death": len(_records(death_events)),
        "player_hurt": len(_records(hurt_events)),
        "round_end": len(_records(round_end_events)),
        "player_team": len(_records(player_team_events)),
        "rounds": rounds_count,
    }
    adr = round(stats["damage"] / rounds_count, 2) if rounds_count else None
    map_name = _header_value(header, ("map_name", "map", "mapName"))
    played_at = _header_datetime(header) or datetime.fromtimestamp(path.stat().st_mtime, UTC).replace(tzinfo=None)
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
        "headshot_percent": round(stats["headshots"] / stats["kills"] * 100, 2) if stats["kills"] else 0,
        "entry_kills": stats["entry_kills"],
        "entry_deaths": stats["entry_deaths"],
        "early_deaths": stats["entry_deaths"],
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
    metric_confidence = _metric_confidence(event_counts, score, stats, adr)
    warnings = _parser_warnings(metric_confidence)
    return {
        "status": "parsed",
        "parser": "demoparser2",
        "file": str(path),
        "player": player,
        "match": match,
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
) -> dict[str, str]:
    confidence = {
        "kills_deaths_assists": "high" if event_counts["player_death"] else "low",
        "adr": "high" if adr is not None and event_counts["player_hurt"] and event_counts["rounds"] else "low",
        "entry_duels": "medium" if event_counts["player_death"] else "low",
        "kast": "medium" if stats.get("kast") is not None and event_counts["player_death"] else "low",
        "utility": "medium" if event_counts["player_hurt"] else "low",
        "score": "medium" if score.get("rounds_for") is not None and event_counts["round_end"] else "low",
        "side_stats": "low",
        "early_deaths": "low",
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
        warnings.append("Early deaths currently fall back to entry deaths; true timing is not implemented yet.")
    if metric_confidence.get("side_stats") == "low":
        warnings.append("T/CT side stats are not reliable yet.")
    if metric_confidence.get("utility") != "high":
        warnings.append("Utility and flash metrics are best-effort because demo event fields vary.")
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


def _store_demo(source_path: Path, original_filename: str | None) -> Path:
    settings = get_settings()
    suffix = source_path.suffix.lower() or ".dem"
    digest = _file_sha1(source_path)
    safe_name = Path(original_filename or source_path.name).name.replace(" ", "_")
    if not safe_name.lower().endswith(".dem"):
        safe_name = f"{safe_name}{suffix}"
    destination = Path(settings.upload_dir) / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{digest[:10]}_{safe_name}"
    shutil.copy2(source_path, destination)
    return destination


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


def _player_stats(player: dict[str, str | None], deaths, hurts) -> dict[str, int | float | None]:
    player_name = player.get("name")
    player_steamid = player.get("steamid")
    kills = deaths_count = assists = headshots = flash_assists = 0
    damage = utility_damage = enemies_flashed = 0
    round_kill = defaultdict(bool)
    round_death = defaultdict(bool)
    round_assist = defaultdict(bool)
    first_death_by_round: dict[Any, dict[str, Any]] = {}

    for row in _records(deaths):
        round_id = _round_id(row)
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
            round_kill[round_id] = True
            if bool(row.get("headshot")):
                headshots += 1
        if victim_match:
            deaths_count += 1
            round_death[round_id] = True
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
        weapon = str(row.get("weapon") or row.get("weapon_name") or "").lower()
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
    }


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
