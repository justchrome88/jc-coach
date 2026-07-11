"""CSV and JSON match ingestion adapter."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Match
from app.services.coach.recommendations import ensure_default_recommendation, evaluate_new_matches

INT_FIELDS = {
    "rounds_for",
    "rounds_against",
    "kills",
    "deaths",
    "assists",
    "entry_kills",
    "entry_deaths",
    "early_deaths",
    "flash_assists",
    "utility_damage",
    "enemies_flashed",
    "clutches_won",
    "clutches_lost",
    "side_t_rounds_won",
    "side_t_rounds_lost",
    "side_ct_rounds_won",
    "side_ct_rounds_lost",
}
FLOAT_FIELDS = {"kd", "adr", "kast", "rating", "swing_score", "headshot_percent"}
TEXT_FIELDS = {"source", "external_match_id", "demo_file", "map_name", "mode", "result"}
DATE_FIELDS = {"played_at"}
SUPPORTED_FIELDS = INT_FIELDS | FLOAT_FIELDS | TEXT_FIELDS | DATE_FIELDS


def import_csv(db: Session, content: bytes | str, source: str = "csv") -> dict[str, int]:
    text = _to_text(content)
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return import_rows(db, rows, source=source)


def import_json(db: Session, content: bytes | str, source: str = "json") -> dict[str, int]:
    payload = json.loads(_to_text(content))
    rows = payload.get("matches", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("JSON must be a list of matches or an object with a matches list")
    return import_rows(db, rows, source=source)


def import_file(db: Session, path: Path, source: str | None = None) -> dict[str, int]:
    suffix = path.suffix.lower()
    content = path.read_bytes()
    if suffix == ".csv":
        return import_csv(db, content, source=source or "csv")
    if suffix == ".json":
        return import_json(db, content, source=source or "json")
    raise ValueError(f"Unsupported file type: {suffix}")


def import_rows(db: Session, rows: list[dict[str, Any]], source: str = "upload") -> dict[str, int]:
    imported = 0
    skipped_duplicates = 0
    errors = 0

    for row in rows:
        try:
            match_data = normalize_match(row, default_source=source)
            external_id = match_data["external_match_id"]
            existing = db.scalar(
                select(Match).where(Match.source == match_data["source"], Match.external_match_id == external_id)
            )
            if existing:
                skipped_duplicates += 1
                continue
            db.add(Match(**match_data))
            imported += 1
        except (TypeError, ValueError, KeyError):
            errors += 1

    db.commit()
    ensure_default_recommendation(db)
    evaluate_new_matches(db)
    return {"imported": imported, "skipped_duplicates": skipped_duplicates, "errors": errors}


def normalize_match(row: dict[str, Any], default_source: str = "upload") -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field in SUPPORTED_FIELDS:
        value = row.get(field)
        if value == "":
            value = None
        if field in INT_FIELDS:
            normalized[field] = _to_int(value)
        elif field in FLOAT_FIELDS:
            normalized[field] = _to_float(value)
        elif field in DATE_FIELDS:
            normalized[field] = _to_datetime(value)
        elif field in TEXT_FIELDS:
            normalized[field] = str(value).strip() if value is not None else None

    normalized["source"] = normalized.get("source") or default_source
    normalized["result"] = _normalize_result(normalized.get("result"))
    if normalized.get("kd") is None and normalized.get("kills") is not None and normalized.get("deaths") is not None:
        deaths = normalized["deaths"] or 1
        normalized["kd"] = round(normalized["kills"] / deaths, 2)
    if normalized.get("early_deaths") is None:
        normalized["early_deaths"] = normalized.get("entry_deaths")
    normalized["raw_json"] = json.dumps(row, ensure_ascii=False, default=str)
    normalized["external_match_id"] = normalized.get("external_match_id") or _stable_match_id(normalized, row)
    return normalized


def _stable_match_id(normalized: dict[str, Any], row: dict[str, Any]) -> str:
    identity = {
        "played_at": normalized.get("played_at").isoformat() if normalized.get("played_at") else None,
        "map_name": normalized.get("map_name"),
        "result": normalized.get("result"),
        "rounds_for": normalized.get("rounds_for"),
        "rounds_against": normalized.get("rounds_against"),
        "kills": normalized.get("kills"),
        "deaths": normalized.get("deaths"),
        "raw": row,
    }
    payload = json.dumps(identity, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _to_text(content: bytes | str) -> str:
    return content.decode("utf-8-sig") if isinstance(content, bytes) else content


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(float(str(value).strip()))


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(str(value).strip().replace(",", "."))


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)


def _normalize_result(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    aliases = {"w": "win", "won": "win", "victory": "win", "l": "loss", "lost": "loss", "lose": "loss", "draw": "draw"}
    return aliases.get(text, text)
