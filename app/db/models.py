from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("source", "external_match_id", name="uq_matches_source_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(50), default="upload", nullable=False)
    external_match_id: Mapped[str | None] = mapped_column(String(255), index=True)
    demo_file: Mapped[str | None] = mapped_column(String(500))
    played_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    map_name: Mapped[str | None] = mapped_column(String(80), index=True)
    mode: Mapped[str | None] = mapped_column(String(80))
    result: Mapped[str | None] = mapped_column(String(20), index=True)
    rounds_for: Mapped[int | None] = mapped_column(Integer)
    rounds_against: Mapped[int | None] = mapped_column(Integer)
    kills: Mapped[int | None] = mapped_column(Integer)
    deaths: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    kd: Mapped[float | None] = mapped_column(Float)
    adr: Mapped[float | None] = mapped_column(Float)
    kast: Mapped[float | None] = mapped_column(Float)
    rating: Mapped[float | None] = mapped_column(Float)
    headshot_percent: Mapped[float | None] = mapped_column(Float)
    entry_kills: Mapped[int | None] = mapped_column(Integer)
    entry_deaths: Mapped[int | None] = mapped_column(Integer)
    flash_assists: Mapped[int | None] = mapped_column(Integer)
    utility_damage: Mapped[int | None] = mapped_column(Integer)
    enemies_flashed: Mapped[int | None] = mapped_column(Integer)
    clutches_won: Mapped[int | None] = mapped_column(Integer)
    clutches_lost: Mapped[int | None] = mapped_column(Integer)
    side_t_rounds_won: Mapped[int | None] = mapped_column(Integer)
    side_t_rounds_lost: Mapped[int | None] = mapped_column(Integer)
    side_ct_rounds_won: Mapped[int | None] = mapped_column(Integer)
    side_ct_rounds_lost: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CoachReport(Base):
    __tablename__ = "coach_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime)
    period_end: Mapped[datetime | None] = mapped_column(DateTime)
    matches_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    report_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    report_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
