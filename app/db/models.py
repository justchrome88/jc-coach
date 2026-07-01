from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
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
    early_deaths: Mapped[int | None] = mapped_column(Integer)
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


class CoachRecommendation(Base):
    __tablename__ = "coach_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(30), default="high", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    target_period_matches: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    baseline_period_matches: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    start_after_match_id: Mapped[int | None] = mapped_column(Integer)
    baseline_metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    target_metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    success_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    failure_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_match_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    coach_comment: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MatchRecommendationEvaluation(Base):
    __tablename__ = "match_recommendation_evaluations"
    __table_args__ = (
        UniqueConstraint("recommendation_id", "match_id", name="uq_match_recommendation_evaluation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("coach_recommendations.id"), nullable=False, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    positive_signals_json: Mapped[str] = mapped_column(Text, nullable=False)
    negative_signals_json: Mapped[str] = mapped_column(Text, nullable=False)
    coach_comment: Mapped[str] = mapped_column(Text, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SteamAccount(Base):
    __tablename__ = "steam_accounts"
    __table_args__ = (UniqueConstraint("steam_id", name="uq_steam_accounts_steam_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    steam_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    persona_name: Mapped[str | None] = mapped_column(String(120))
    profile_url: Mapped[str | None] = mapped_column(String(500))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    linked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime)
    sync_enabled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    match_auth_code: Mapped[str | None] = mapped_column(String(255))
    last_share_code: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", index=True)
    steam_account_id: Mapped[int | None] = mapped_column(ForeignKey("steam_accounts.id"), index=True)
    requested_payload_json: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
