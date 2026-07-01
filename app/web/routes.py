from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Match
from app.db.session import get_db
from app.main import templates
from app.services.ai_coach import (
    latest_ai_coach_report,
    latest_ai_handoff,
    prepare_ai_coach_handoff,
    save_ai_coach_result,
)
from app.services.analytics import (
    chart_series,
    compare_periods,
    get_dashboard_status,
    get_map_stats,
    get_summary,
    match_detail,
)
from app.services.coach_rules import build_coach_focus
from app.services.demo_parser import DemoParseError, import_demo_file, import_inbox_demo, list_inbox_demos
from app.services.importer import import_csv, import_json
from app.services.mistake_detection import (
    category_scorecard,
    detect_structured_mistakes,
    match_coach_sections,
    mistakes_by_match_id,
)
from app.services.recommendation_tracking import (
    get_active_recommendation_progress,
    get_all_recommendation_progress,
    get_evaluations_by_match_id,
)
from app.services.report_generator import generate_report, latest_report, markdown_to_html
from app.services.steam_integration import (
    create_steam_import_job,
    link_steam_account,
    list_import_jobs,
    list_steam_accounts,
    parse_share_code_input,
    steam_login_url,
    validate_openid_callback,
)

router = APIRouter()


@router.get("/")
def dashboard(request: Request, db: Annotated[Session, Depends(get_db)]):
    matches = db.scalars(select(Match).order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    summary = get_summary(matches)
    comparison = compare_periods(matches)
    map_stats = get_map_stats(matches)
    dashboard_status = get_dashboard_status(matches)
    recommendation_progress = get_active_recommendation_progress(db)
    all_recommendation_progress = get_all_recommendation_progress(db)
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
            "dashboard_status": dashboard_status,
            "recommendation_progress": recommendation_progress,
            "all_recommendation_progress": all_recommendation_progress,
            "evaluations_by_match_id": evaluations_by_match_id,
            "recent_matches": recent_matches,
            "chart_data": chart_series(matches),
        },
    )


@router.get("/coach")
def coach_page(request: Request, db: Annotated[Session, Depends(get_db)], message: str | None = None):
    matches = db.scalars(select(Match).order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    summary = get_summary(matches)
    comparison = compare_periods(matches)
    map_stats = get_map_stats(matches)
    focus = build_coach_focus(summary, comparison, map_stats)
    structured_mistakes = detect_structured_mistakes(matches)
    coach_categories = category_scorecard(structured_mistakes)
    recommendation_progress = get_active_recommendation_progress(db)
    all_recommendation_progress = get_all_recommendation_progress(db)
    evaluations_by_match_id = get_evaluations_by_match_id(db)
    evaluated_matches = [
        match
        for match in reversed(matches)
        if match.id in evaluations_by_match_id
    ][:10]
    report = latest_report(db)
    ai_handoff = latest_ai_handoff()
    ai_report = latest_ai_coach_report(db)
    return templates.TemplateResponse(
        request=request,
        name="coach.html",
        context={
            "request": request,
            "message": message,
            "focus": focus,
            "structured_mistakes": structured_mistakes[:12],
            "coach_categories": coach_categories,
            "recommendation_progress": recommendation_progress,
            "all_recommendation_progress": all_recommendation_progress,
            "evaluations_by_match_id": evaluations_by_match_id,
            "evaluated_matches": evaluated_matches,
            "report": report,
            "ai_handoff": ai_handoff,
            "ai_report": ai_report,
        },
    )


@router.get("/upload")
def upload_page(request: Request, message: str | None = None):
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={"message": message, "inbox_demos": list_inbox_demos()},
    )


@router.get("/settings/imports")
def import_settings_page(request: Request, db: Annotated[Session, Depends(get_db)], message: str | None = None):
    return templates.TemplateResponse(
        request=request,
        name="import_settings.html",
        context={
            "request": request,
            "message": message,
            "steam_accounts": list_steam_accounts(db),
            "import_jobs": list_import_jobs(db),
        },
    )


@router.get("/auth/steam")
def steam_auth_start():
    return RedirectResponse(steam_login_url(), status_code=303)


@router.get("/auth/steam/callback")
def steam_auth_callback(request: Request, db: Annotated[Session, Depends(get_db)]):
    steam_id, error = validate_openid_callback(dict(request.query_params))
    if error:
        return RedirectResponse(f"/settings/imports?message={error}", status_code=303)
    link_steam_account(db, steam_id)
    create_steam_import_job(db, None, "steam_openid_linked", {"steam_id": steam_id})
    return RedirectResponse("/settings/imports?message=Steam account linked.", status_code=303)


@router.post("/settings/imports/share-code")
def create_share_code_job(db: Annotated[Session, Depends(get_db)], share_code: Annotated[str, Form()]):
    try:
        payload = parse_share_code_input(share_code)
    except ValueError as exc:
        return RedirectResponse(f"/settings/imports?message={exc}", status_code=303)
    create_steam_import_job(db, None, "share_code_import", payload)
    return RedirectResponse("/settings/imports?message=Share-code import job queued.", status_code=303)


@router.post("/upload")
async def upload_file(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    player_identifier: Annotated[str | None, Form()] = None,
):
    content = await file.read()
    filename = file.filename or ""
    try:
        import_result = None
        if filename.lower().endswith(".dem"):
            with NamedTemporaryFile(suffix=".dem", delete=True) as temporary:
                temporary.write(content)
                temporary.flush()
                result = import_demo_file(
                    db,
                    Path(temporary.name),
                    original_filename=filename,
                    player_identifier=player_identifier,
                )
                import_result = result
        elif filename.lower().endswith(".json"):
            result = import_json(db, content, source="json")
        else:
            result = import_csv(db, content, source="csv")
        message = f"Imported {result['imported']}, duplicates {result['skipped_duplicates']}, errors {result['errors']}"
    except DemoParseError as exc:
        message = f"Demo parse failed: {exc}"
        import_result = None
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={"message": message, "inbox_demos": list_inbox_demos(), "import_result": import_result},
    )


@router.post("/upload/server-demo")
def upload_server_demo(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    filename: Annotated[str, Form()],
    player_identifier: Annotated[str | None, Form()] = None,
):
    try:
        result = import_inbox_demo(db, filename, player_identifier=player_identifier)
        import_result = result
        message = f"Imported {result['imported']}, duplicates {result['skipped_duplicates']}, errors {result['errors']}"
    except DemoParseError as exc:
        message = f"Demo parse failed: {exc}"
        import_result = None
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={"message": message, "inbox_demos": list_inbox_demos(), "import_result": import_result},
    )


@router.get("/matches")
def matches_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    map_name: str | None = None,
    result: str | None = None,
    source: str | None = None,
    goal_status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = "played_at",
    direction: str = "desc",
    page: int = 1,
    per_page: int = 25,
):
    stmt = select(Match)
    if map_name:
        stmt = stmt.where(Match.map_name == map_name)
    if result:
        stmt = stmt.where(Match.result == result)
    if source:
        stmt = stmt.where(Match.source == source)
    if date_from:
        stmt = stmt.where(Match.played_at >= _parse_date(date_from))
    if date_to:
        stmt = stmt.where(Match.played_at <= _parse_date(date_to))
    matches = db.scalars(stmt).all()
    evaluations_by_match_id = get_evaluations_by_match_id(db)
    if goal_status:
        matches = [
            match
            for match in matches
            if (evaluations_by_match_id.get(match.id).status if evaluations_by_match_id.get(match.id) else "baseline")
            == goal_status
        ]
    matches = _sort_matches_for_page(matches, sort, direction)
    per_page = min(max(per_page, 10), 100)
    page = max(page, 1)
    total_matches = len(matches)
    total_pages = max(1, (total_matches + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    paged_matches = matches[offset : offset + per_page]
    maps = db.scalars(
        select(Match.map_name).where(Match.map_name.is_not(None)).distinct().order_by(Match.map_name)
    ).all()
    sources = db.scalars(select(Match.source).where(Match.source.is_not(None)).distinct().order_by(Match.source)).all()
    return templates.TemplateResponse(
        request=request,
        name="matches.html",
        context={
            "request": request,
            "matches": paged_matches,
            "evaluations_by_match_id": evaluations_by_match_id,
            "maps": maps,
            "sources": sources,
            "total_matches": total_matches,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_previous": page > 1,
                "has_next": page < total_pages,
                "previous_page": page - 1,
                "next_page": page + 1,
            },
            "filters": {
                "map_name": map_name or "",
                "result": result or "",
                "source": source or "",
                "goal_status": goal_status or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "sort": sort,
                "direction": direction,
                "per_page": per_page,
            },
            "sort_links": _sort_links(sort, direction),
        },
    )


@router.get("/matches/{match_id}")
def match_detail_page(request: Request, db: Annotated[Session, Depends(get_db)], match_id: int):
    match = db.get(Match, match_id)
    if match is None:
        return RedirectResponse("/matches", status_code=303)
    evaluations_by_match_id = get_evaluations_by_match_id(db)
    all_matches = db.scalars(select(Match).order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    match_mistakes = mistakes_by_match_id(all_matches).get(match.id, [])
    return templates.TemplateResponse(
        request=request,
        name="match_detail.html",
        context={
            "request": request,
            "match": match,
            "detail": match_detail(match),
            "evaluation": evaluations_by_match_id.get(match.id),
            "match_mistakes": match_mistakes,
            "coach_sections": match_coach_sections(match, match_mistakes),
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


@router.post("/coach/ai-handoff")
def generate_ai_handoff_page(db: Annotated[Session, Depends(get_db)]):
    prepare_ai_coach_handoff(db)
    return RedirectResponse("/coach", status_code=303)


@router.post("/coach/ai-result")
def save_ai_result_page(
    db: Annotated[Session, Depends(get_db)],
    ai_result_markdown: Annotated[str, Form()],
    source_ref: Annotated[str | None, Form()] = None,
):
    try:
        save_ai_coach_result(db, ai_result_markdown, source_ref=source_ref)
    except ValueError as exc:
        return RedirectResponse(f"/coach?message={exc}", status_code=303)
    return RedirectResponse("/coach", status_code=303)


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def _sort_matches_for_page(matches: list[Match], sort: str, direction: str) -> list[Match]:
    sort_map = {
        "played_at": lambda match: match.played_at or match.created_at,
        "map": lambda match: match.map_name or "",
        "result": lambda match: match.result or "",
        "source": lambda match: match.source or "",
        "adr": lambda match: match.adr if match.adr is not None else -1,
        "kast": lambda match: match.kast if match.kast is not None else -1,
        "rating": lambda match: match.rating if match.rating is not None else -1,
        "kd": lambda match: match.kd if match.kd is not None else -1,
    }
    key = sort_map.get(sort, sort_map["played_at"])
    reverse = direction != "asc"
    return sorted(matches, key=lambda match: (key(match), match.id or 0), reverse=reverse)


def _sort_links(current_sort: str, current_direction: str) -> dict[str, dict[str, str]]:
    links = {}
    for field in ("played_at", "map", "result", "source", "kd", "adr", "kast", "rating"):
        next_direction = "asc" if current_sort == field and current_direction == "desc" else "desc"
        links[field] = {"sort": field, "direction": next_direction}
    return links
