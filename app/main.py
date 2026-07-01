from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import router as api_router
from app.config import BASE_DIR, get_settings
from app.db.session import SessionLocal, init_db
from app.services.auth import current_user_from_session
from app.services.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, normalize_locale, translate


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
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

    @app.middleware("http")
    async def require_web_auth(request: Request, call_next):
        if _is_public_path(request.url.path):
            return await call_next(request)
        db = SessionLocal()
        try:
            if current_user_from_session(request, db) is None:
                request.session.clear()
                return RedirectResponse("/login", status_code=303)
        finally:
            db.close()
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
        or path == "/robots.txt"
        or path.startswith("/static/")
        or path.startswith("/language/")
        or path.startswith("/api/")
    )


app = create_app()
