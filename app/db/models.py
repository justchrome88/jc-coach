from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("source", "external_match_id", name="uq_matches_source_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    steam_account_id: Mapped[int | None] = mapped_column(ForeignKey("steam_accounts.id"), index=True)
    import_job_id: Mapped[int | None] = mapped_column(ForeignKey("import_jobs.id"), index=True)
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
    swing_score: Mapped[float | None] = mapped_column(Float)
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


class DemoParseArtifact(Base):
    __tablename__ = "demo_parse_artifacts"
    __table_args__ = (UniqueConstraint("match_id", name="uq_demo_parse_artifacts_match_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    import_job_id: Mapped[int | None] = mapped_column(ForeignKey("import_jobs.id"), index=True)
    parser_name: Mapped[str] = mapped_column(String(80), nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(80))
    payload_version: Mapped[str] = mapped_column(String(40), default="2026-07-02.1", nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_demo_file: Mapped[str | None] = mapped_column(String(500))
    demo_sha1: Mapped[str | None] = mapped_column(String(64), index=True)
    parsed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    event_counts_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    data_gaps_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "match_id",
            "player_key",
            "metric_domain",
            "semantic_version",
            "source",
            "source_event_set_id",
            name="uq_metric_snapshot_semantic_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    player_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(255), index=True)
    player_steamid: Mapped[str | None] = mapped_column(String(32), index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    metric_domain: Mapped[str] = mapped_column(String(80), default="legacy", nullable=False, index=True)
    semantic_version: Mapped[str] = mapped_column(String(40), default="1.0.0", nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(40), default="player_match", nullable=False, index=True)
    validation_status: Mapped[str] = mapped_column(String(40), default="legacy_unverified", nullable=False, index=True)
    implementation_version: Mapped[str | None] = mapped_column(String(120), index=True)
    input_event_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    source_parser_artifact_id: Mapped[int | None] = mapped_column(ForeignKey("demo_parse_artifacts.id"), index=True)
    source_event_set_id: Mapped[str | None] = mapped_column(String(255), index=True)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_baseline_json: Mapped[str] = mapped_column(Text, nullable=False)
    caveats_json: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    owner_steam_id: Mapped[str | None] = mapped_column(String(32), index=True)
    mode: Mapped[str] = mapped_column(String(50), default="personal", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="created", nullable=False, index=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    source: Mapped[str | None] = mapped_column(String(80), index=True)
    selected_metric_snapshot_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_scope_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CoachHypothesis(Base):
    __tablename__ = "coach_hypotheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    owner_steam_id: Mapped[str | None] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(40), default="candidate", nullable=False, index=True)
    source_insight_card_id: Mapped[str | None] = mapped_column(String(120), index=True)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    caveats_json: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_focus: Mapped[str] = mapped_column(Text, nullable=False)
    mission_readiness_json: Mapped[str] = mapped_column(Text, nullable=False)
    target_metric_candidates_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_card_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CoachMission(Base):
    __tablename__ = "coach_missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hypothesis_id: Mapped[int | None] = mapped_column(ForeignKey("coach_hypotheses.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    owner_steam_id: Mapped[str | None] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    focus: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MissionCriteria(Base):
    __tablename__ = "mission_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("coach_missions.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    owner_steam_id: Mapped[str | None] = mapped_column(String(32), index=True)
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(40), nullable=False)
    baseline_value: Mapped[float | None] = mapped_column(Float)
    target_value: Mapped[float | None] = mapped_column(Float)
    min_sample_matches: Mapped[int | None] = mapped_column(Integer)
    min_sample_rounds: Mapped[int | None] = mapped_column(Integer)
    confidence_required: Mapped[float | None] = mapped_column(Float)
    rule_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MissionProgressEvaluation(Base):
    __tablename__ = "mission_progress_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("coach_missions.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    owner_steam_id: Mapped[str | None] = mapped_column(String(32), index=True)
    evaluation_window_start: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    evaluation_window_end: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    caveats_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CoachEvidenceBaseline(Base):
    """Immutable owner-scoped evidence selection for one AI analysis cutoff."""

    __tablename__ = "coach_evidence_baselines"
    __table_args__ = (UniqueConstraint("baseline_hash", name="uq_coach_evidence_baseline_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    owner_steam_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    analysis_cutoff: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    baseline_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    evidence_version: Mapped[str] = mapped_column(String(40), nullable=False)
    match_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    lineage_json: Mapped[str] = mapped_column(Text, nullable=False)
    exclusions_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)


class AIDomainAnalysis(Base):
    """Append-only configured-model attempt and deterministic validation result."""

    __tablename__ = "ai_domain_analyses"
    __table_args__ = (UniqueConstraint("idempotency_key", "attempt_number", name="uq_ai_domain_analysis_attempt"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    owner_steam_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    domain_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    baseline_id: Mapped[int] = mapped_column(ForeignKey("coach_evidence_baselines.id"), nullable=False, index=True)
    baseline_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    routing_json: Mapped[str] = mapped_column(Text, nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(255), index=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    raw_response_hash: Mapped[str | None] = mapped_column(String(64))
    structured_output_json: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    validation_errors_json: Mapped[str] = mapped_column(Text, nullable=False)
    failure_reason_code: Mapped[str | None] = mapped_column(String(80), index=True)
    supersedes_analysis_id: Mapped[int | None] = mapped_column(ForeignKey("ai_domain_analyses.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)


class CoachMissionProposal(Base):
    __tablename__ = "coach_mission_proposals"
    __table_args__ = (
        Index(
            "uq_current_coach_proposal_owner_domain",
            "owner_user_id",
            "domain_key",
            unique=True,
            sqlite_where=text("is_current = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    owner_steam_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    domain_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("ai_domain_analyses.id"), nullable=False, unique=True)
    baseline_id: Mapped[int] = mapped_column(ForeignKey("coach_evidence_baselines.id"), nullable=False, index=True)
    proposal_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    provenance_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    superseded_by_id: Mapped[int | None] = mapped_column(ForeignKey("coach_mission_proposals.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)


class CoachDomainSlot(Base):
    __tablename__ = "coach_domain_slots"
    __table_args__ = (UniqueConstraint("owner_user_id", "domain_key", name="uq_coach_domain_slot_owner_domain"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    owner_steam_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    domain_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    baseline_id: Mapped[int | None] = mapped_column(ForeignKey("coach_evidence_baselines.id"), index=True)
    current_analysis_id: Mapped[int | None] = mapped_column(ForeignKey("ai_domain_analyses.id"), index=True)
    current_proposal_id: Mapped[int | None] = mapped_column(ForeignKey("coach_mission_proposals.id"), index=True)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DemoRound(Base):
    __tablename__ = "demo_rounds"
    __table_args__ = (UniqueConstraint("match_id", "round_number", name="uq_demo_round_match_round"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    start_tick: Mapped[int | None] = mapped_column(Integer)
    freeze_end_tick: Mapped[int | None] = mapped_column(Integer)
    end_tick: Mapped[int | None] = mapped_column(Integer)
    winner_side: Mapped[str | None] = mapped_column(String(10), index=True)
    end_reason: Mapped[str | None] = mapped_column(String(80))
    bomb_planted_tick: Mapped[int | None] = mapped_column(Integer)
    bomb_site: Mapped[str | None] = mapped_column(String(20))
    bomb_outcome: Mapped[str | None] = mapped_column(String(40))
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)


class DemoPlayerRound(Base):
    __tablename__ = "demo_player_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(255), index=True)
    player_steamid: Mapped[str | None] = mapped_column(String(32), index=True)
    team_side: Mapped[str | None] = mapped_column(String(10))
    kills: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deaths: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    damage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    utility_damage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    headshots: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flash_assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enemies_flashed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opening_kill: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opening_death: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    survived: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    kast: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)


class DemoWeaponStat(Base):
    __tablename__ = "demo_weapon_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    player_name: Mapped[str | None] = mapped_column(String(255), index=True)
    player_steamid: Mapped[str | None] = mapped_column(String(32), index=True)
    weapon: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    shots: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kills: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deaths: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    damage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    headshots: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Float)
    headshot_percent: Mapped[float | None] = mapped_column(Float)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)


class DemoDamageEvent(Base):
    __tablename__ = "demo_damage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tick: Mapped[int | None] = mapped_column(Integer, index=True)
    attacker_name: Mapped[str | None] = mapped_column(String(255), index=True)
    attacker_steamid: Mapped[str | None] = mapped_column(String(32), index=True)
    victim_name: Mapped[str | None] = mapped_column(String(255), index=True)
    victim_steamid: Mapped[str | None] = mapped_column(String(32), index=True)
    weapon: Mapped[str | None] = mapped_column(String(120), index=True)
    hitgroup: Mapped[str | None] = mapped_column(String(80))
    damage_health: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    damage_armor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    victim_health_after: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)


class DemoDuel(Base):
    __tablename__ = "demo_duels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tick: Mapped[int | None] = mapped_column(Integer, index=True)
    attacker_name: Mapped[str | None] = mapped_column(String(255), index=True)
    attacker_steamid: Mapped[str | None] = mapped_column(String(32), index=True)
    victim_name: Mapped[str | None] = mapped_column(String(255), index=True)
    victim_steamid: Mapped[str | None] = mapped_column(String(32), index=True)
    assister_name: Mapped[str | None] = mapped_column(String(255))
    assister_steamid: Mapped[str | None] = mapped_column(String(32))
    weapon: Mapped[str | None] = mapped_column(String(120), index=True)
    headshot: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opening_duel: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trade_kill: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    distance: Mapped[float | None] = mapped_column(Float)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)


class DemoGrenadeEvent(Base):
    __tablename__ = "demo_grenade_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tick: Mapped[int | None] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    grenade_type: Mapped[str | None] = mapped_column(String(120), index=True)
    player_name: Mapped[str | None] = mapped_column(String(255), index=True)
    player_steamid: Mapped[str | None] = mapped_column(String(32), index=True)
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    z: Mapped[float | None] = mapped_column(Float)
    flashed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    damage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)


class CoachReport(Base):
    __tablename__ = "coach_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    source_metric_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("metric_snapshots.id"), index=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime)
    period_end: Mapped[datetime | None] = mapped_column(DateTime)
    matches_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), default="rule_based", nullable=False, index=True)
    source_ref: Mapped[str | None] = mapped_column(String(500))
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
    __table_args__ = (UniqueConstraint("recommendation_id", "match_id", name="uq_match_recommendation_evaluation"),)

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
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
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
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="requested", index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    steam_account_id: Mapped[int | None] = mapped_column(ForeignKey("steam_accounts.id"), index=True)
    logical_target_key: Mapped[str | None] = mapped_column(String(500), index=True)
    requested_payload_json: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
