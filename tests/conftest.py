# ruff: noqa: E402, I001

import os
import tempfile
from collections.abc import MutableMapping
from collections.abc import Generator
from contextlib import AbstractAsyncContextManager
from io import BytesIO
from pathlib import Path
from types import TracebackType
from typing import Any
from urllib.parse import unquote

import anyio
import anyio.to_thread
import fastapi.testclient
import httpx
import pytest
import starlette.testclient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

TEST_RUNTIME_ROOT = Path(tempfile.gettempdir()) / f"jc-coach-pytest-{os.getpid()}"
TEST_DB_PATH = TEST_RUNTIME_ROOT / "cs2_coach_test.db"

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["APP_ENV"] = "test"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
os.environ.setdefault("UPLOAD_DIR", str(TEST_RUNTIME_ROOT / "uploads"))
os.environ.setdefault("DEMO_INBOX_DIR", str(TEST_RUNTIME_ROOT / "incoming_demos"))
os.environ.setdefault("TEMP_DIR", str(TEST_RUNTIME_ROOT / "tmp"))
os.environ.setdefault("REPORTS_DIR", str(TEST_RUNTIME_ROOT / "reports"))
os.environ.setdefault("AI_HANDOFF_DIR", str(TEST_RUNTIME_ROOT / "ai_handoffs"))
os.environ.setdefault("SESSION_SECRET_KEY", "pytest-only-session-secret")
os.environ.setdefault("AUTH_COOKIE_SECURE", "false")
os.environ.setdefault("STEAM_IMPORT_MIN_FREE_BYTES", "0")
os.environ.setdefault("STEAM_IMPORT_PRESERVE_FREE_BYTES", "0")
os.environ.setdefault("STEAM_IMPORT_MAX_BYTES_PER_JOB", str(64 * 1024 * 1024))
os.environ.setdefault("STEAM_IMPORT_MAX_SINGLE_DEMO_BYTES", str(16 * 1024 * 1024))
os.environ.setdefault("STEAM_IMPORT_UNKNOWN_DEMO_RESERVE_BYTES", str(1024 * 1024))

# App imports must happen after test env vars are set.
from app.config import assert_test_database_not_production
from app.db.models import Match
from app.db.session import Base, engine
from app.services.owner.security import rate_limiter

assert_test_database_not_production(os.environ["DATABASE_URL"], context="pytest configuration")


async def _run_sync_inline(func, *args, abandon_on_cancel=False, cancellable=None, limiter=None):
    return func(*args)


anyio.to_thread.run_sync = _run_sync_inline


class _AnyIORunASGITransport(httpx.BaseTransport):
    def __init__(self, app: Any, raise_server_exceptions: bool, root_path: str, client: tuple[str, int]) -> None:
        self._app = app
        self._raise_server_exceptions = raise_server_exceptions
        self._root_path = root_path
        self._client = client

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request_body = request.read()

        async def run_request() -> tuple[int, list[tuple[str, str]], bytes]:
            scheme = request.url.scheme
            host = request.url.host or "testserver"
            port = request.url.port or (443 if scheme == "https" else 80)
            headers = [(key.lower(), value) for key, value in request.headers.raw]
            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": request.method,
                "path": unquote(request.url.path),
                "raw_path": request.url.raw_path.split(b"?", 1)[0],
                "root_path": self._root_path,
                "scheme": scheme,
                "query_string": request.url.query,
                "headers": headers,
                "client": self._client,
                "server": (host, port),
                "extensions": {"http.response.debug": {}},
                "state": {},
            }
            request_sent = False
            response_started = False
            response_complete = anyio.Event()
            status_code = 500
            response_headers: list[tuple[str, str]] = []
            response_body = BytesIO()

            async def receive() -> MutableMapping[str, Any]:
                nonlocal request_sent
                if request_sent:
                    return {"type": "http.disconnect"}
                request_sent = True
                return {"type": "http.request", "body": request_body, "more_body": False}

            async def send(message: MutableMapping[str, Any]) -> None:
                nonlocal response_started, status_code, response_headers
                if message["type"] == "http.response.start":
                    response_started = True
                    status_code = message["status"]
                    response_headers = [(key.decode(), value.decode()) for key, value in message.get("headers", [])]
                elif message["type"] == "http.response.body":
                    if request.method != "HEAD":
                        response_body.write(message.get("body", b""))
                    if not message.get("more_body", False):
                        response_complete.set()

            try:
                await self._app(scope, receive, send)
            except Exception:
                if self._raise_server_exceptions:
                    raise
                if not response_started:
                    response_complete.set()

            if self._raise_server_exceptions and not response_started:
                raise AssertionError("TestClient did not receive any response.")
            await response_complete.wait()
            return status_code, response_headers, response_body.getvalue()

        status_code, headers, body = anyio.run(run_request)
        return httpx.Response(
            status_code=status_code,
            headers=headers,
            content=body,
            request=request,
        )


class PortalFreeTestClient(httpx.Client):
    __test__ = False

    def __init__(
        self,
        app: Any,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: str = "asyncio",
        backend_options: dict[str, Any] | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        headers: dict[str, str] | None = None,
        follow_redirects: bool = True,
        client: tuple[str, int] = ("testclient", 50000),
    ) -> None:
        if backend != "asyncio" or backend_options:
            raise NotImplementedError("pytest PortalFreeTestClient supports the default asyncio backend only")
        self.app = app
        self._lifespan_context: AbstractAsyncContextManager[Any] | None = None
        default_headers = {"user-agent": "testclient"}
        if headers:
            default_headers.update(headers)
        super().__init__(
            base_url=base_url,
            headers=default_headers,
            transport=_AnyIORunASGITransport(app, raise_server_exceptions, root_path, client),
            follow_redirects=follow_redirects,
            cookies=cookies,
        )

    def __enter__(self) -> "PortalFreeTestClient":
        anyio.run(self._startup)
        return super().__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        try:
            anyio.run(self._shutdown)
        finally:
            super().__exit__(exc_type, exc_value, traceback)

    async def _startup(self) -> None:
        if self._lifespan_context is not None:
            return
        self._lifespan_context = self.app.router.lifespan_context(self.app)
        await self._lifespan_context.__aenter__()

    async def _shutdown(self) -> None:
        if self._lifespan_context is None:
            return
        lifespan_context = self._lifespan_context
        self._lifespan_context = None
        await lifespan_context.__aexit__(None, None, None)


# Starlette's current TestClient path hangs in this Python/dependency set while
# waiting on AnyIO's blocking portal. Patch pytest imports to keep sync HTTP
# coverage without using the blocked portal path.
fastapi.testclient.TestClient = PortalFreeTestClient
starlette.testclient.TestClient = PortalFreeTestClient


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def sample_rows() -> list[dict]:
    return [
        {
            "played_at": "2026-06-01",
            "map_name": "Mirage",
            "result": "win",
            "rounds_for": 13,
            "rounds_against": 9,
            "kills": 22,
            "deaths": 15,
            "assists": 4,
            "adr": 91.2,
            "kast": 78,
            "rating": 1.21,
            "entry_kills": 3,
            "entry_deaths": 2,
            "utility_damage": 120,
            "flash_assists": 1,
        },
        {
            "played_at": "2026-06-02",
            "map_name": "Ancient",
            "result": "loss",
            "rounds_for": 7,
            "rounds_against": 13,
            "kills": 14,
            "deaths": 22,
            "assists": 3,
            "adr": 58,
            "kast": 61,
            "rating": 0.7,
            "entry_kills": 0,
            "entry_deaths": 5,
            "utility_damage": 18,
            "flash_assists": 0,
        },
    ]


def make_match(**kwargs) -> Match:
    fallback_id = f"id-{kwargs.get('played_at', 'x')}-{kwargs.get('map_name', 'map')}"
    defaults = {
        "source": "test",
        "external_match_id": kwargs.get("external_match_id", fallback_id),
    }
    defaults.update(kwargs)
    return Match(**defaults)
