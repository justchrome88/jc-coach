from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Match
from app.db.session import get_db
from app.services.analytics import compare_periods, get_map_stats, get_summary
from app.services.demo_parser import DemoParseError, import_demo_file
from app.services.importer import import_csv, import_json
from app.services.recommendation_tracking import (
    get_active_recommendation_progress,
)
from app.services.report_generator import generate_report, latest_report

router = APIRouter(prefix="/api")


@router.get("/matches")
def list_matches(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    matches = db.scalars(select(Match).order_by(Match.played_at.desc().nulls_last(), Match.id.desc())).all()
    return [serialize_match(match) for match in matches]


@router.post("/import/csv")
async def import_csv_endpoint(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    result = import_csv(db, await file.read(), source="csv")
    return {"ok": True, **result}


@router.post("/import/json")
async def import_json_endpoint(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    try:
        result = import_json(db, await file.read(), source="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.post("/import/demo")
async def import_demo_endpoint(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    player_identifier: str | None = None,
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".dem"):
        raise HTTPException(status_code=400, detail="Upload a .dem file")
    with NamedTemporaryFile(suffix=".dem", delete=True) as temporary:
        temporary.write(await file.read())
        temporary.flush()
        try:
            result = import_demo_file(
                db,
                Path(temporary.name),
                original_filename=file.filename,
                player_identifier=player_identifier,
            )
        except DemoParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.get("/analytics/summary")
def analytics_summary(db: Annotated[Session, Depends(get_db)]) -> dict:
    matches = db.scalars(select(Match).order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    summary = get_summary(matches)
    comparison = compare_periods(matches)
    map_stats = get_map_stats(matches)
    return {"summary": summary, "comparison": comparison, "map_stats": map_stats}


@router.get("/recommendations/active")
def active_recommendation(db: Annotated[Session, Depends(get_db)]) -> dict:
    progress = get_active_recommendation_progress(db)
    if not progress:
        raise HTTPException(status_code=404, detail="No active recommendation yet")
    recommendation = progress["recommendation"]
    return {
        "id": recommendation.id,
        "title": recommendation.title,
        "status": recommendation.status,
        "baseline": progress["baseline"],
        "target": progress["target"],
        "counts": progress["counts"],
        "progress_score": progress["progress_score"],
        "completed_matches": progress["completed_matches"],
        "target_matches": progress["target_matches"],
        "summary": progress["summary"],
    }


@router.post("/reports/generate")
def generate_report_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    report = generate_report(db)
    return {"ok": True, "id": report.id, "matches_count": report.matches_count, "created_at": report.created_at}


@router.get("/reports/latest")
def latest_report_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    report = latest_report(db)
    if report is None:
        raise HTTPException(status_code=404, detail="No reports generated yet")
    return {
        "id": report.id,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "matches_count": report.matches_count,
        "report_markdown": report.report_markdown,
        "created_at": report.created_at,
    }


def serialize_match(match: Match) -> dict:
    return {
        "id": match.id,
        "source": match.source,
        "external_match_id": match.external_match_id,
        "played_at": match.played_at.isoformat() if match.played_at else None,
        "map_name": match.map_name,
        "mode": match.mode,
        "result": match.result,
        "rounds_for": match.rounds_for,
        "rounds_against": match.rounds_against,
        "kills": match.kills,
        "deaths": match.deaths,
        "assists": match.assists,
        "kd": match.kd,
        "adr": match.adr,
        "kast": match.kast,
        "rating": match.rating,
        "headshot_percent": match.headshot_percent,
        "entry_kills": match.entry_kills,
        "entry_deaths": match.entry_deaths,
        "early_deaths": match.early_deaths,
        "flash_assists": match.flash_assists,
        "utility_damage": match.utility_damage,
        "enemies_flashed": match.enemies_flashed,
        "clutches_won": match.clutches_won,
        "clutches_lost": match.clutches_lost,
    }
