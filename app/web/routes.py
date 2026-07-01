from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Match
from app.db.session import get_db
from app.main import templates
from app.services.analytics import chart_series, compare_periods, get_map_stats, get_summary
from app.services.coach_rules import build_coach_focus
from app.services.importer import import_csv, import_json
from app.services.recommendation_tracking import get_active_recommendation_progress, get_evaluations_by_match_id
from app.services.report_generator import generate_report, latest_report, markdown_to_html

router = APIRouter()


@router.get("/")
def dashboard(request: Request, db: Annotated[Session, Depends(get_db)]):
    matches = db.scalars(select(Match).order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    summary = get_summary(matches)
    comparison = compare_periods(matches)
    map_stats = get_map_stats(matches)
    focus = build_coach_focus(summary, comparison, map_stats)
    recommendation_progress = get_active_recommendation_progress(db)
    evaluations_by_match_id = get_evaluations_by_match_id(db)
    recent_matches = list(reversed(matches[-10:]))
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "summary": summary,
            "comparison": comparison,
            "map_stats": map_stats,
            "focus": focus,
            "recommendation_progress": recommendation_progress,
            "evaluations_by_match_id": evaluations_by_match_id,
            "recent_matches": recent_matches,
            "chart_data": chart_series(matches),
        },
    )


@router.get("/upload")
def upload_page(request: Request, message: str | None = None):
    return templates.TemplateResponse(request=request, name="upload.html", context={"message": message})


@router.post("/upload")
async def upload_file(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
):
    content = await file.read()
    if file.filename and file.filename.lower().endswith(".json"):
        result = import_json(db, content, source="json")
    else:
        result = import_csv(db, content, source="csv")
    message = f"Imported {result['imported']}, duplicates {result['skipped_duplicates']}, errors {result['errors']}"
    return templates.TemplateResponse(request=request, name="upload.html", context={"message": message})


@router.get("/matches")
def matches_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    map_name: str | None = None,
    result: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    stmt = select(Match)
    if map_name:
        stmt = stmt.where(Match.map_name == map_name)
    if result:
        stmt = stmt.where(Match.result == result)
    if date_from:
        stmt = stmt.where(Match.played_at >= _parse_date(date_from))
    if date_to:
        stmt = stmt.where(Match.played_at <= _parse_date(date_to))
    matches = db.scalars(stmt.order_by(Match.played_at.desc().nulls_last(), Match.id.desc())).all()
    evaluations_by_match_id = get_evaluations_by_match_id(db)
    maps = db.scalars(
        select(Match.map_name).where(Match.map_name.is_not(None)).distinct().order_by(Match.map_name)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="matches.html",
        context={
            "request": request,
            "matches": matches,
            "evaluations_by_match_id": evaluations_by_match_id,
            "maps": maps,
            "filters": {
                "map_name": map_name or "",
                "result": result or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
            },
        },
    )


@router.get("/report")
def report_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    report = latest_report(db)
    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={"report": report, "report_html": markdown_to_html(report.report_markdown) if report else None},
    )


@router.post("/report/generate")
def generate_report_page(db: Annotated[Session, Depends(get_db)]):
    generate_report(db)
    return RedirectResponse("/report", status_code=303)


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")
