from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

STEAM_GC_PLAYED_AT_SOURCE = "steam_gc_match_time"


def parse_steam_match_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, int | float):
        parsed = _datetime_from_epoch(float(value))
    elif isinstance(value, str):
        parsed = _datetime_from_string(value)
    else:
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def steam_gc_metadata_from_item(item: dict[str, Any]) -> dict[str, Any]:
    nested = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    played_at = parse_steam_match_time(
        item.get("match_time")
        or item.get("matchtime")
        or item.get("match_time_seconds")
        or item.get("matchtime_seconds")
        or nested.get("match_time")
        or nested.get("matchtime")
    )
    metadata = {
        "source": "steam_gc",
        "match_id": item.get("match_id") or item.get("matchid") or nested.get("match_id") or nested.get("matchid"),
        "match_time": (
            item.get("match_time") or item.get("matchtime") or nested.get("match_time") or nested.get("matchtime")
        ),
        "share_code": item.get("share_code"),
    }
    if nested:
        metadata["raw_gc_metadata"] = nested
    if played_at:
        metadata["played_at"] = played_at.isoformat()
        metadata["played_at_source"] = STEAM_GC_PLAYED_AT_SOURCE
    return {key: value for key, value in metadata.items() if value is not None}


def apply_steam_metadata_to_parsed_demo(parsed: dict[str, Any], metadata: dict[str, Any]) -> None:
    played_at = parse_steam_match_time(metadata.get("played_at") or metadata.get("match_time"))
    if not played_at:
        return
    parsed["played_at"] = played_at.isoformat()
    parsed["played_at_source"] = STEAM_GC_PLAYED_AT_SOURCE
    parsed["steam_metadata"] = metadata
    match = parsed.get("match")
    if isinstance(match, dict):
        match["played_at"] = played_at
        match["played_at_source"] = STEAM_GC_PLAYED_AT_SOURCE


def _datetime_from_epoch(value: float) -> datetime | None:
    if value <= 0:
        return None
    if value > 10_000_000_000:
        value = value / 1000
    try:
        return datetime.fromtimestamp(value, UTC).replace(tzinfo=None)
    except (OSError, OverflowError, ValueError):
        return None


def _datetime_from_string(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    try:
        return _datetime_from_epoch(float(text))
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed
