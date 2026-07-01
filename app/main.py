from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router as api_router
from app.config import BASE_DIR, get_settings
from app.db.session import init_db

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    from app.web.routes import router as web_router

    app.include_router(api_router)
    app.include_router(web_router)
    return app


app = create_app()
