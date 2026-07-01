from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "CS2 Personal Coach"
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
    openai_api_key: str | None = None
    demo_player_identifier: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.demo_inbox_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    settings.ai_handoff_dir.mkdir(parents=True, exist_ok=True)
    return settings
