from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import router as api_router
from app.config import BASE_DIR, get_settings
from app.db.session import SessionLocal, init_db
from app.services.auth import current_user_from_session
from app.services.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, normalize_locale, translate
from app.services.security import (
    csrf_token,
    has_valid_api_token,
    has_valid_csrf,
    log_security_event,
    rate_limit_bucket,
    rate_limit_key,
    rate_limiter,
)


def _template_context(request: Request) -> dict[str, object]:
    locale = normalize_locale(request.cookies.get("locale") or request.query_params.get("lang"))
    current_user = None
    if "user_id" in request.session:
        db = SessionLocal()
        try:
            current_user = current_user_from_session(request, db)
        finally:
            db.close()
    return {
        "locale": locale,
        "current_user": current_user,
        "csrf_token": csrf_token(request),
        "supported_locales": SUPPORTED_LOCALES,
        "default_locale": DEFAULT_LOCALE,
        "t": lambda key: translate(locale, key),
    }


templates = Jinja2Templates(
    directory=str(BASE_DIR / "app" / "templates"),
    context_processors=[_template_context],
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    settings = get_settings()
    if settings.steam_import_repair_stale_on_startup:
        from app.services.steam_integration import run_startup_stale_steam_import_repair

        db = SessionLocal()
        try:
            run_startup_stale_steam_import_repair(db)
        finally:
            db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

    @app.middleware("http")
    async def enforce_security(request: Request, call_next):
        path = request.url.path
        bucket = rate_limit_bucket(path, request.method)
        if bucket:
            bucket_name, limit = bucket
            if not rate_limiter.allow(rate_limit_key(request, bucket_name), limit):
                log_security_event("rate_limited", request, bucket=bucket_name)
                if path.startswith("/api/"):
                    return JSONResponse({"detail": "Rate limit exceeded."}, status_code=429)
                return PlainTextResponse("Rate limit exceeded.", status_code=429)

        if path.startswith("/api/"):
            db = SessionLocal()
            try:
                current_user = current_user_from_session(request, db)
            finally:
                db.close()
            api_token_valid = has_valid_api_token(request, settings.api_token)
            if current_user is None and not api_token_valid:
                log_security_event("api_auth_required", request)
                return JSONResponse({"detail": "Authentication required."}, status_code=401)
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                log_security_event("api_state_change", request, api_token=api_token_valid)
                if current_user is not None and not api_token_valid and not await has_valid_csrf(request):
                    return JSONResponse({"detail": "CSRF token missing or invalid."}, status_code=403)
            return await call_next(request)

        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not await has_valid_csrf(request):
            log_security_event("csrf_rejected", request)
            return PlainTextResponse("CSRF token missing or invalid.", status_code=403)

        if _is_public_path(path):
            return await call_next(request)
        db = SessionLocal()
        try:
            if current_user_from_session(request, db) is None:
                request.session.clear()
                return RedirectResponse("/login", status_code=303)
        finally:
            db.close()
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            log_security_event("web_state_change", request)
        return await call_next(request)

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        https_only=settings.auth_cookie_secure,
        same_site="lax",
        max_age=60 * 60 * 24 * 30,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/robots.txt", response_class=PlainTextResponse)
    def robots_txt() -> str:
        return "User-agent: *\nDisallow: /\n"

    from app.web.routes import router as web_router

    app.include_router(api_router)
    app.include_router(web_router)
    return app


def _is_public_path(path: str) -> bool:
    return (
        path == "/"
        or path == "/login"
        or path == "/register"
        or path == "/health"
        or path == "/favicon.ico"
        or path == "/robots.txt"
        or path.startswith("/static/")
        or path.startswith("/language/")
        or path == "/auth/steam/callback"
    )


app = create_app()
