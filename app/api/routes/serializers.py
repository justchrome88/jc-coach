"""API-only serialization helpers."""

from __future__ import annotations

import json
from typing import Any

from app.db.models import ImportJob, Match


def serialize_import_job(job: ImportJob) -> dict:
    return {
        "id": job.id,
        "provider": job.provider,
        "job_type": job.job_type,
        "status": job.status,
        "user_id": job.user_id,
        "steam_account_id": job.steam_account_id,
        "logical_target_key": job.logical_target_key,
        "requested_payload": _json_dict(job.requested_payload_json),
        "result": _json_dict(job.result_json),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "error_message": job.error_message,
    }

def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)

def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}

def serialize_match(match: Match) -> dict:
    raw = _match_raw(match)
    return {
        "id": match.id,
        "source": match.source,
        "external_match_id": match.external_match_id,
        "played_at": match.played_at.isoformat() if match.played_at else None,
        "played_at_source": raw.get("played_at_source"),
        "map_name": match.map_name,
        "mode": match.mode,
        "result": match.result,
        "rounds_for": match.rounds_for,
        "rounds_against": match.rounds_against,
        "kills": None,
        "deaths": None,
        "assists": None,
        "kd": None,
        "adr": None,
        "kast": None,
        "rating": None,
        "swing_score": None,
        "headshot_percent": None,
        "entry_kills": None,
        "entry_deaths": None,
        "early_deaths": None,
        "flash_assists": None,
        "utility_damage": None,
        "enemies_flashed": None,
        "clutches_won": None,
        "clutches_lost": None,
        "metric_assurance": {
            "status": "legacy_unverified",
            "trusted_performance_metrics_available": False,
            "reason_codes": ["validated_versioned_snapshot_required"],
        },
    }

def _match_raw(match: Match) -> dict:
    try:
        raw = json.loads(match.raw_json or "{}")
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}

__all__ = (
    'serialize_import_job',
    'serialize_match',
)
