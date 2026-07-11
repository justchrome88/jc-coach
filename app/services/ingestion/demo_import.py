"""Demo import persistence and parser handoff orchestration."""

from __future__ import annotations

import json
from datetime import datetime
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
from app.services.ingestion.demo_storage import store_demo_file
from app.services.ingestion.match_metadata import apply_steam_metadata_to_parsed_demo
from app.services.metrics.recommendations import (
    compact_recommendation_evaluations,
    ensure_default_recommendation,
    evaluate_recommendations_for_match,
    recommendation_evaluation_metadata,
)
from app.services.parsing import demo_parser
from app.services.parsing.demo_parser import PARSER_PAYLOAD_VERSION, DemoParseError
from app.services.shared.demo_retention import (
    ARTIFACT_CATEGORY_PARSER_ARTIFACT,
    ARTIFACT_CATEGORY_RAW_DEMO,
    artifact_retention_metadata,
    retention_metadata,
)
from app.services.shared.value_coercion import float_or_none, int_or_none, int_or_zero, jsonable

MATCH_COLUMN_NAMES = frozenset(column.name for column in Match.__table__.columns)


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
        parsed = demo_parser.parse_demo(stored_path, player_identifier=player_identifier)
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
        "state": storage_metadata["state"],
        "sha1": storage_metadata["sha1"],
        "size_bytes": storage_metadata["size_bytes"],
        "integrity": storage_metadata["integrity"],
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
    match_model_data["user_id"] = int_or_none(storage_links.get("user_id"))
    match_model_data["steam_account_id"] = int_or_none(storage_links.get("steam_account_id"))
    match_model_data["import_job_id"] = int_or_none(storage_links.get("import_job_id"))

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
        "state": stored["state"],
        "path": stored["path"],
        "relative_path": stored["relative_path"],
        "parser_handoff_path": stored["parser_handoff_path"],
        "sha1": stored["sha1"],
        "size_bytes": stored["size_bytes"],
        "integrity": stored["integrity"],
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
                    "source_artifact": parsed.get("storage", {}).get("integrity"),
                }
            ),
        )
    )
    for row in deep.get("rounds") or []:
        db.add(
            DemoRound(
                match_id=match.id,
                round_number=int_or_zero(row.get("round_number")),
                start_tick=int_or_none(row.get("start_tick")),
                freeze_end_tick=int_or_none(row.get("freeze_end_tick")),
                end_tick=int_or_none(row.get("end_tick")),
                winner_side=row.get("winner_side"),
                end_reason=row.get("end_reason"),
                bomb_planted_tick=int_or_none(row.get("bomb_planted_tick")),
                bomb_site=row.get("bomb_site"),
                bomb_outcome=row.get("bomb_outcome"),
                raw_json=_to_json(row),
            )
        )
    for row in deep.get("player_rounds") or []:
        db.add(
            DemoPlayerRound(
                match_id=match.id,
                round_number=int_or_zero(row.get("round_number")),
                player_name=row.get("player_name"),
                player_steamid=row.get("player_steamid"),
                team_side=row.get("team_side"),
                kills=int_or_zero(row.get("kills")),
                deaths=int_or_zero(row.get("deaths")),
                assists=int_or_zero(row.get("assists")),
                damage=int_or_zero(row.get("damage")),
                utility_damage=int_or_zero(row.get("utility_damage")),
                headshots=int_or_zero(row.get("headshots")),
                flash_assists=int_or_zero(row.get("flash_assists")),
                enemies_flashed=int_or_zero(row.get("enemies_flashed")),
                opening_kill=int_or_zero(row.get("opening_kill")),
                opening_death=int_or_zero(row.get("opening_death")),
                survived=int_or_zero(row.get("survived")),
                kast=int_or_zero(row.get("kast")),
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
                shots=int_or_zero(row.get("shots")),
                hits=int_or_zero(row.get("hits")),
                kills=int_or_zero(row.get("kills")),
                deaths=int_or_zero(row.get("deaths")),
                damage=int_or_zero(row.get("damage")),
                headshots=int_or_zero(row.get("headshots")),
                accuracy=float_or_none(row.get("accuracy")),
                headshot_percent=float_or_none(row.get("headshot_percent")),
                raw_json=_to_json(row),
            )
        )
    for row in deep.get("damage_events") or []:
        db.add(
            DemoDamageEvent(
                match_id=match.id,
                round_number=int_or_zero(row.get("round_number")),
                tick=int_or_none(row.get("tick")),
                attacker_name=row.get("attacker_name"),
                attacker_steamid=row.get("attacker_steamid"),
                victim_name=row.get("victim_name"),
                victim_steamid=row.get("victim_steamid"),
                weapon=row.get("weapon"),
                hitgroup=row.get("hitgroup"),
                damage_health=int_or_zero(row.get("damage_health")),
                damage_armor=int_or_zero(row.get("damage_armor")),
                victim_health_after=int_or_none(row.get("victim_health_after")),
                raw_json=_to_json(row),
            )
        )
    for row in deep.get("duels") or []:
        db.add(
            DemoDuel(
                match_id=match.id,
                round_number=int_or_zero(row.get("round_number")),
                tick=int_or_none(row.get("tick")),
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
                distance=float_or_none(row.get("distance")),
                raw_json=_to_json(row),
            )
        )
    for row in deep.get("grenade_events") or []:
        db.add(
            DemoGrenadeEvent(
                match_id=match.id,
                round_number=int_or_zero(row.get("round_number")),
                tick=int_or_none(row.get("tick")),
                event_type=str(row.get("event_type") or "grenade"),
                grenade_type=row.get("grenade_type"),
                player_name=row.get("player_name"),
                player_steamid=row.get("player_steamid"),
                x=float_or_none(row.get("x")),
                y=float_or_none(row.get("y")),
                z=float_or_none(row.get("z")),
                flashed_count=int_or_zero(row.get("flashed_count")),
                damage=int_or_zero(row.get("damage")),
                raw_json=_to_json(row),
            )
        )
    db.commit()

def _to_json(value: Any) -> str:
    return json.dumps(jsonable(value), ensure_ascii=False, default=str)

__all__ = (
    "import_demo_file",
    "import_inbox_demo",
    "list_inbox_demos",
)
