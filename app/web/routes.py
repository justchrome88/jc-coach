from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    DemoDuel,
    DemoGrenadeEvent,
    DemoParseArtifact,
    DemoPlayerRound,
    DemoRound,
    DemoWeaponStat,
    ImportJob,
    Match,
)
from app.db.session import SessionLocal, get_db
from app.main import templates
from app.services.ai_coach import (
    ai_provider_health,
    generate_ai_coach_with_provider,
    latest_ai_coach_report,
    latest_ai_handoff,
    list_ai_coach_reports,
    personal_ai_coach_analysis_scope,
    prepare_ai_coach_handoff,
    save_ai_coach_result,
    serialize_ai_coach_report,
)
from app.services.aim_stats import get_aim_profile
from app.services.analytics import (
    chart_series,
    compare_periods,
    get_dashboard_status,
    get_map_stats,
    get_summary,
    match_detail,
)
from app.services.app_settings import set_app_setting
from app.services.auth import authenticate_user, current_user_from_session, login_user, logout_user, register_user
from app.services.coach_rules import build_coach_focus
from app.services.demo_parser import DemoParseError, import_demo_file, import_inbox_demo, list_inbox_demos
from app.services.demo_storage import demo_storage_report, write_demo_storage_manifest
from app.services.i18n import normalize_locale
from app.services.import_jobs import IMPORT_JOB_COMPLETED, IMPORT_JOB_FAILED, IMPORT_JOB_IN_PROGRESS, IMPORT_JOB_QUEUED
from app.services.importer import import_csv, import_json
from app.services.match_queries import is_playable_match, playable_match_select
from app.services.metric_confidence import (
    exact_date_matches,
    exact_recent_matches,
    is_exact_date_match,
    metric_context,
    sort_matches,
)
from app.services.metric_truth import metric_definition, metric_warning, usage_decision
from app.services.mistake_detection import (
    category_scorecard,
    detect_structured_mistakes,
    match_coach_sections,
    mistakes_by_match_id,
)
from app.services.recommendation_tracking import (
    extend_recommendation_target,
    get_active_recommendation_progress,
    get_all_recommendation_progress,
    get_evaluations_by_match_id,
    list_recommendation_history,
    recommendation_category_summary,
    restart_recommendation_category,
    update_recommendation_status,
)
from app.services.report_generator import generate_report, latest_report, markdown_to_html
from app.services.steam_demo_downloader import steam_demo_downloader_configured
from app.services.steam_integration import (
    clear_steam_demo_download_errors,
    create_steam_import_job,
    import_steam_share_code_demo,
    link_steam_account,
    list_steam_accounts,
    list_visible_steam_import_jobs,
    mark_steam_import_all_job_interrupted,
    match_date_truth,
    process_queued_steam_jobs,
    queue_match_history_sync,
    queue_steam_import_all,
    run_steam_import_all_job,
    steam_import_overview,
    steam_login_url,
    sync_match_history_job,
    update_match_auth_code,
    validate_openid_callback,
)

router = APIRouter()


def _run_steam_import_all_background(job_id: int) -> None:
    db = SessionLocal()
    try:
        run_steam_import_all_job(db, job_id)
    except BaseException as exc:
        job = db.get(ImportJob, job_id)
        if job is not None and job.status == IMPORT_JOB_IN_PROGRESS:
            mark_steam_import_all_job_interrupted(
                db,
                job,
                reason=f"steam_import_all background task was interrupted: {type(exc).__name__}",
            )
        raise
    finally:
        db.close()


@router.get("/")
def landing_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    if current_user_from_session(request, db):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="landing.html", context={"request": request})


@router.get("/login")
def login_page(request: Request, db: Annotated[Session, Depends(get_db)], message: str | None = None):
    if current_user_from_session(request, db):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "message": message},
    )


@router.post("/login")
def login_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    user = authenticate_user(db, email, password)
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request, "message": "Неверный email или пароль."},
            status_code=400,
        )
    login_user(request, user)
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/register")
def register_page(request: Request, db: Annotated[Session, Depends(get_db)], message: str | None = None):
    if current_user_from_session(request, db):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"request": request, "message": message},
    )


@router.post("/register")
def register_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    display_name: Annotated[str | None, Form()] = None,
):
    try:
        user = register_user(db, email, password, display_name=display_name)
    except ValueError as exc:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"request": request, "message": str(exc)},
            status_code=400,
        )
    login_user(request, user)
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
def logout_submit(request: Request):
    logout_user(request)
    return RedirectResponse("/", status_code=303)


@router.get("/dashboard")
def dashboard(request: Request, db: Annotated[Session, Depends(get_db)]):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    matches = db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    context = metric_context(matches)
    summary = get_summary(matches, date_windowed=True, context=context)
    comparison = compare_periods(matches, context=context)
    map_stats = get_map_stats(matches, context=context)
    dashboard_status = get_dashboard_status(matches, context=context)
    aim_profile = get_aim_profile(matches, context=context)
    recommendation_progress = get_active_recommendation_progress(db)
    all_recommendation_progress = get_all_recommendation_progress(db)
    evaluations_by_match_id = get_evaluations_by_match_id(db)
    recent_matches = list(reversed(exact_recent_matches(matches, 10, context=context)))
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "summary": summary,
            "comparison": comparison,
            "map_stats": map_stats,
            "dashboard_status": dashboard_status,
            "aim_profile": aim_profile,
            "recommendation_progress": recommendation_progress,
            "all_recommendation_progress": all_recommendation_progress,
            "evaluations_by_match_id": evaluations_by_match_id,
            "recent_matches": recent_matches,
            "chart_data": chart_series(matches, context=context),
        },
    )


@router.get("/language/{locale}")
def set_language(request: Request, locale: str):
    target_locale = normalize_locale(locale)
    next_url = request.headers.get("referer") or "/"
    response = RedirectResponse(next_url, status_code=303)
    response.set_cookie("locale", target_locale, max_age=60 * 60 * 24 * 365, samesite="lax")
    return response


@router.get("/stats")
def stats_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    range_type: str = "last",
    matches_count: int = 30,
    date_from: str | None = None,
    date_to: str | None = None,
):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    all_matches = db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    all_context = metric_context(all_matches)
    selected_matches = _select_stats_matches(
        all_matches,
        range_type,
        matches_count,
        date_from,
        date_to,
        context=all_context,
    )
    selected_context = metric_context(selected_matches)
    summary = get_summary(selected_matches, date_windowed=range_type != "all", context=selected_context)
    comparison = compare_periods(selected_matches, context=selected_context)
    dashboard_status = get_dashboard_status(selected_matches, context=selected_context)
    aim_profile = get_aim_profile(selected_matches, context=selected_context)
    map_stats = get_map_stats(selected_matches, context=selected_context)
    recent_matches = list(reversed(exact_recent_matches(selected_matches, 12, context=selected_context)))
    return templates.TemplateResponse(
        request=request,
        name="stats.html",
        context={
            "request": request,
            "summary": summary,
            "comparison": comparison,
            "dashboard_status": dashboard_status,
            "aim_profile": aim_profile,
            "map_stats": map_stats,
            "recent_matches": recent_matches,
            "chart_data": chart_series(selected_matches, context=selected_context),
            "filters": {
                "range_type": range_type if range_type in {"last", "dates", "all"} else "last",
                "matches_count": min(max(matches_count, 1), 500),
                "date_from": date_from or "",
                "date_to": date_to or "",
            },
            "total_matches": len(all_matches),
        },
    )


@router.get("/coach")
def coach_page(request: Request, db: Annotated[Session, Depends(get_db)], message: str | None = None):
    matches = db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    context = metric_context(matches)
    exact_matches = exact_date_matches(matches, context=context)
    summary = get_summary(matches, date_windowed=True, context=context)
    comparison = compare_periods(matches, context=context)
    map_stats = get_map_stats(matches, context=context)
    focus = build_coach_focus(summary, comparison, map_stats)
    structured_mistakes = detect_structured_mistakes(exact_matches)
    coach_categories = category_scorecard(structured_mistakes)
    recommendation_progress = get_active_recommendation_progress(db)
    all_recommendation_progress = get_all_recommendation_progress(db)
    evaluations_by_match_id = get_evaluations_by_match_id(db)
    evaluated_matches = [
        match
        for match in reversed(exact_matches)
        if match.id in evaluations_by_match_id
    ][:10]
    report = latest_report(db)
    ai_handoff = latest_ai_handoff()
    ai_report = latest_ai_coach_report(db)
    ai_health = ai_provider_health()
    aim_profile = get_aim_profile(matches, context=context)
    ai_report_history = [serialize_ai_coach_report(report) for report in list_ai_coach_reports(db, limit=5)]
    recommendation_history = list_recommendation_history(db, limit=20)
    recommendation_categories = recommendation_category_summary(db)
    parse_overview = _demo_parse_overview(db, len(matches))
    coach_ui = _coach_first_view_model(
        matches=exact_matches,
        recommendation_progress=recommendation_progress,
        evaluations_by_match_id=evaluations_by_match_id,
        ai_report=ai_report,
    )
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
            "ai_report_history": ai_report_history,
            "ai_health": ai_health,
            "aim_profile": aim_profile,
            "recommendation_history": recommendation_history,
            "recommendation_categories": recommendation_categories,
            "parse_overview": parse_overview,
            "coach_ui": coach_ui,
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
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    return templates.TemplateResponse(
        request=request,
        name="import_settings.html",
        context={
            "request": request,
            "message": message,
            "steam_accounts": list_steam_accounts(db),
            "import_jobs": list_visible_steam_import_jobs(db),
            "steam_import_overview": steam_import_overview(db),
            "steam_demo_downloader_configured": steam_demo_downloader_configured(),
        },
    )


@router.get("/settings/storage")
def storage_settings_page(request: Request, db: Annotated[Session, Depends(get_db)], message: str | None = None):
    return templates.TemplateResponse(
        request=request,
        name="storage_settings.html",
        context={
            "request": request,
            "message": message,
            "storage_report": demo_storage_report(db),
        },
    )


@router.post("/settings/storage/manifest")
def write_storage_manifest(db: Annotated[Session, Depends(get_db)]):
    report = write_demo_storage_manifest(db)
    message = f"Manifest updated: {report['manifest_path']}"
    return RedirectResponse(f"/settings/storage?message={quote(message)}", status_code=303)


@router.get("/auth/steam")
def steam_auth_start(request: Request, db: Annotated[Session, Depends(get_db)]):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    return RedirectResponse(steam_login_url(), status_code=303)


@router.get("/auth/steam/callback")
def steam_auth_callback(request: Request, db: Annotated[Session, Depends(get_db)]):
    owner = current_user_from_session(request, db)
    if owner is None:
        message = "Sign in as the owner before linking Steam."
        return RedirectResponse(f"/settings/imports?message={quote(message)}", status_code=303)
    steam_id, error = validate_openid_callback(dict(request.query_params))
    if error:
        return RedirectResponse(f"/settings/imports?message={quote(error)}", status_code=303)
    account = link_steam_account(db, steam_id, user_id=owner.id)
    create_steam_import_job(db, account.id, "steam_openid_linked", {"steam_id": steam_id, "owner_user_id": owner.id})
    return RedirectResponse("/settings/imports?message=Steam%20account%20linked.", status_code=303)


@router.post("/settings/imports/steam-web-api-key")
def save_steam_web_api_key(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    steam_web_api_key: Annotated[str, Form()],
):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    try:
        set_app_setting(db, "steam_web_api_key", steam_web_api_key)
    except ValueError as exc:
        return RedirectResponse(f"/settings/imports?message={quote(str(exc))}", status_code=303)
    return RedirectResponse("/settings/imports?message=Steam%20Web%20API%20key%20saved.", status_code=303)


@router.post("/settings/imports/steam/{steam_account_id}/auth-code")
def save_steam_auth_code(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    steam_account_id: int,
    match_auth_code: Annotated[str, Form()],
    latest_share_code: Annotated[str, Form()],
):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    try:
        update_match_auth_code(db, steam_account_id, match_auth_code, latest_share_code)
    except ValueError as exc:
        return RedirectResponse(f"/settings/imports?message={quote(str(exc))}", status_code=303)
    return RedirectResponse("/settings/imports?message=Steam%20codes%20saved.", status_code=303)


@router.post("/settings/imports/steam/{steam_account_id}/share-code")
def import_steam_share_code(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    steam_account_id: int,
    share_code: Annotated[str, Form()],
):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    try:
        result = import_steam_share_code_demo(db, steam_account_id, share_code)
    except ValueError as exc:
        return RedirectResponse(f"/settings/imports?message={quote(str(exc))}", status_code=303)
    demo_download = result.get("demo_download") or {}
    if demo_download.get("configured") is False:
        message = f"Share code saved, but demo bot is not configured: {demo_download.get('message')}"
    elif demo_download.get("imported"):
        message = f"Imported demo for {result['share_code']}."
    else:
        message = f"Queued demo for {result['share_code']}."
    return RedirectResponse(f"/settings/imports?message={quote(str(message))}", status_code=303)


@router.post("/settings/imports/steam/{steam_account_id}/sync")
def queue_steam_sync(request: Request, db: Annotated[Session, Depends(get_db)], steam_account_id: int):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    try:
        queue_match_history_sync(db, steam_account_id)
    except ValueError as exc:
        return RedirectResponse(f"/settings/imports?message={quote(str(exc))}", status_code=303)
    return RedirectResponse("/settings/imports?message=Steam%20sync%20queued.", status_code=303)


@router.post("/settings/imports/jobs/{job_id}/run")
def run_steam_import_job(request: Request, db: Annotated[Session, Depends(get_db)], job_id: int):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    try:
        result = sync_match_history_job(db, job_id)
    except ValueError as exc:
        return RedirectResponse(f"/settings/imports?message={quote(str(exc))}", status_code=303)
    message = result.get("error") or f"Job {job_id} {result.get('status')}"
    return RedirectResponse(f"/settings/imports?message={quote(str(message))}", status_code=303)


@router.post("/settings/imports/run-queued")
def run_queued_steam_import_jobs(request: Request, db: Annotated[Session, Depends(get_db)]):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    results = process_queued_steam_jobs(db)
    succeeded = sum(1 for item in results if item.get("status") == IMPORT_JOB_COMPLETED)
    failed = sum(1 for item in results if item.get("status") == IMPORT_JOB_FAILED)
    message = f"Processed {len(results)} Steam jobs: {succeeded} succeeded, {failed} failed."
    return RedirectResponse(
        f"/settings/imports?message={quote(message)}",
        status_code=303,
    )


@router.post("/settings/imports/pull-all")
def pull_all_steam_imports(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    job = queue_steam_import_all(db)
    if job.status in {IMPORT_JOB_QUEUED, IMPORT_JOB_IN_PROGRESS}:
        if job.status == IMPORT_JOB_QUEUED:
            background_tasks.add_task(_run_steam_import_all_background, job.id)
        message = f"Steam import job #{job.id} started. This page will show progress."
    else:
        message = f"Steam import job #{job.id} is already {job.status}."
    return RedirectResponse(f"/settings/imports?message={quote(str(message))}", status_code=303)


@router.post("/settings/imports/clear-demo-errors")
def clear_steam_demo_errors(request: Request, db: Annotated[Session, Depends(get_db)]):
    auth_redirect = _require_user_redirect(request, db)
    if auth_redirect:
        return auth_redirect
    result = clear_steam_demo_download_errors(db)
    message = f"Cleared {result['cleared']} old demo download errors."
    return RedirectResponse(f"/settings/imports?message={quote(message)}", status_code=303)


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
    stmt = playable_match_select()
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
    date_truth_by_match_id = {match.id: match_date_truth(match) for match in paged_matches}
    maps = db.scalars(
        playable_match_select().with_only_columns(Match.map_name).where(Match.map_name.is_not(None)).distinct().order_by(Match.map_name)
    ).all()
    sources = db.scalars(
        playable_match_select().with_only_columns(Match.source).where(Match.source.is_not(None)).distinct().order_by(Match.source)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="matches.html",
        context={
            "request": request,
            "matches": paged_matches,
            "date_truth_by_match_id": date_truth_by_match_id,
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
    if match is None or not is_playable_match(match):
        return RedirectResponse("/matches", status_code=303)
    evaluations_by_match_id = get_evaluations_by_match_id(db)
    all_matches = db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    match_mistakes = mistakes_by_match_id(all_matches).get(match.id, [])
    return templates.TemplateResponse(
        request=request,
        name="match_detail.html",
        context={
            "request": request,
            "match": match,
            "detail": match_detail(match),
            "date_truth": match_date_truth(match),
            "parse_summary": _demo_parse_summary(db, match.id),
            "evaluation": evaluations_by_match_id.get(match.id),
            "match_mistakes": match_mistakes,
            "coach_sections": match_coach_sections(match, match_mistakes),
        },
    )


def _demo_parse_summary(db: Session, match_id: int) -> dict:
    artifact = db.scalar(select(DemoParseArtifact).where(DemoParseArtifact.match_id == match_id))
    if artifact is None:
        return {"available": False}
    rounds = db.scalars(select(DemoRound).where(DemoRound.match_id == match_id).order_by(DemoRound.round_number)).all()
    player_rounds = db.scalars(
        select(DemoPlayerRound).where(DemoPlayerRound.match_id == match_id).order_by(DemoPlayerRound.round_number)
    ).all()
    weapons = db.scalars(
        select(DemoWeaponStat)
        .where(DemoWeaponStat.match_id == match_id)
        .order_by(DemoWeaponStat.kills.desc(), DemoWeaponStat.damage.desc())
    ).all()
    duels = db.scalars(select(DemoDuel).where(DemoDuel.match_id == match_id).order_by(DemoDuel.tick.asc())).all()
    grenades = db.scalars(
        select(DemoGrenadeEvent)
        .where(DemoGrenadeEvent.match_id == match_id)
        .order_by(DemoGrenadeEvent.round_number.asc(), DemoGrenadeEvent.tick.asc())
    ).all()
    target_player = _artifact_target_player(artifact)
    target_weapons = [
        weapon
        for weapon in weapons
        if not target_player
        or weapon.player_steamid == target_player.get("steamid")
        or weapon.player_name == target_player.get("name")
    ][:8]
    target_rounds = [
        row
        for row in player_rounds
        if not target_player
        or row.player_steamid == target_player.get("steamid")
        or row.player_name == target_player.get("name")
    ]
    return {
        "available": True,
        "artifact": artifact,
        "target_player": target_player or {},
        "counts": {
            "rounds": len(rounds),
            "player_rounds": len(player_rounds),
            "duels": len(duels),
            "grenades": len(grenades),
            "weapons": len(weapons),
        },
        "target": {
            "rounds": len(target_rounds),
            "kills": sum(row.kills for row in target_rounds),
            "deaths": sum(row.deaths for row in target_rounds),
            "damage": sum(row.damage for row in target_rounds),
            "utility_damage": sum(row.utility_damage for row in target_rounds),
            "enemies_flashed": sum(row.enemies_flashed for row in target_rounds),
            "opening_kills": sum(row.opening_kill for row in target_rounds),
            "opening_deaths": sum(row.opening_death for row in target_rounds),
        },
        "top_weapons": target_weapons,
        "recent_grenades": grenades[:12],
        "first_duels": [duel for duel in duels if duel.opening_duel][:8],
    }


def _artifact_target_player(artifact: DemoParseArtifact) -> dict | None:
    try:
        payload = json.loads(artifact.payload_json)
    except (TypeError, ValueError):
        return None
    player = payload.get("player") or {}
    if not player:
        return None
    return {"name": player.get("name"), "steamid": str(player.get("steamid")) if player.get("steamid") else None}


def _demo_parse_overview(db: Session, total_matches: int) -> dict:
    artifacts = db.scalars(select(DemoParseArtifact).order_by(DemoParseArtifact.parsed_at.desc())).all()
    weapons = db.scalars(select(DemoWeaponStat)).all()
    rounds = db.scalars(select(DemoRound)).all()
    duels = db.scalars(select(DemoDuel)).all()
    grenades = db.scalars(select(DemoGrenadeEvent)).all()
    weapon_buckets: dict[str, dict] = {}
    for weapon in weapons:
        item = weapon_buckets.setdefault(
            weapon.weapon,
            {"weapon": weapon.weapon, "shots": 0, "hits": 0, "kills": 0, "damage": 0},
        )
        item["shots"] += weapon.shots
        item["hits"] += weapon.hits
        item["kills"] += weapon.kills
        item["damage"] += weapon.damage
    top_weapons = sorted(weapon_buckets.values(), key=lambda item: (item["kills"], item["damage"]), reverse=True)[:8]
    for item in top_weapons:
        item["accuracy"] = round(item["hits"] / item["shots"] * 100, 2) if item["shots"] else None
    return {
        "matches_total": total_matches,
        "matches_parsed": len(artifacts),
        "coverage": round(len(artifacts) / total_matches * 100, 2) if total_matches else 0,
        "rounds": len(rounds),
        "duels": len(duels),
        "grenades": len(grenades),
        "weapon_profiles": len(weapons),
        "top_weapons": top_weapons,
        "latest": artifacts[0] if artifacts else None,
    }


def _coach_first_view_model(
    matches: list[Match],
    recommendation_progress: dict | None,
    evaluations_by_match_id: dict[int, object],
    ai_report,
) -> dict:
    latest_match = matches[-1] if matches else None
    latest_evaluation = evaluations_by_match_id.get(latest_match.id) if latest_match and latest_match.id else None
    current = _current_recommendation_card(recommendation_progress)
    return {
        "current": current,
        "latest_match": _latest_match_summary(latest_match, latest_evaluation),
        "ai_validation": _ai_validation_status(ai_report),
        "weak_metric_notes": _weak_metric_notes(),
    }


def _current_recommendation_card(recommendation_progress: dict | None) -> dict:
    if not recommendation_progress:
        return {
            "available": False,
            "next_action": "Импортируйте матчи и создайте tracked recommendation через явный write path.",
            "evidence": [],
            "last_evaluation": None,
        }
    recommendation = recommendation_progress["recommendation"]
    category = recommendation.category
    metrics = _recommendation_metric_ids(category)
    evaluations = recommendation_progress.get("evaluations") or []
    last_evaluation = evaluations[-1] if evaluations else None
    return {
        "available": True,
        "label": "Current tracked recommendation",
        "not_planner_label": "Это текущая отслеживаемая цель, не verified top problem.",
        "health": recommendation_progress.get("health") or {},
        "legacy_label": (recommendation_progress.get("health") or {}).get("label"),
        "needs_refresh": bool((recommendation_progress.get("health") or {}).get("needs_refresh")),
        "accepted_for_hard_progress": bool(
            (recommendation_progress.get("health") or {}).get("accepted_for_hard_progress", True)
        ),
        "category": category,
        "title": recommendation.title,
        "description": recommendation.description,
        "status": recommendation.status,
        "progress_score": recommendation_progress["progress_score"],
        "completed_matches": recommendation_progress["completed_matches"],
        "target_matches": recommendation_progress["target_matches"],
        "counts": recommendation_progress["counts"],
        "summary": recommendation_progress["summary"],
        "next_action": _next_match_action(category),
        "success_rule": _first_json_item(recommendation.success_rules_json),
        "failure_rule": _first_json_item(recommendation.failure_rules_json),
        "last_comment": recommendation_progress["last_comment"],
        "last_evaluation": _evaluation_summary(last_evaluation),
        "baseline_confidence": (recommendation_progress.get("baseline") or {}).get("confidence", {}),
        "evidence": [
            _metric_evidence_item(
                metric_id,
                recommendation_progress.get("baseline") or {},
                recommendation_progress.get("current") or {},
                recommendation_progress.get("target") or {},
            )
            for metric_id in metrics
        ],
    }


def _recommendation_metric_ids(category: str) -> list[str]:
    if category == "aim":
        return ["adr", "kast", "headshot_rate", "entry_kills"]
    if category == "grenades":
        return ["utility_damage", "flash_assists", "grenade_rating"]
    if category == "map":
        return ["result", "entry_deaths", "adr", "side_split_metrics"]
    return ["entry_deaths", "early_deaths", "kast", "adr"]


def _metric_evidence_item(metric_id: str, baseline: dict, current: dict, target: dict) -> dict:
    definition = metric_definition(metric_id)
    value_key = _metric_value_key(metric_id)
    warning = metric_warning(metric_id, "recommendation")
    confidence = ((baseline.get("confidence") or {}).get("metrics") or {}).get(definition.metric_id)
    return {
        "metric_id": definition.metric_id,
        "name": definition.display_name,
        "reliability": definition.reliability,
        "decision": usage_decision(definition.metric_id, "recommendation"),
        "baseline": baseline.get(value_key),
        "current": current.get(value_key),
        "target": target.get(value_key) or target.get(definition.metric_id),
        "warning": warning,
        "confidence": confidence or {},
    }


def _metric_value_key(metric_id: str) -> str:
    mapping = {
        "kd_ratio": "kd",
        "entry_deaths": "entry_deaths_per_match",
        "early_deaths": "early_deaths_per_match",
        "result": "winrate",
        "headshot_rate": "headshot_percent",
    }
    return mapping.get(metric_id, metric_id)


def _next_match_action(category: str) -> str:
    actions = {
        "aim": "В следующем матче держите ADR не ниже baseline и не просаживайте KAST.",
        "grenades": "В следующем матче заранее выберите 2-3 повторяемые гранаты для opening/retake.",
        "map": "В следующем матче играйте карту с понятным планом и избегайте раннего развала раунда.",
        "survival": "В следующем матче первые 20 секунд играйте на размен и не отдавайте первый контакт без поддержки.",
    }
    return actions.get(
        category,
        "В следующем матче выполните текущую tracked recommendation и проверьте оценку после импорта.",
    )


def _evaluation_summary(evaluation) -> dict | None:
    if evaluation is None:
        return None
    return {
        "status": evaluation.status,
        "score": evaluation.score,
        "comment": evaluation.coach_comment,
        "evaluated_at": evaluation.evaluated_at,
    }


def _latest_match_summary(match: Match | None, evaluation) -> dict:
    if match is None:
        return {"available": False, "message": "Матчей пока нет. Импортируйте CSV, JSON или DEM."}
    return {
        "available": True,
        "date": match.played_at,
        "map_name": match.map_name or "n/a",
        "result": match.result or "n/a",
        "score": f"{match.rounds_for or 0}:{match.rounds_against or 0}",
        "adr": match.adr,
        "kast": match.kast,
        "entry_deaths": match.entry_deaths,
        "evaluation": _evaluation_summary(evaluation),
    }


def _ai_validation_status(ai_report) -> dict:
    if ai_report is None:
        return {
            "available": False,
            "label": "AI-отчёта пока нет",
            "detail": "AI не запускается на page render; подготовьте handoff или сохраните результат вручную.",
            "status_class": "gray",
        }
    metadata = _json_loads(ai_report.report_json)
    validation = metadata.get("ai_validation") if isinstance(metadata.get("ai_validation"), dict) else None
    if validation is None:
        return {
            "available": True,
            "label": "Validation status unknown",
            "detail": "Отчёт сохранён до Stage 8 или без validation metadata.",
            "status_class": "yellow",
        }
    if validation.get("valid") is True:
        return {
            "available": True,
            "label": "Valid structured AI report",
            "detail": "Структура и Metric Truth usage прошли validator.",
            "status_class": "green",
        }
    return {
        "available": True,
        "label": "Fallback AI report",
        "detail": "Исходный AI output отклонён validator; показан safe fallback.",
        "status_class": "red",
    }


def _weak_metric_notes() -> list[dict[str, str]]:
    return [
        _weak_metric_note("early_deaths", "recommendation"),
        _weak_metric_note("trade_kills", "recommendation"),
        _weak_metric_note("side_split_metrics", "recommendation"),
        _weak_metric_note("traded_deaths", "recommendation"),
    ]


def _weak_metric_note(metric_id: str, usage: str) -> dict[str, str]:
    definition = metric_definition(metric_id)
    return {
        "metric_id": definition.metric_id,
        "name": definition.display_name,
        "reliability": definition.reliability,
        "decision": usage_decision(definition.metric_id, usage),
        "warning": metric_warning(definition.metric_id, usage) or "Allowed for current usage.",
    }


def _first_json_item(raw_json: str | None) -> str | None:
    items = _json_loads(raw_json)
    if isinstance(items, list) and items:
        return str(items[0])
    return None


def _json_loads(value: str | None):
    if not value:
        return {}
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return {}


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
def generate_ai_handoff_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    owner = current_user_from_session(request, db)
    prepare_ai_coach_handoff(
        db,
        analysis_scope=personal_ai_coach_analysis_scope(db, user_id=owner.id if owner else None),
    )
    return RedirectResponse("/coach", status_code=303)


@router.post("/coach/ai-result")
def save_ai_result_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    ai_result_markdown: Annotated[str, Form()],
    source_ref: Annotated[str | None, Form()] = None,
):
    try:
        owner = current_user_from_session(request, db)
        save_ai_coach_result(
            db,
            ai_result_markdown,
            source_ref=source_ref,
            user_id=owner.id if owner else None,
            analysis_scope=personal_ai_coach_analysis_scope(db, user_id=owner.id if owner else None),
        )
    except ValueError as exc:
        return RedirectResponse(f"/coach?message={exc}", status_code=303)
    return RedirectResponse("/coach", status_code=303)


@router.post("/coach/ai-generate")
def generate_ai_result_with_provider_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    try:
        owner = current_user_from_session(request, db)
        generate_ai_coach_with_provider(
            db,
            analysis_scope=personal_ai_coach_analysis_scope(db, user_id=owner.id if owner else None),
        )
    except RuntimeError as exc:
        return RedirectResponse(f"/coach?message={exc}", status_code=303)
    return RedirectResponse("/coach", status_code=303)


@router.post("/coach/recommendations/{recommendation_id}/status")
def update_recommendation_status_page(
    db: Annotated[Session, Depends(get_db)],
    recommendation_id: int,
    status: Annotated[str, Form()],
):
    try:
        update_recommendation_status(db, recommendation_id, status)
    except ValueError as exc:
        return RedirectResponse(f"/coach?message={exc}", status_code=303)
    return RedirectResponse("/coach", status_code=303)


@router.post("/coach/recommendations/{recommendation_id}/extend")
def extend_recommendation_page(
    db: Annotated[Session, Depends(get_db)],
    recommendation_id: int,
    additional_matches: Annotated[int, Form()] = 5,
):
    try:
        extend_recommendation_target(db, recommendation_id, additional_matches)
    except ValueError as exc:
        return RedirectResponse(f"/coach?message={exc}", status_code=303)
    return RedirectResponse("/coach", status_code=303)


@router.post("/coach/recommendations/category/{category}/restart")
def restart_recommendation_category_page(db: Annotated[Session, Depends(get_db)], category: str):
    try:
        restart_recommendation_category(db, category)
    except ValueError as exc:
        return RedirectResponse(f"/coach?message={exc}", status_code=303)
    return RedirectResponse("/coach", status_code=303)


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def _require_user_redirect(request: Request, db: Session) -> RedirectResponse | None:
    return None if current_user_from_session(request, db) else RedirectResponse("/login", status_code=303)


def _select_stats_matches(
    matches: list[Match],
    range_type: str,
    matches_count: int,
    date_from: str | None,
    date_to: str | None,
    *,
    context=None,
) -> list[Match]:
    sorted_matches = sort_matches(matches)
    if range_type == "all":
        return sorted_matches
    if range_type == "dates":
        selected = sorted_matches
        if date_from:
            selected = [
                match
                for match in selected
                if (
                    is_exact_date_match(match, context=context)
                    and match.played_at
                    and match.played_at >= _parse_date(date_from)
                )
            ]
        if date_to:
            selected = [
                match
                for match in selected
                if (
                    is_exact_date_match(match, context=context)
                    and match.played_at
                    and match.played_at <= _parse_date(date_to)
                )
            ]
        return selected
    safe_count = min(max(matches_count, 1), 500)
    return exact_recent_matches(sorted_matches, safe_count, context=context)


def _sort_matches_for_page(matches: list[Match], sort: str, direction: str) -> list[Match]:
    sort_map = {
        "played_at": lambda match: match.played_at or match.created_at,
        "map": lambda match: match.map_name or "",
        "result": lambda match: match.result or "",
        "source": lambda match: match.source or "",
        "adr": lambda match: match.adr if match.adr is not None else -1,
        "kast": lambda match: match.kast if match.kast is not None else -1,
        "rating": lambda match: match.rating if match.rating is not None else -1,
        "swing_score": lambda match: match.swing_score if match.swing_score is not None else -999,
        "kd": lambda match: match.kd if match.kd is not None else -1,
    }
    key = sort_map.get(sort, sort_map["played_at"])
    reverse = direction != "asc"
    return sorted(matches, key=lambda match: (key(match), match.id or 0), reverse=reverse)


def _sort_links(current_sort: str, current_direction: str) -> dict[str, dict[str, str]]:
    links = {}
    for field in ("played_at", "map", "result", "source", "kd", "adr", "kast", "rating", "swing_score"):
        next_direction = "asc" if current_sort == field and current_direction == "desc" else "desc"
        links[field] = {"sort": field, "direction": next_direction}
    return links
