from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "CS2 Personal Coach"
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'cs2_coach.db'}"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    reports_dir: Path = BASE_DIR / "data" / "reports"
    openai_api_key: str | None = None
    demo_player_identifier: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return settings
