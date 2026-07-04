from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTION_DB_PATH = (BASE_DIR / "data" / "cs2_coach.db").resolve()


class Settings(BaseSettings):
    app_name: str = "CS2 Personal Coach"
    app_env: str = "local"
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'cs2_coach.db'}"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    demo_inbox_dir: Path = BASE_DIR / "data" / "incoming_demos"
    reports_dir: Path = BASE_DIR / "data" / "reports"
    ai_handoff_dir: Path = BASE_DIR / "data" / "ai_handoffs"
    ai_provider: str = "codex_cli_handoff"
    ai_codex_command: str = "codex exec"
    local_llm_base_url: str | None = None
    local_llm_model: str | None = None
    local_llm_timeout_seconds: int = 90
    public_base_url: str = "http://127.0.0.1:8000"
    steam_realm: str | None = None
    steam_return_path: str = "/auth/steam/callback"
    steam_web_api_key: str | None = None
    steam_sync_max_codes: int = 20
    steam_bot_username: str | None = None
    steam_bot_password: str | None = None
    steam_bot_shared_secret: str | None = None
    steam_bot_two_factor_code: str | None = None
    steam_bot_refresh_token: str | None = None
    steam_bot_timeout_seconds: int = 45
    session_secret_key: str = "change-me-before-public-release"
    auth_cookie_secure: bool = False
    api_token: str | None = None
    openai_api_key: str | None = None
    demo_player_identifier: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _assert_safe_test_settings(settings)
    _assert_strong_session_secret(settings)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.demo_inbox_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    settings.ai_handoff_dir.mkdir(parents=True, exist_ok=True)
    return settings


def is_test_environment(app_env: str) -> bool:
    return app_env.strip().lower() == "test"


def database_url_points_to_production(database_url: str) -> bool:
    db_path = _sqlite_database_path(database_url)
    return db_path == PRODUCTION_DB_PATH


def assert_test_database_not_production(database_url: str, context: str = "test execution") -> None:
    if database_url_points_to_production(database_url):
        raise RuntimeError(
            f"Unsafe {context}: test helpers cannot use the production database at {PRODUCTION_DB_PATH}."
        )


def _assert_strong_session_secret(settings: Settings) -> None:
    app_env = settings.app_env.strip().lower()
    if app_env in {"local", "test", "dev", "development"}:
        return
    secret = settings.session_secret_key.strip()
    weak_values = {"", "change-me-before-public-release", "changeme", "secret", "password"}
    if secret in weak_values or len(secret) < 32:
        raise RuntimeError(
            "Unsafe session configuration: set a strong SESSION_SECRET_KEY before running outside local/test."
        )


def _assert_safe_test_settings(settings: Settings) -> None:
    if not is_test_environment(settings.app_env):
        return
    assert_test_database_not_production(settings.database_url, context="test configuration")


def _sqlite_database_path(database_url: str) -> Path | None:
    if database_url == "sqlite:///:memory:":
        return None
    if not database_url.startswith("sqlite:///"):
        return None
    if database_url.startswith("sqlite:////"):
        raw_path = "/" + database_url.removeprefix("sqlite:////")
    else:
        raw_path = database_url.removeprefix("sqlite:///")
    raw_path = unquote(raw_path)
    if not raw_path:
        return None
    return Path(raw_path).resolve()
