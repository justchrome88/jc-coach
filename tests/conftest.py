from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Match
from app.db.session import Base


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
