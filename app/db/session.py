from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


settings = get_settings()
engine = create_engine(settings.database_url, future=True, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _upgrade_sqlite_schema()


def _upgrade_sqlite_schema() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "matches" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("matches")}
    with engine.begin() as connection:
        if "early_deaths" not in columns:
            connection.execute(text("ALTER TABLE matches ADD COLUMN early_deaths INTEGER"))
    recommendation_tables = inspector.get_table_names()
    if "coach_recommendations" not in recommendation_tables:
        return
    recommendation_columns = {column["name"] for column in inspector.get_columns("coach_recommendations")}
    with engine.begin() as connection:
        if "start_after_match_id" not in recommendation_columns:
            connection.execute(text("ALTER TABLE coach_recommendations ADD COLUMN start_after_match_id INTEGER"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
