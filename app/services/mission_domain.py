from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AnalysisRun,
    CoachHypothesis,
    CoachMission,
    Match,
    MetricSnapshot,
    MissionCriteria,
    MissionProgressEvaluation,
)
from app.services.coach_domain_model import (
    CANONICAL_COACH_DOMAINS,
    canonical_domain_for_family,
    canonicalize_domain_key,
    require_canonical_domain,
)

MISSION_PROGRESS_STATUSES = {
    "improving",
    "unchanged",
    "regressing",
    "insufficient_data",
    "not_following",
}
INSIGHT_CONFIDENCE_SCORES = {
    "low": 0.25,
    "medium": 0.6,
    "high": 0.9,
}
MISSION_STATUSES = {"draft", "active", "completed", "failed", "paused", "cancelled", "expired"}
ACTIVE_MISSION_STATUSES = {"active"}
TERMINAL_MISSION_STATUSES = {"completed", "failed", "cancelled", "expired"}
MISSION_TRANSITIONS = {
    "draft": {"active", "cancelled"},
    "active": {"paused", "completed", "failed", "cancelled", "expired"},
    "paused": {"active", "cancelled", "expired"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
    "expired": set(),
}
MISSION_DUPLICATE_POLICIES = {"reject", "replace", "allow"}
CRITERIA_ROLES = {"primary", "secondary", "guardrail"}
CRITERIA_DIRECTIONS = {
    "higher_is_better",
    "lower_is_better",
    "stay_above",
    "stay_below",
    "not_drop_more_than",
    "improve_or_same",
}
MISSION_ELIGIBLE_CONFIDENCE_LEVELS = {"medium", "high"}
MISSION_PAYLOAD_SCHEMA_VERSION = "coach-mission-payload-v1"
REQUIRED_MISSION_PAYLOAD_FIELDS = ("title", "goal", "rules", "duration", "success_metric", "failure_condition")
SURVIVAL_OPENING_MISSION_METRICS = {"opening_death_rate", "survival_rate"}
BAD_FIGHT_TRADE_MISSION_METRICS = {"untraded_death_rate"}
EFFECTIVE_UTILITY_METRIC = "effective_enemy_utility_damage"
UTILITY_VALUE_MISSION_METRICS = {
    EFFECTIVE_UTILITY_METRIC,
    "utility_damage_per_round",
    "enemy_he_damage",
    "enemy_fire_damage",
    "effective_enemy_flash_duration",
}
UTILITY_NEGATIVE_TREND_MATERIALITY = 0.10
MAX_UTILITY_TREND_SUPPORTED_MATCHES = 30
MIN_UTILITY_TREND_SUPPORTED_MATCHES = 10
MIN_UTILITY_TREND_SEGMENT_MATCHES = 5
ROLLING_MISSION_WINDOW_TYPES = {"last_30", "last_60", "custom_match_set"}
ROLLING_MISSION_METRICS = {
    "adr",
    "deaths",
    "kast",
    "kills_per_round",
    "survival_rate",
    "opening_death_rate",
    "opening_duel_win_rate",
    "untraded_death_rate",
    "traded_death_rate",
    EFFECTIVE_UTILITY_METRIC,
}
MIN_ROLLING_WINDOW_MATCHES = 3
MIN_ROLLING_WINDOW_ROUNDS = 8
CORE_COMBAT_SNAPSHOT_SOURCE = "coach_metric_performance"
UTILITY_SNAPSHOT_SOURCE = "coach_metric_utility"
UTILITY_SNAPSHOT_METRICS = {
    "enemies_effectively_flashed",
    "effective_enemy_flash_duration",
    "flash_assists",
    "flash_detonations",
    "enemy_he_damage",
    "he_detonations",
    "enemy_fire_damage",
    "fire_grenade_detonations",
    "smoke_detonations",
    "smokes_used",
    EFFECTIVE_UTILITY_METRIC,
    "utility_damage_per_round",
}


@dataclass(frozen=True)
class MissionPayload:
    title: str
    goal: str
    rules: tuple[str, ...]
    duration: dict[str, Any]
    success_metric: dict[str, Any]
    failure_condition: dict[str, Any]
    linked_insight: dict[str, Any]
    schema_version: str = MISSION_PAYLOAD_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "goal": self.goal,
            "rules": list(self.rules),
            "duration": dict(self.duration),
            "success_metric": dict(self.success_metric),
            "failure_condition": dict(self.failure_condition),
            "linked_insight": dict(self.linked_insight),
        }


@dataclass(frozen=True)
class MissionPayloadValidationIssue:
    code: str
    message: str
    path: str


@dataclass(frozen=True)
class UtilityTrendEvidence:
    evidence_available: bool
    deficiency_detected: bool
    mission_ready: bool
    supported_match_ids: tuple[int, ...]
    supported_snapshot_ids: tuple[int, ...]
    ignored_oldest_match_ids: tuple[int, ...]
    baseline_match_ids: tuple[int, ...]
    recent_match_ids: tuple[int, ...]
    baseline_snapshot_ids: tuple[int, ...]
    recent_snapshot_ids: tuple[int, ...]
    baseline_value: float | None
    recent_value: float | None
    absolute_change: float | None
    absolute_gap: float
    relative_change: float | None
    relative_drop: float
    severity: float
    confidence: str
    source: str
    caveats: tuple[str, ...]
    materiality_threshold: float
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_available": self.evidence_available,
            "deficiency_detected": self.deficiency_detected,
            "mission_ready": self.mission_ready,
            "supported_match_ids": list(self.supported_match_ids),
            "supported_snapshot_ids": list(self.supported_snapshot_ids),
            "supported_match_count": len(self.supported_match_ids),
            "ignored_oldest_match_ids": list(self.ignored_oldest_match_ids),
            "baseline_match_ids": list(self.baseline_match_ids),
            "recent_match_ids": list(self.recent_match_ids),
            "baseline_snapshot_ids": list(self.baseline_snapshot_ids),
            "recent_snapshot_ids": list(self.recent_snapshot_ids),
            "baseline_value": self.baseline_value,
            "recent_value": self.recent_value,
            "absolute_change": self.absolute_change,
            "absolute_gap": self.absolute_gap,
            "relative_change": self.relative_change,
            "relative_drop": self.relative_drop,
            "severity": self.severity,
            "confidence": self.confidence,
            "source": self.source,
            "caveats": list(self.caveats),
            "materiality_threshold": self.materiality_threshold,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class RollingMissionWindow:
    user_id: int
    owner_steam_id: str
    window_type: str
    source: str
    match_ids: tuple[int, ...]
    metric_snapshot_ids: tuple[int, ...]
    metrics: dict[str, float]
    metric_samples: dict[str, dict[str, Any]]
    sample_matches: int
    sample_rounds: int
    confidence: str
    confidence_score: float
    caveats: tuple[str, ...]
    utility_trend: UtilityTrendEvidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "owner_steam_id": self.owner_steam_id,
            "window_type": self.window_type,
            "source": self.source,
            "match_ids": list(self.match_ids),
            "metric_snapshot_ids": list(self.metric_snapshot_ids),
            "metrics": dict(self.metrics),
            "metric_samples": {key: dict(value) for key, value in self.metric_samples.items()},
            "sample_matches": self.sample_matches,
            "sample_rounds": self.sample_rounds,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "caveats": list(self.caveats),
            "utility_trend": self.utility_trend.to_dict(),
        }


@dataclass(frozen=True)
class RollingMissionCandidate:
    rank: int
    candidate_id: str
    family: str
    primary_metric: str
    severity: float
    confidence_score: float
    sample_size: int
    suppressed_by_active_mission: bool
    suppression_reason: str | None
    explanation: str
    insight_card: dict[str, Any]
    mission_payload: dict[str, Any]
    window_evidence: dict[str, Any]
    suppression_key: dict[str, Any]
    suppression_reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "candidate_id": self.candidate_id,
            "family": self.family,
            "primary_metric": self.primary_metric,
            "severity": self.severity,
            "confidence_score": self.confidence_score,
            "sample_size": self.sample_size,
            "suppressed_by_active_mission": self.suppressed_by_active_mission,
            "suppression_reason": self.suppression_reason,
            "explanation": self.explanation,
            "insight_card": dict(self.insight_card),
            "mission_payload": dict(self.mission_payload),
            "window_evidence": dict(self.window_evidence),
            "suppression_key": dict(self.suppression_key),
            "suppression_reason_codes": list(self.suppression_reason_codes),
        }


@dataclass(frozen=True)
class MissionSuppressionDecision:
    suppressed: bool
    reason: str | None
    reason_codes: tuple[str, ...]
    active_mission_id: int | None
    active_mission_title: str | None
    active_mission_status: str | None
    active_mission_progress_status: str | None
    key: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "suppressed": self.suppressed,
            "reason": self.reason,
            "reason_codes": list(self.reason_codes),
            "active_mission_id": self.active_mission_id,
            "active_mission_title": self.active_mission_title,
            "active_mission_status": self.active_mission_status,
            "active_mission_progress_status": self.active_mission_progress_status,
            "key": dict(self.key),
        }


def create_analysis_run(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str | None = None,
    mode: str = "personal",
    status: str = "created",
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    source: str | None = None,
    selected_metric_snapshot_ids: Sequence[int] | None = None,
    analysis_scope: Mapping[str, Any] | None = None,
    source_payload: Mapping[str, Any] | None = None,
) -> AnalysisRun:
    run = AnalysisRun(
        user_id=user_id,
        owner_steam_id=owner_steam_id,
        mode=mode,
        status=status,
        window_start=window_start,
        window_end=window_end,
        source=source,
        selected_metric_snapshot_ids_json=_json_list(selected_metric_snapshot_ids or []),
        analysis_scope_json=_json_object(analysis_scope or {}),
        source_payload_json=_json_object(source_payload or {}),
    )
    db.add(run)
    db.flush()
    return run


def get_analysis_run(db: Session, *, user_id: int, analysis_run_id: int) -> AnalysisRun | None:
    return db.scalar(
        select(AnalysisRun).where(AnalysisRun.id == analysis_run_id).where(AnalysisRun.user_id == user_id)
    )


def list_analysis_runs(db: Session, *, user_id: int) -> list[AnalysisRun]:
    return list(
        db.scalars(
            select(AnalysisRun)
            .where(AnalysisRun.user_id == user_id)
            .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
        ).all()
    )


def create_coach_hypothesis(
    db: Session,
    *,
    user_id: int,
    analysis_run_id: int,
    insight_card: Mapping[str, Any],
    status: str = "candidate",
) -> CoachHypothesis:
    analysis_run = _require_owned_analysis_run(db, user_id=user_id, analysis_run_id=analysis_run_id)
    hypothesis = CoachHypothesis(
        analysis_run_id=analysis_run.id,
        user_id=user_id,
        owner_steam_id=analysis_run.owner_steam_id,
        status=status,
        source_insight_card_id=_optional_str(insight_card.get("id") or insight_card.get("card_id")),
        problem=str(insight_card.get("problem") or ""),
        evidence_json=_json_any(insight_card.get("evidence") or []),
        confidence=_optional_float(insight_card.get("confidence")),
        caveats_json=_json_any(insight_card.get("caveats") or []),
        recommended_focus=str(insight_card.get("recommended_focus") or ""),
        mission_readiness_json=_json_any(_mission_readiness(insight_card)),
        target_metric_candidates_json=_json_any(_target_metric_candidates(insight_card)),
        source_card_json=_json_any(dict(insight_card)),
    )
    db.add(hypothesis)
    db.flush()
    return hypothesis


def get_coach_hypothesis(db: Session, *, user_id: int, hypothesis_id: int) -> CoachHypothesis | None:
    return db.scalar(
        select(CoachHypothesis).where(CoachHypothesis.id == hypothesis_id).where(CoachHypothesis.user_id == user_id)
    )


def list_coach_hypotheses(db: Session, *, user_id: int, analysis_run_id: int | None = None) -> list[CoachHypothesis]:
    stmt = (
        select(CoachHypothesis)
        .where(CoachHypothesis.user_id == user_id)
        .order_by(CoachHypothesis.created_at.desc(), CoachHypothesis.id.desc())
    )
    if analysis_run_id is not None:
        stmt = stmt.where(CoachHypothesis.analysis_run_id == analysis_run_id)
    return list(db.scalars(stmt).all())


def activate_coach_mission(
    db: Session,
    *,
    user_id: int,
    hypothesis_id: int,
    title: str,
    focus: str | None = None,
    status: str = "active",
    source_payload: Mapping[str, Any] | None = None,
    duplicate_policy: str = "reject",
) -> CoachMission:
    if status not in MISSION_STATUSES:
        raise ValueError(f"Unsupported mission status: {status}")
    if duplicate_policy not in MISSION_DUPLICATE_POLICIES:
        raise ValueError(f"Unsupported mission duplicate policy: {duplicate_policy}")
    hypothesis = _require_owned_hypothesis(db, user_id=user_id, hypothesis_id=hypothesis_id)
    criteria_specs = _criteria_specs_from_hypothesis(hypothesis)
    if status == "active":
        _validate_hypothesis_can_activate(hypothesis, criteria_specs)
    mission_payload = mission_payload_from_hypothesis(hypothesis, title=title)
    if status == "active" and mission_payload is None:
        raise ValueError("Coach hypothesis cannot become an active mission: missing_mission_payload")
    domain_key = _mission_domain_key_from_parts(
        hypothesis=hypothesis,
        criteria_specs=criteria_specs,
        mission_payload=mission_payload,
    )
    if status == "active":
        _handle_duplicate_active_mission(
            db,
            user_id=user_id,
            owner_steam_id=hypothesis.owner_steam_id,
            domain_key=domain_key,
            duplicate_policy=duplicate_policy,
            replacement_reason="activate_duplicate_domain",
        )
    mission = CoachMission(
        hypothesis_id=hypothesis.id,
        user_id=user_id,
        owner_steam_id=hypothesis.owner_steam_id,
        status=status,
        title=title,
        focus=focus if focus is not None else hypothesis.recommended_focus,
        source_payload_json=_json_object(
            _mission_source_payload(
                hypothesis,
                source_payload,
                mission_payload,
                criteria_specs=criteria_specs,
                domain_key=domain_key,
            )
        ),
    )
    db.add(mission)
    db.flush()
    for criteria_spec in criteria_specs:
        _add_mission_criteria_from_spec(db, user_id=user_id, mission=mission, criteria_spec=criteria_spec)
    if status == "active":
        hypothesis.status = "mission_active"
    elif status == "draft":
        hypothesis.status = "mission_draft"
    db.flush()
    return mission


def create_draft_coach_mission(
    db: Session,
    *,
    user_id: int,
    hypothesis_id: int,
    title: str,
    focus: str | None = None,
    source_payload: Mapping[str, Any] | None = None,
) -> CoachMission:
    return activate_coach_mission(
        db,
        user_id=user_id,
        hypothesis_id=hypothesis_id,
        title=title,
        focus=focus,
        status="draft",
        source_payload=source_payload,
    )


def activate_draft_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    duplicate_policy: str = "reject",
) -> CoachMission:
    if duplicate_policy not in MISSION_DUPLICATE_POLICIES:
        raise ValueError(f"Unsupported mission duplicate policy: {duplicate_policy}")
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    if mission.status == "active":
        return mission
    if mission.status not in {"draft", "paused"}:
        raise ValueError(f"Cannot activate mission from status: {mission.status}")
    hypothesis = _require_mission_hypothesis(db, mission)
    criteria_specs = _criteria_specs_from_hypothesis(hypothesis)
    _validate_hypothesis_can_activate(hypothesis, criteria_specs)
    mission_payload = mission_payload_from_hypothesis(hypothesis, title=mission.title)
    if mission_payload is None:
        raise ValueError("Coach hypothesis cannot become an active mission: missing_mission_payload")
    domain_key = _mission_domain_key_from_parts(
        hypothesis=hypothesis,
        criteria_specs=criteria_specs,
        mission_payload=mission_payload,
    )
    _handle_duplicate_active_mission(
        db,
        user_id=user_id,
        owner_steam_id=mission.owner_steam_id,
        domain_key=domain_key,
        duplicate_policy=duplicate_policy,
        replacement_reason="activate_draft_duplicate_domain",
        exclude_mission_id=mission.id,
    )
    if not list_mission_criteria(db, user_id=user_id, mission_id=mission.id):
        for criteria_spec in criteria_specs:
            _add_mission_criteria_from_spec(db, user_id=user_id, mission=mission, criteria_spec=criteria_spec)
    mission.status = "active"
    mission.ended_at = None
    source_payload = _json_load_mapping(mission.source_payload_json)
    source_payload.update(
        _mission_source_payload(
            hypothesis,
            source_payload,
            mission_payload,
            criteria_specs=criteria_specs,
            domain_key=domain_key,
        )
    )
    mission.source_payload_json = _json_object(source_payload)
    hypothesis.status = "mission_active"
    db.flush()
    return mission


def get_coach_mission(db: Session, *, user_id: int, mission_id: int) -> CoachMission | None:
    return db.scalar(select(CoachMission).where(CoachMission.id == mission_id).where(CoachMission.user_id == user_id))


def list_coach_missions(
    db: Session,
    *,
    user_id: int,
    status: str | None = None,
    owner_steam_id: str | None = None,
    domain_key: str | None = None,
) -> list[CoachMission]:
    stmt = (
        select(CoachMission)
        .where(CoachMission.user_id == user_id)
        .order_by(CoachMission.activated_at.desc(), CoachMission.id.desc())
    )
    if status is not None:
        stmt = stmt.where(CoachMission.status == status)
    if owner_steam_id is not None:
        stmt = stmt.where(CoachMission.owner_steam_id == owner_steam_id)
    missions = list(db.scalars(stmt).all())
    if domain_key is not None:
        missions = [mission for mission in missions if mission_domain_key(mission) == domain_key]
    return missions


def list_active_coach_missions(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str | None = None,
    domain_key: str | None = None,
) -> list[CoachMission]:
    return list_coach_missions(
        db,
        user_id=user_id,
        status="active",
        owner_steam_id=owner_steam_id,
        domain_key=domain_key,
    )


def reconcile_noncanonical_active_missions(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str,
    apply: bool,
) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    for mission in list_active_coach_missions(db, user_id=user_id, owner_steam_id=owner_steam_id):
        source_payload = _json_load_mapping(mission.source_payload_json)
        legacy_domain_key = _optional_str(
            source_payload.get("mission_domain_key") or source_payload.get("domain_key")
        )
        canonical_domain_key = canonicalize_domain_key(legacy_domain_key)
        if canonical_domain_key is not None:
            decisions.append(
                {
                    "mission_id": mission.id,
                    "action": "preserve",
                    "legacy_domain_key": legacy_domain_key,
                    "canonical_domain_key": canonical_domain_key,
                }
            )
            continue
        decision = {
            "mission_id": mission.id,
            "action": "cancel_noncanonical" if apply else "would_cancel_noncanonical",
            "legacy_domain_key": legacy_domain_key,
            "canonical_domain_key": None,
            "reason": "noncanonical_domain_reconciliation",
        }
        decisions.append(decision)
        if not apply:
            continue
        source_payload["canonical_domain_reconciliation"] = {
            "schema_version": "canonical-domain-reconciliation-v1",
            "task": "H01B-R01",
            "decision": "supersede",
            "reason": "noncanonical_domain_reconciliation",
            "legacy_domain_key": legacy_domain_key,
            "canonical_domain_key": None,
            "historical_payload_preserved": True,
        }
        mission.source_payload_json = _json_object(source_payload)
        cancel_coach_mission(
            db,
            user_id=user_id,
            mission_id=mission.id,
            reason="noncanonical_domain_reconciliation",
        )
    db.flush()
    return {
        "schema_version": "canonical-domain-reconciliation-v1",
        "apply": apply,
        "owner_user_id": user_id,
        "owner_steam_id": owner_steam_id,
        "decisions": decisions,
        "active_mission_ids_after": [
            mission.id
            for mission in list_active_coach_missions(
                db,
                user_id=user_id,
                owner_steam_id=owner_steam_id,
            )
        ],
    }


def update_coach_mission_status(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    status: str,
    ended_at: datetime | None = None,
    reason: str = "status_update",
) -> CoachMission:
    if status not in MISSION_STATUSES:
        raise ValueError(f"Unsupported mission status: {status}")
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    _validate_mission_transition(mission.status, status)
    previous_status = mission.status
    if status == "active" and previous_status != "active":
        _handle_duplicate_active_mission(
            db,
            user_id=user_id,
            owner_steam_id=mission.owner_steam_id,
            domain_key=mission_domain_key(mission),
            duplicate_policy="reject",
            replacement_reason="status_update_duplicate_domain",
            exclude_mission_id=mission.id,
        )
    mission.status = status
    if status == "active":
        mission.ended_at = None
    elif status in TERMINAL_MISSION_STATUSES:
        mission.ended_at = ended_at or datetime.now(UTC)
    else:
        mission.ended_at = ended_at
    _record_lifecycle_transition(
        mission,
        previous_status=previous_status,
        next_status=status,
        reason=reason,
        occurred_at=mission.ended_at if status in TERMINAL_MISSION_STATUSES else None,
    )
    db.flush()
    return mission


def pause_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
) -> CoachMission:
    return update_coach_mission_status(db, user_id=user_id, mission_id=mission_id, status="paused")


def resume_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    duplicate_policy: str = "reject",
) -> CoachMission:
    return activate_draft_coach_mission(
        db,
        user_id=user_id,
        mission_id=mission_id,
        duplicate_policy=duplicate_policy,
    )


def cancel_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    ended_at: datetime | None = None,
    reason: str = "status_update",
) -> CoachMission:
    return update_coach_mission_status(
        db,
        user_id=user_id,
        mission_id=mission_id,
        status="cancelled",
        ended_at=ended_at or datetime.now(UTC),
        reason=reason,
    )


def complete_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    ended_at: datetime | None = None,
) -> CoachMission:
    return update_coach_mission_status(
        db,
        user_id=user_id,
        mission_id=mission_id,
        status="completed",
        ended_at=ended_at or datetime.now(UTC),
    )


def fail_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    ended_at: datetime | None = None,
) -> CoachMission:
    return update_coach_mission_status(
        db,
        user_id=user_id,
        mission_id=mission_id,
        status="failed",
        ended_at=ended_at or datetime.now(UTC),
    )


def expire_coach_mission(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    observed_matches: int | None = None,
    force: bool = False,
    ended_at: datetime | None = None,
) -> CoachMission:
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    if not force and not _mission_duration_exceeded(mission, observed_matches=observed_matches):
        raise ValueError("Cannot expire mission before configured duration/window is exceeded.")
    return update_coach_mission_status(
        db,
        user_id=user_id,
        mission_id=mission.id,
        status="expired",
        ended_at=ended_at or datetime.now(UTC),
    )


def add_mission_criteria(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    metric_name: str,
    role: str,
    direction: str,
    baseline_value: float | None = None,
    target_value: float | None = None,
    min_sample_matches: int | None = None,
    min_sample_rounds: int | None = None,
    confidence_required: float | None = None,
    rule: Mapping[str, Any] | None = None,
) -> MissionCriteria:
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    if role not in CRITERIA_ROLES:
        raise ValueError(f"Unsupported mission criteria role: {role}")
    if direction not in CRITERIA_DIRECTIONS:
        raise ValueError(f"Unsupported mission criteria direction: {direction}")
    criteria = MissionCriteria(
        mission_id=mission.id,
        user_id=user_id,
        owner_steam_id=mission.owner_steam_id,
        metric_name=metric_name,
        role=role,
        direction=direction,
        baseline_value=baseline_value,
        target_value=target_value,
        min_sample_matches=min_sample_matches,
        min_sample_rounds=min_sample_rounds,
        confidence_required=confidence_required,
        rule_json=_json_object(rule or {}),
    )
    db.add(criteria)
    db.flush()
    return criteria


def list_mission_criteria(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    include_superseded: bool = False,
) -> list[MissionCriteria]:
    _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    rows = list(
        db.scalars(
            select(MissionCriteria)
            .where(MissionCriteria.mission_id == mission_id)
            .where(MissionCriteria.user_id == user_id)
            .order_by(MissionCriteria.id.asc())
        ).all()
    )
    if include_superseded:
        return rows
    return [
        criteria
        for criteria in rows
        if _mapping(_json_load_mapping(criteria.rule_json).get("lifecycle")).get("state") != "superseded"
    ]


def record_mission_progress_evaluation(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    status: str,
    evaluation_window_start: datetime | None = None,
    evaluation_window_end: datetime | None = None,
    result: Mapping[str, Any] | None = None,
    confidence: float | None = None,
    caveats: Sequence[Any] | None = None,
) -> MissionProgressEvaluation:
    if status not in MISSION_PROGRESS_STATUSES:
        raise ValueError(f"Unsupported mission progress status: {status}")
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    evaluation = MissionProgressEvaluation(
        mission_id=mission.id,
        user_id=user_id,
        owner_steam_id=mission.owner_steam_id,
        evaluation_window_start=evaluation_window_start,
        evaluation_window_end=evaluation_window_end,
        status=status,
        result_json=_json_object(result or {}),
        confidence=confidence,
        caveats_json=_json_list(caveats or []),
    )
    db.add(evaluation)
    db.flush()
    return evaluation


def evaluate_mission_progress(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
    baseline_metric_snapshots: Sequence[Any] | None = None,
    evaluation_metric_snapshots: Sequence[Any],
    evaluation_window_start: datetime | None = None,
    evaluation_window_end: datetime | None = None,
    evaluation_window: Mapping[str, Any] | None = None,
) -> MissionProgressEvaluation:
    mission = _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    if mission.status != "active":
        raise ValueError(f"Cannot evaluate mission progress from status: {mission.status}")
    criteria_rows = list_mission_criteria(db, user_id=user_id, mission_id=mission.id)
    criteria_metric_names = {criteria.metric_name for criteria in criteria_rows}
    baseline_window = (
        _metric_snapshot_window(mission, baseline_metric_snapshots, metric_names=criteria_metric_names)
        if baseline_metric_snapshots is not None
        else None
    )
    snapshot_window = _metric_snapshot_window(
        mission,
        evaluation_metric_snapshots,
        metric_names=criteria_metric_names,
    )
    components = [
        _evaluate_criteria(criteria, snapshot_window, baseline_window=baseline_window)
        for criteria in criteria_rows
    ]
    status = _composite_progress_status(components)
    caveats = _evaluation_caveats(snapshot_window, components)
    snapshot_comparison = _snapshot_comparison(
        mission=mission,
        baseline_window=baseline_window,
        evaluation_window=snapshot_window,
        components=components,
    )
    window_payload = dict(evaluation_window or {})
    window_payload.update({
        "start": evaluation_window_start.isoformat() if evaluation_window_start else None,
        "end": evaluation_window_end.isoformat() if evaluation_window_end else None,
        "snapshot_ids": snapshot_window["snapshot_ids"],
        "snapshot_count": snapshot_window["snapshot_count"],
        "match_ids": snapshot_window["match_ids"],
        "sample_matches": snapshot_window["sample_matches"],
        "sample_rounds": snapshot_window["sample_rounds"],
        "metric_samples": snapshot_window["metric_samples"],
    })
    result = {
        "mission_id": mission.id,
        "owner_steam_id": mission.owner_steam_id,
        "status": status,
        "evaluation_window_json": window_payload,
        "components": components,
        "component_metrics": {
            component["metric_name"]: component
            for component in components
        },
        "snapshot_comparison": snapshot_comparison,
        "source_metric_snapshot_ids": snapshot_window["snapshot_ids"],
        "target_met": _target_met(components),
        "progress_explanation": _progress_explanation(status, snapshot_comparison, caveats),
    }
    return record_mission_progress_evaluation(
        db,
        user_id=user_id,
        mission_id=mission.id,
        status=status,
        evaluation_window_start=evaluation_window_start,
        evaluation_window_end=evaluation_window_end,
        result=result,
        confidence=_evaluation_confidence(snapshot_window, components),
        caveats=caveats,
    )


def list_mission_progress_evaluations(
    db: Session,
    *,
    user_id: int,
    mission_id: int,
) -> list[MissionProgressEvaluation]:
    _require_owned_mission(db, user_id=user_id, mission_id=mission_id)
    return list(
        db.scalars(
            select(MissionProgressEvaluation)
            .where(MissionProgressEvaluation.mission_id == mission_id)
            .where(MissionProgressEvaluation.user_id == user_id)
            .order_by(MissionProgressEvaluation.created_at.desc(), MissionProgressEvaluation.id.desc())
        ).all()
    )


def build_rolling_mission_window(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str,
    window_type: str = "last_30",
    match_ids: Sequence[int] | None = None,
) -> RollingMissionWindow:
    if window_type not in ROLLING_MISSION_WINDOW_TYPES:
        raise ValueError(f"Unsupported rolling mission window_type: {window_type}")
    if window_type == "custom_match_set" and not match_ids:
        raise ValueError("custom_match_set requires match_ids")
    match_limit = {"last_30": 30, "last_60": 60}.get(window_type)
    snapshots = _select_owner_metric_snapshots_for_window(
        db,
        user_id=user_id,
        owner_steam_id=owner_steam_id,
        window_type=window_type,
        match_ids=match_ids,
        match_limit=match_limit,
    )
    utility_snapshots = (
        snapshots
        if window_type == "custom_match_set"
        else _select_owner_metric_snapshots_for_window(
            db,
            user_id=user_id,
            owner_steam_id=owner_steam_id,
            window_type=window_type,
            match_ids=match_ids,
            match_limit=None,
        )
    )
    return _rolling_window_from_snapshots(
        user_id=user_id,
        owner_steam_id=owner_steam_id,
        window_type=window_type,
        snapshots=snapshots,
        utility_snapshots=utility_snapshots,
    )


def generate_rolling_mission_candidates(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str,
    window_type: str = "last_30",
    match_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    window = build_rolling_mission_window(
        db,
        user_id=user_id,
        owner_steam_id=owner_steam_id,
        window_type=window_type,
        match_ids=match_ids,
    )
    active_context = active_mission_context_for_owner(db, user_id=user_id, owner_steam_id=owner_steam_id)
    outcome_context = _match_outcome_context(db, user_id=user_id, match_ids=window.match_ids)
    candidates = _rolling_candidates_from_window(
        window,
        outcome_context=outcome_context,
        active_mission_summaries=active_context["active_missions"],
    )
    return {
        "window": window.to_dict(),
        "diagnostics": {
            EFFECTIVE_UTILITY_METRIC: {
                **window.utility_trend.to_dict(),
                "classification": "context-only",
                "mission_eligible": False,
                "reason_codes": sorted(
                    set(window.utility_trend.reason_codes) | {"noncanonical_utility_value_family"}
                ),
            },
            "impact_leak": _impact_leak_diagnostics(window, outcome_context),
        },
        "active_mission_context": active_context,
        "candidates": [candidate.to_dict() for candidate in candidates],
    }


def persist_rolling_mission_candidates(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str,
    window_type: str = "last_30",
    match_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    result = generate_rolling_mission_candidates(
        db,
        user_id=user_id,
        owner_steam_id=owner_steam_id,
        window_type=window_type,
        match_ids=match_ids,
    )
    window = _mapping(result.get("window"))
    utility_trend = _mapping(window.get("utility_trend"))
    selected_snapshot_ids = _ordered_ints(
        [
            *_int_list(window.get("metric_snapshot_ids")),
            *_int_list(utility_trend.get("baseline_snapshot_ids")),
            *_int_list(utility_trend.get("recent_snapshot_ids")),
        ]
    )
    analysis_scope = {
        "mode": "personal",
        "owner_user_id": user_id,
        "owner_steam_id": owner_steam_id,
        "window_type": window_type,
        "match_ids": list(match_ids or []),
        "source": "metric_snapshots",
    }
    analysis_run = _equivalent_rolling_analysis_run(
        db,
        user_id=user_id,
        owner_steam_id=owner_steam_id,
        selected_snapshot_ids=selected_snapshot_ids,
        analysis_scope=analysis_scope,
    )
    reused_analysis_run = analysis_run is not None
    if analysis_run is None:
        analysis_run = create_analysis_run(
            db,
            user_id=user_id,
            owner_steam_id=owner_steam_id,
            mode="personal",
            status="candidate_generated",
            source="rolling_mission_window",
            selected_metric_snapshot_ids=selected_snapshot_ids,
            analysis_scope=analysis_scope,
            source_payload={"rolling_window": window},
        )
    existing_card_ids = {
        hypothesis.source_insight_card_id
        for hypothesis in list_coach_hypotheses(db, user_id=user_id, analysis_run_id=analysis_run.id)
        if hypothesis.source_insight_card_id
    }
    hypotheses: list[CoachHypothesis] = []
    for candidate in result["candidates"]:
        candidate_payload = _mapping(candidate)
        if candidate_payload.get("suppressed_by_active_mission") is True:
            continue
        insight_card = _mapping(candidate_payload.get("insight_card"))
        card_id = _optional_str(insight_card.get("id") or insight_card.get("card_id"))
        if card_id and card_id in existing_card_ids:
            continue
        hypothesis = create_coach_hypothesis(
            db,
            user_id=user_id,
            analysis_run_id=analysis_run.id,
            insight_card=insight_card,
        )
        hypotheses.append(hypothesis)
        if card_id:
            existing_card_ids.add(card_id)
    db.flush()
    all_hypotheses = list_coach_hypotheses(db, user_id=user_id, analysis_run_id=analysis_run.id)
    return {
        **result,
        "analysis_run_id": analysis_run.id,
        "coach_hypothesis_ids": [hypothesis.id for hypothesis in all_hypotheses],
        "idempotency": {
            "reused_analysis_run": reused_analysis_run,
            "created_hypothesis_ids": [hypothesis.id for hypothesis in hypotheses],
        },
    }


def _equivalent_rolling_analysis_run(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str,
    selected_snapshot_ids: Sequence[int],
    analysis_scope: Mapping[str, Any],
) -> AnalysisRun | None:
    candidates = list(
        db.scalars(
            select(AnalysisRun)
            .where(AnalysisRun.user_id == user_id)
            .where(AnalysisRun.owner_steam_id == owner_steam_id)
            .where(AnalysisRun.source == "rolling_mission_window")
            .order_by(AnalysisRun.id.desc())
        ).all()
    )
    for run in candidates:
        if _ordered_ints(_json_load_sequence(run.selected_metric_snapshot_ids_json)) != list(selected_snapshot_ids):
            continue
        persisted_scope = _json_load_mapping(run.analysis_scope_json)
        if persisted_scope.get("window_type") != analysis_scope.get("window_type"):
            continue
        if _ordered_ints(persisted_scope.get("match_ids") or []) != _ordered_ints(
            analysis_scope.get("match_ids") or []
        ):
            continue
        return run
    return None


def active_mission_context_for_owner(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str,
) -> dict[str, Any]:
    missions = list_active_coach_missions(db, user_id=user_id, owner_steam_id=owner_steam_id)
    summaries = []
    for mission in missions:
        evaluations = list_mission_progress_evaluations(db, user_id=user_id, mission_id=mission.id)
        summaries.append(
            serialize_active_mission_summary(
                mission,
                latest_evaluation=evaluations[0] if evaluations else None,
            )
        )
    return {
        "scope": "owner_active_missions",
        "user_id": user_id,
        "owner_steam_id": owner_steam_id,
        "active_mission_count": len(summaries),
        "active_missions": summaries,
        "suppression_keys": [summary["suppression_key"] for summary in summaries],
    }


def mission_suppression_key_from_payload(
    *,
    owner_user_id: int,
    owner_steam_id: str | None,
    mission_payload: Mapping[str, Any] | None,
    domain_key: str | None = None,
    problem_key: str | None = None,
) -> dict[str, Any]:
    payload = _mapping(mission_payload)
    success_metric = _mapping(payload.get("success_metric"))
    target_metric = _optional_str(success_metric.get("metric_name"))
    resolved_domain_key = domain_key or (_domain_key_for_metric(target_metric) if target_metric else None)
    return {
        "owner_user_id": owner_user_id,
        "owner_steam_id": owner_steam_id,
        "domain_key": resolved_domain_key,
        "problem_key": problem_key or resolved_domain_key,
        "target_metric": target_metric,
        "mission_payload_type": _mission_payload_type(payload, domain_key=resolved_domain_key),
    }


def mission_suppression_decision_for_payload(
    *,
    candidate_key: Mapping[str, Any],
    active_mission_summaries: Sequence[Mapping[str, Any]],
) -> MissionSuppressionDecision:
    key = dict(candidate_key)
    candidate_owner = key.get("owner_user_id")
    candidate_steam = key.get("owner_steam_id")
    candidate_domain = key.get("domain_key")
    for summary in active_mission_summaries:
        active_key = _mapping(summary.get("suppression_key"))
        if active_key.get("owner_user_id") != candidate_owner:
            continue
        if active_key.get("owner_steam_id") != candidate_steam:
            continue
        if active_key.get("domain_key") != candidate_domain:
            continue
        if summary.get("mission_status") == "active":
            return MissionSuppressionDecision(
                suppressed=True,
                reason="active_mission_same_domain",
                reason_codes=("active_mission_same_domain",),
                active_mission_id=_optional_int(summary.get("mission_id")),
                active_mission_title=_optional_str(summary.get("title")),
                active_mission_status=_optional_str(summary.get("mission_status")),
                active_mission_progress_status=_optional_str(summary.get("progress_status")),
                key=key,
            )
    return MissionSuppressionDecision(
        suppressed=False,
        reason=None,
        reason_codes=(),
        active_mission_id=None,
        active_mission_title=None,
        active_mission_status=None,
        active_mission_progress_status=None,
        key=key,
    )


def serialize_mission_progress_evaluation(evaluation: MissionProgressEvaluation) -> dict[str, Any]:
    result = _json_load_mapping(evaluation.result_json)
    components = [
        dict(component)
        for component in result.get("components", [])
        if isinstance(component, Mapping)
    ]
    primary = next((component for component in components if component.get("role") == "primary"), None)
    guardrails = [component for component in components if component.get("role") == "guardrail"]
    secondaries = [component for component in components if component.get("role") == "secondary"]
    target_met = result.get("target_met") is True
    counted_reason = _mission_count_reason(evaluation.status, components, target_met)
    return {
        "evaluation_id": evaluation.id,
        "mission_id": evaluation.mission_id,
        "owner_steam_id": evaluation.owner_steam_id,
        "evaluated_window": result.get("evaluation_window_json") or {},
        "source_metric_snapshot_ids": _int_list(result.get("source_metric_snapshot_ids")),
        "status": evaluation.status,
        "confidence": evaluation.confidence,
        "caveats": _json_load_sequence(evaluation.caveats_json),
        "primary_metric_result": _component_summary(primary),
        "secondary_metric_results": [_component_summary(component) for component in secondaries],
        "guardrail_results": [_component_summary(component) for component in guardrails],
        "snapshot_comparison": result.get("snapshot_comparison") or {},
        "target_met": target_met,
        "counted": target_met,
        "why_counted_or_not": counted_reason,
        "progress_explanation": result.get("progress_explanation")
        or _progress_explanation(
            evaluation.status,
            result.get("snapshot_comparison") or {},
            _json_load_sequence(evaluation.caveats_json),
        ),
    }


def serialize_active_mission_summary(
    mission: CoachMission,
    *,
    latest_evaluation: MissionProgressEvaluation | None = None,
) -> dict[str, Any]:
    mission_payload = _mapping(_json_load_mapping(mission.source_payload_json).get("mission_payload"))
    success_metric = _mapping(mission_payload.get("success_metric"))
    target_metric = _optional_str(success_metric.get("metric_name"))
    domain_key = mission_domain_key(mission)
    progress = (
        serialize_mission_progress_evaluation(latest_evaluation)
        if latest_evaluation is not None
        else _no_evaluation_progress_summary(mission, target_metric=target_metric)
    )
    comparison = _mapping(progress.get("snapshot_comparison"))
    before = _mapping(comparison.get("before"))
    after = _mapping(comparison.get("after"))
    primary = _mapping(progress.get("primary_metric_result"))
    metric_name = (
        _optional_str(comparison.get("metric_name"))
        or _optional_str(primary.get("metric_name"))
        or target_metric
    )
    return {
        "mission_id": mission.id,
        "title": mission.title,
        "mission_status": mission.status,
        "owner_steam_id": mission.owner_steam_id,
        "domain_key": domain_key,
        "problem_key": mission_problem_key(mission),
        "target_metric": target_metric,
        "mission_payload_type": _mission_payload_type(mission_payload, domain_key=domain_key),
        "metric": metric_name,
        "baseline_value": before.get("value") if before else primary.get("baseline_value"),
        "current_value": after.get("value") if after else primary.get("evaluation_value"),
        "delta": comparison.get("delta") if comparison else primary.get("delta"),
        "confidence": progress.get("confidence"),
        "caveats": list(progress.get("caveats") or []),
        "counted": progress.get("counted") is True,
        "progress_status": progress.get("status"),
        "progress_explanation": progress.get("progress_explanation"),
        "coach_feedback": _active_mission_feedback(
            mission_title=mission.title,
            progress_status=str(progress.get("status") or "no_evaluation_yet"),
            metric_name=metric_name,
            progress_explanation=_optional_str(progress.get("progress_explanation")),
        ),
        "latest_progress_evaluation": progress,
        "suppression_key": mission_suppression_key_from_payload(
            owner_user_id=mission.user_id,
            owner_steam_id=mission.owner_steam_id,
            mission_payload=mission_payload,
            domain_key=domain_key,
            problem_key=mission_problem_key(mission),
        ),
    }


def mission_payload_from_insight_card(
    insight_card: Mapping[str, Any],
    *,
    title: str | None = None,
    duration: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    readiness = _mapping(_mission_readiness(insight_card))
    if not _readiness_allows_mission_payload(readiness):
        return None
    criteria_specs = _criteria_specs_from_insight_card(insight_card)
    if not criteria_specs:
        return None
    linked_insight: dict[str, Any] = {
        "source_insight_card_id": _optional_str(insight_card.get("id") or insight_card.get("card_id")),
        "source": "insight_card",
    }
    trend_evidence = _mapping(readiness.get("trend_evidence"))
    if trend_evidence:
        linked_insight["trend_evidence"] = trend_evidence
    return _mission_payload_from_parts(
        title=title or _mission_title(
            problem=str(insight_card.get("problem") or ""),
            primary_metric=str(criteria_specs[0]["metric_name"]),
        ),
        problem=str(insight_card.get("problem") or ""),
        recommended_focus=str(insight_card.get("recommended_focus") or ""),
        caveats=_string_sequence(insight_card.get("caveats")),
        readiness=readiness,
        criteria_specs=criteria_specs,
        duration=duration,
        linked_insight=linked_insight,
    )


def mission_payload_from_hypothesis(
    hypothesis: CoachHypothesis,
    *,
    title: str | None = None,
    duration: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    if not _readiness_allows_mission_payload(readiness):
        return None
    criteria_specs = _criteria_specs_from_hypothesis(hypothesis)
    if not criteria_specs:
        return None
    linked_insight: dict[str, Any] = {
        "source_hypothesis_id": hypothesis.id,
        "source_insight_card_id": hypothesis.source_insight_card_id,
        "analysis_run_id": hypothesis.analysis_run_id,
        "source": "coach_hypothesis",
    }
    trend_evidence = _mapping(readiness.get("trend_evidence"))
    if trend_evidence:
        linked_insight["trend_evidence"] = trend_evidence
    return _mission_payload_from_parts(
        title=title or _mission_title(problem=hypothesis.problem, primary_metric=str(criteria_specs[0]["metric_name"])),
        problem=hypothesis.problem,
        recommended_focus=hypothesis.recommended_focus,
        caveats=_json_load_sequence(hypothesis.caveats_json),
        readiness=readiness,
        criteria_specs=criteria_specs,
        duration=duration,
        linked_insight=linked_insight,
    )


def validate_mission_payload(
    raw_payload: Any,
    *,
    path: str = "$.mission_payload",
) -> tuple[MissionPayloadValidationIssue, ...]:
    if not isinstance(raw_payload, Mapping):
        return (
            MissionPayloadValidationIssue(
                "invalid_mission_payload",
                "Mission payload must be an object.",
                path,
            ),
        )
    payload = dict(raw_payload)
    issues: list[MissionPayloadValidationIssue] = []
    for field in REQUIRED_MISSION_PAYLOAD_FIELDS:
        if field not in payload:
            issues.append(
                MissionPayloadValidationIssue(
                    "missing_mission_payload_field",
                    f"Missing required mission payload field: {field}.",
                    f"{path}.{field}",
                )
            )
    _validate_payload_non_empty_string(payload, "title", path, issues)
    _validate_payload_non_empty_string(payload, "goal", path, issues)
    _validate_mission_rules(payload.get("rules"), path, issues)
    _validate_mission_duration(payload.get("duration"), path, issues)
    _validate_mission_success_metric(payload.get("success_metric"), path, issues)
    _validate_mission_failure_condition(payload.get("failure_condition"), path, issues)
    linked_insight = payload.get("linked_insight")
    if linked_insight is not None and not isinstance(linked_insight, Mapping):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_linked_insight",
                "Mission linked_insight must be an object when present.",
                f"{path}.linked_insight",
            )
        )
    return tuple(issues)


def serialize_mission_payload(raw_payload: Any) -> dict[str, Any]:
    if validate_mission_payload(raw_payload):
        return {}
    payload = dict(raw_payload)
    return MissionPayload(
        title=str(payload["title"]).strip(),
        goal=str(payload["goal"]).strip(),
        rules=tuple(str(rule).strip() for rule in payload["rules"]),
        duration=dict(payload["duration"]),
        success_metric=dict(payload["success_metric"]),
        failure_condition=dict(payload["failure_condition"]),
        linked_insight=dict(payload.get("linked_insight") or {}),
        schema_version=str(payload.get("schema_version") or MISSION_PAYLOAD_SCHEMA_VERSION),
    ).to_dict()


def serialize_coach_mission(mission: CoachMission) -> dict[str, Any]:
    source_payload = _json_load_mapping(mission.source_payload_json)
    legacy_domain_key = source_payload.get("mission_domain_key") or source_payload.get("domain_key")
    return {
        "mission_id": mission.id,
        "hypothesis_id": mission.hypothesis_id,
        "user_id": mission.user_id,
        "owner_steam_id": mission.owner_steam_id,
        "status": mission.status,
        "domain_key": mission_domain_key(mission),
        "problem_key": mission_problem_key(mission),
        "legacy_domain_key": legacy_domain_key if legacy_domain_key != mission_domain_key(mission) else None,
        "title": mission.title,
        "focus": mission.focus,
        "mission_payload": serialize_mission_payload(source_payload.get("mission_payload")),
        "source_payload": source_payload,
        "activated_at": mission.activated_at.isoformat() if mission.activated_at else None,
        "ended_at": mission.ended_at.isoformat() if mission.ended_at else None,
    }


def mission_domain_key(mission: CoachMission) -> str | None:
    source_payload = _json_load_mapping(mission.source_payload_json)
    domain_key = source_payload.get("mission_domain_key") or source_payload.get("domain_key")
    if domain_key:
        return canonicalize_domain_key(str(domain_key))
    mission_payload = _mapping(source_payload.get("mission_payload"))
    success_metric = _mapping(mission_payload.get("success_metric"))
    metric_name = success_metric.get("metric_name")
    if metric_name:
        return _domain_key_for_metric(str(metric_name))
    return None


def mission_problem_key(mission: CoachMission) -> str | None:
    source_payload = _json_load_mapping(mission.source_payload_json)
    problem_key = source_payload.get("problem_key")
    if problem_key:
        return canonicalize_domain_key(str(problem_key))
    return mission_domain_key(mission)


def _select_owner_metric_snapshots_for_window(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str,
    window_type: str,
    match_ids: Sequence[int] | None,
    match_limit: int | None,
) -> list[MetricSnapshot]:
    owner = owner_steam_id.strip()
    if not owner:
        return []
    identity_filter = (
        (MetricSnapshot.player_steamid == owner)
        | (
            MetricSnapshot.player_steamid.is_(None)
            & (MetricSnapshot.player_key == f"steam:{owner}")
        )
    )
    stmt = (
        select(MetricSnapshot)
        .join(Match, Match.id == MetricSnapshot.match_id)
        .where(Match.user_id == user_id)
        .where(identity_filter)
        .where(MetricSnapshot.semantic_version == "3.0.0")
        .where(MetricSnapshot.validation_status == "validated")
        .order_by(Match.played_at.desc().nullslast(), Match.id.desc(), MetricSnapshot.id.desc())
    )
    if window_type == "custom_match_set":
        stmt = stmt.where(MetricSnapshot.match_id.in_([int(match_id) for match_id in (match_ids or [])]))
    rows = list(db.scalars(stmt).all())
    if match_limit is None:
        return rows
    selected: list[MetricSnapshot] = []
    seen_match_ids: set[int] = set()
    for snapshot in rows:
        if snapshot.match_id not in seen_match_ids and len(seen_match_ids) >= match_limit:
            continue
        selected.append(snapshot)
        seen_match_ids.add(snapshot.match_id)
    return selected


def _utility_trend_evidence_from_snapshots(
    snapshots: Sequence[MetricSnapshot],
) -> UtilityTrendEvidence:
    candidates_by_match: dict[int, list[dict[str, Any]]] = {}
    match_ids_descending: list[int] = []
    caveats: list[str] = []
    blocking_reason_codes: set[str] = set()
    metric_seen = False
    accepted_source_seen = False
    insufficient_confidence_seen = False
    invalid_sample_identity_seen = False

    for raw_snapshot in snapshots:
        snapshot = _snapshot_to_mapping(raw_snapshot)
        metrics = _snapshot_payload_mapping(snapshot, "metrics", "metrics_json")
        if EFFECTIVE_UTILITY_METRIC not in metrics:
            continue
        metric_seen = True
        value = _metric_numeric_value(metrics.get(EFFECTIVE_UTILITY_METRIC))
        if value is None:
            continue
        match_id = _optional_positive_int(snapshot.get("match_id"))
        snapshot_id = _optional_positive_int(snapshot.get("id"))
        if match_id is None or snapshot_id is None:
            invalid_sample_identity_seen = True
            continue
        if match_id not in match_ids_descending:
            match_ids_descending.append(match_id)
        source = _optional_str(snapshot.get("source")) or "unknown"
        confidence_payload = _snapshot_payload_mapping(
            snapshot,
            "confidence_baseline",
            "confidence_baseline_json",
        )
        confidence = _metric_confidence_metadata(confidence_payload, EFFECTIVE_UTILITY_METRIC)
        candidates_by_match.setdefault(match_id, []).append(
            {
                "match_id": match_id,
                "snapshot_id": snapshot_id,
                "source": source,
                "value": value,
                "confidence": INSIGHT_CONFIDENCE_SCORES.get(confidence["level"]),
                "confidence_level": confidence["level"],
                "usable_for_missions": confidence["usable_for_missions"],
                "sample_rounds": _metric_sample_rounds(snapshot, metrics),
                "source_parser_artifact_id": _optional_int(snapshot.get("source_parser_artifact_id")),
                "source_event_set_id": _optional_str(snapshot.get("source_event_set_id")),
            }
        )
        caveats.extend(_snapshot_caveats(snapshot))

    supported_observations: list[dict[str, Any]] = []
    for match_id in reversed(match_ids_descending):
        resolution = _resolve_metric_observation(
            EFFECTIVE_UTILITY_METRIC,
            match_id,
            candidates_by_match[match_id],
        )
        canonical = resolution["canonical"]
        if canonical is None:
            blocking_reason_codes.add("conflicting_metric_sources")
            continue
        if canonical.get("source") != UTILITY_SNAPSHOT_SOURCE:
            continue
        accepted_source_seen = True
        if (
            canonical.get("confidence_level") not in MISSION_ELIGIBLE_CONFIDENCE_LEVELS
            or canonical.get("usable_for_missions") is not True
        ):
            insufficient_confidence_seen = True
            continue
        supported_observations.append(canonical)
        if resolution["deduplicated_snapshot_ids"]:
            caveats.append(
                "Duplicate effective utility damage observations were canonically resolved without increasing "
                "the supported match count."
            )

    if invalid_sample_identity_seen:
        blocking_reason_codes.add("invalid_sample_identity")
    if not metric_seen:
        blocking_reason_codes.add("effective_enemy_utility_damage_unavailable")
    elif not accepted_source_seen:
        blocking_reason_codes.add("utility_source_not_accepted")
    if insufficient_confidence_seen and not supported_observations:
        blocking_reason_codes.add("insufficient_confidence")

    latest_supported = supported_observations[-MAX_UTILITY_TREND_SUPPORTED_MATCHES:]
    ignored_observations = supported_observations[: -len(latest_supported)] if latest_supported else []
    evidence_available = bool(latest_supported) and not {
        "conflicting_metric_sources",
        "invalid_sample_identity",
    }.intersection(blocking_reason_codes)
    if len(latest_supported) < MIN_UTILITY_TREND_SUPPORTED_MATCHES:
        blocking_reason_codes.add("insufficient_supported_matches")

    segment_size = len(latest_supported) // 2
    if segment_size < MIN_UTILITY_TREND_SEGMENT_MATCHES:
        blocking_reason_codes.update(
            {"insufficient_baseline_segment", "insufficient_recent_segment"}
        )

    paired_observations: list[dict[str, Any]] = []
    if segment_size >= MIN_UTILITY_TREND_SEGMENT_MATCHES:
        paired_observations = latest_supported[-(segment_size * 2) :]
        ignored_observations.extend(latest_supported[: len(latest_supported) - len(paired_observations)])
    baseline_observations = paired_observations[:segment_size]
    recent_observations = paired_observations[segment_size:]
    baseline_value = (
        sum(float(item["value"]) for item in baseline_observations) / len(baseline_observations)
        if baseline_observations
        else None
    )
    recent_value = (
        sum(float(item["value"]) for item in recent_observations) / len(recent_observations)
        if recent_observations
        else None
    )
    absolute_change: float | None = None
    absolute_gap = 0.0
    relative_change: float | None = None
    relative_drop = 0.0
    deficiency_detected = False
    if baseline_value is not None and recent_value is not None:
        if baseline_value <= 0:
            blocking_reason_codes.add("invalid_baseline")
        else:
            absolute_change = recent_value - baseline_value
            absolute_gap = max(0.0, baseline_value - recent_value)
            relative_change = absolute_change / baseline_value
            relative_drop = absolute_gap / baseline_value
            if recent_value >= baseline_value:
                blocking_reason_codes.add("utility_trend_not_negative")
            elif relative_drop < UTILITY_NEGATIVE_TREND_MATERIALITY:
                blocking_reason_codes.add("utility_drop_below_materiality_gate")
            else:
                deficiency_detected = True

    mission_ready = evidence_available and deficiency_detected and not blocking_reason_codes
    used_observations = [*baseline_observations, *recent_observations]
    confidence_observations = used_observations or latest_supported
    confidence = _lowest_confidence_level(
        [str(item.get("confidence_level") or "low") for item in confidence_observations]
    )
    sources = sorted({str(item.get("source")) for item in confidence_observations})
    if sources:
        trend_source = "+".join(sources)
    elif accepted_source_seen:
        trend_source = UTILITY_SNAPSHOT_SOURCE
    else:
        trend_source = "unavailable"
    return UtilityTrendEvidence(
        evidence_available=evidence_available,
        deficiency_detected=deficiency_detected,
        mission_ready=mission_ready,
        supported_match_ids=tuple(int(item["match_id"]) for item in latest_supported),
        supported_snapshot_ids=tuple(int(item["snapshot_id"]) for item in latest_supported),
        ignored_oldest_match_ids=tuple(int(item["match_id"]) for item in ignored_observations),
        baseline_match_ids=tuple(int(item["match_id"]) for item in baseline_observations),
        recent_match_ids=tuple(int(item["match_id"]) for item in recent_observations),
        baseline_snapshot_ids=tuple(int(item["snapshot_id"]) for item in baseline_observations),
        recent_snapshot_ids=tuple(int(item["snapshot_id"]) for item in recent_observations),
        baseline_value=round(baseline_value, 3) if baseline_value is not None else None,
        recent_value=round(recent_value, 3) if recent_value is not None else None,
        absolute_change=round(absolute_change, 3) if absolute_change is not None else None,
        absolute_gap=round(absolute_gap, 3),
        relative_change=round(relative_change, 6) if relative_change is not None else None,
        relative_drop=round(relative_drop, 6),
        severity=round(max(0.0, relative_drop), 6),
        confidence=confidence,
        source=trend_source,
        caveats=tuple(sorted(set(caveats))),
        materiality_threshold=UTILITY_NEGATIVE_TREND_MATERIALITY,
        reason_codes=tuple(sorted(blocking_reason_codes)),
    )


def _rolling_window_from_snapshots(
    *,
    user_id: int,
    owner_steam_id: str,
    window_type: str,
    snapshots: Sequence[MetricSnapshot],
    utility_snapshots: Sequence[MetricSnapshot],
) -> RollingMissionWindow:
    values_by_metric: dict[str, list[float]] = {}
    confidence_by_metric: dict[str, list[str]] = {}
    usable_by_metric: dict[str, list[bool]] = {}
    sample_rounds_by_metric: dict[str, int] = {}
    source_values = {snapshot.source for snapshot in snapshots}
    caveats: list[str] = []
    match_ids: list[int] = []
    snapshot_ids: list[int] = []
    for snapshot in snapshots:
        if snapshot.match_id not in match_ids:
            match_ids.append(snapshot.match_id)
        snapshot_ids.append(snapshot.id)
        snapshot_payload = _snapshot_to_mapping(snapshot)
        metrics = _snapshot_payload_mapping(snapshot_payload, "metrics", "metrics_json")
        confidence_payload = _snapshot_payload_mapping(
            snapshot_payload,
            "confidence_baseline",
            "confidence_baseline_json",
        )
        for metric_name in ROLLING_MISSION_METRICS:
            if metric_name == EFFECTIVE_UTILITY_METRIC:
                continue
            if metric_name not in metrics:
                continue
            value = _metric_numeric_value(metrics[metric_name])
            if value is None:
                continue
            values_by_metric.setdefault(metric_name, []).append(value)
            confidence = _metric_confidence_metadata(confidence_payload, metric_name)
            confidence_by_metric.setdefault(metric_name, []).append(confidence["level"])
            usable_by_metric.setdefault(metric_name, []).append(confidence["usable_for_missions"])
            rounds = _sample_rounds_for_metric(metric_name, metrics, snapshot_payload)
            if rounds:
                sample_rounds_by_metric[metric_name] = sample_rounds_by_metric.get(metric_name, 0) + rounds
        caveats.extend(_snapshot_caveats(snapshot_payload))

    metrics = {
        metric_name: round(sum(values) / len(values), 3)
        for metric_name, values in values_by_metric.items()
        if values
    }
    metric_samples = {
        metric_name: {
            "snapshot_count": len(values_by_metric.get(metric_name, [])),
            "sample_matches": len(match_ids),
            "sample_rounds": sample_rounds_by_metric.get(metric_name, 0),
            "confidence": _lowest_confidence_level(confidence_by_metric.get(metric_name, [])),
            "usable_for_missions": bool(usable_by_metric.get(metric_name))
            and all(usable_by_metric.get(metric_name, [])),
        }
        for metric_name in sorted(values_by_metric)
    }
    utility_trend = _utility_trend_evidence_from_snapshots(utility_snapshots)
    if utility_trend.recent_value is not None:
        metrics[EFFECTIVE_UTILITY_METRIC] = utility_trend.recent_value
    if utility_trend.supported_match_ids:
        metric_samples[EFFECTIVE_UTILITY_METRIC] = {
            "snapshot_count": len(utility_trend.supported_snapshot_ids),
            "sample_matches": len(utility_trend.supported_match_ids),
            "sample_rounds": 0,
            "confidence": utility_trend.confidence,
            "usable_for_missions": utility_trend.evidence_available,
            "canonical_source": utility_trend.source,
            "reason_codes": list(utility_trend.reason_codes),
        }
    eligible_confidences = [
        str(sample["confidence"])
        for sample in metric_samples.values()
        if sample.get("usable_for_missions") is True
    ]
    window_confidence = _lowest_confidence_level(eligible_confidences)
    window_caveats = sorted(set([*caveats, *utility_trend.caveats]))
    if not snapshots:
        window_caveats.append("No owner-scoped metric snapshots were available for the rolling window.")
    return RollingMissionWindow(
        user_id=user_id,
        owner_steam_id=owner_steam_id,
        window_type=window_type,
        source="+".join(sorted(source_values)) if source_values else "metric_snapshots",
        match_ids=tuple(match_ids),
        metric_snapshot_ids=tuple(snapshot_ids),
        metrics=metrics,
        metric_samples=metric_samples,
        sample_matches=len(match_ids),
        sample_rounds=max(sample_rounds_by_metric.values(), default=0),
        confidence=window_confidence,
        confidence_score=INSIGHT_CONFIDENCE_SCORES.get(window_confidence, 0.25),
        caveats=tuple(window_caveats),
        utility_trend=utility_trend,
    )


def _rolling_candidates_from_window(
    window: RollingMissionWindow,
    *,
    outcome_context: Mapping[str, Any],
    active_mission_summaries: Sequence[Mapping[str, Any]],
) -> list[RollingMissionCandidate]:
    candidates: list[RollingMissionCandidate] = []
    impact_candidate = _impact_leak_candidate(
        window,
        outcome_context=outcome_context,
        active_mission_summaries=active_mission_summaries,
    )
    if impact_candidate is not None:
        candidates.append(impact_candidate)
    for family, metric_order in (
        ("survival_opening", ("opening_death_rate", "survival_rate")),
        ("bad_fight_trade", ("untraded_death_rate",)),
    ):
        candidate = _rolling_candidate_for_family(
            window,
            family=family,
            metric_order=metric_order,
            active_mission_summaries=active_mission_summaries,
        )
        if candidate is not None:
            candidates.append(candidate)
    candidates.sort(
        key=lambda item: (
            item.suppressed_by_active_mission,
            -item.severity,
            -item.confidence_score,
            -item.sample_size,
            item.primary_metric,
            item.family,
        )
    )
    return [
        RollingMissionCandidate(
            rank=index,
            candidate_id=candidate.candidate_id,
            family=candidate.family,
            primary_metric=candidate.primary_metric,
            severity=candidate.severity,
            confidence_score=candidate.confidence_score,
            sample_size=candidate.sample_size,
            suppressed_by_active_mission=candidate.suppressed_by_active_mission,
            suppression_reason=candidate.suppression_reason,
            explanation=candidate.explanation,
            insight_card=candidate.insight_card,
            mission_payload=candidate.mission_payload,
            window_evidence=candidate.window_evidence,
            suppression_key=candidate.suppression_key,
            suppression_reason_codes=candidate.suppression_reason_codes,
        )
        for index, candidate in enumerate(candidates, start=1)
    ]


def _match_outcome_context(
    db: Session,
    *,
    user_id: int,
    match_ids: Sequence[int],
) -> dict[str, Any]:
    requested = {int(match_id) for match_id in match_ids}
    rows = list(
        db.scalars(
            select(Match)
            .where(Match.user_id == user_id)
            .where(Match.id.in_(requested))
            .order_by(Match.played_at.asc().nulls_last(), Match.id.asc())
        ).all()
    )
    accepted = [match for match in rows if str(match.result or "").lower() in {"win", "loss", "draw"}]
    wins = sum(str(match.result).lower() == "win" for match in accepted)
    round_differential = sum((match.rounds_for or 0) - (match.rounds_against or 0) for match in accepted)
    metric_rows = list(
        db.scalars(
            select(MetricSnapshot)
            .where(MetricSnapshot.owner_user_id == user_id)
            .where(MetricSnapshot.match_id.in_([match.id for match in accepted]))
            .where(MetricSnapshot.source == "coach_metric_performance")
            .where(MetricSnapshot.semantic_version == "3.0.0")
            .where(MetricSnapshot.validation_status == "validated")
        ).all()
    )
    by_match = {snapshot.match_id: _json_load_mapping(snapshot.metrics_json) for snapshot in metric_rows}
    observations = [
        {
            "match_id": match.id,
            "result": str(match.result).lower(),
            "adr": _optional_number(by_match.get(match.id, {}).get("adr")),
            "kills_per_round": _optional_number(by_match.get(match.id, {}).get("kills_per_round")),
            "survival_rate": _optional_number(by_match.get(match.id, {}).get("survival_rate")),
        }
        for match in accepted
    ]
    high_impact_non_wins = [
        item
        for item in observations
        if item["result"] != "win"
        and (
            (item["adr"] is not None and item["adr"] >= 80.0)
            or (item["kills_per_round"] is not None and item["kills_per_round"] >= 0.75)
        )
    ]
    return {
        "match_ids": [match.id for match in accepted],
        "sample_matches": len(accepted),
        "wins": wins,
        "losses": sum(str(match.result).lower() == "loss" for match in accepted),
        "draws": sum(str(match.result).lower() == "draw" for match in accepted),
        "win_rate": round(wins / len(accepted), 3) if accepted else None,
        "non_win_rate": round((len(accepted) - wins) / len(accepted), 3) if accepted else None,
        "round_differential": round_differential,
        "chronology": [match.played_at.isoformat() if match.played_at else None for match in accepted],
        "observations": observations,
        "high_impact_non_win_match_ids": [item["match_id"] for item in high_impact_non_wins],
        "high_impact_non_win_count": len(high_impact_non_wins),
    }


def _impact_leak_diagnostics(
    window: RollingMissionWindow,
    outcome_context: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    sample_matches = _optional_int(outcome_context.get("sample_matches")) or 0
    adr = _optional_number(window.metrics.get("adr"))
    kast = _optional_number(window.metrics.get("kast"))
    survival_rate = _optional_number(window.metrics.get("survival_rate"))
    win_rate = _optional_number(outcome_context.get("win_rate"))
    if sample_matches < 5:
        reasons.append("insufficient_supported_matches")
    if window.sample_rounds < 40:
        reasons.append("insufficient_supported_rounds")
    if adr is None or kast is None or survival_rate is None or win_rate is None:
        reasons.append("required_metric_missing")
    if (_optional_int(outcome_context.get("high_impact_non_win_count")) or 0) < 2:
        reasons.append("outcome_vs_impact_mismatch_not_repeated")
    if win_rate is not None and win_rate > 0.5:
        reasons.append("outcome_conversion_leak_not_detected")
    if survival_rate is not None and survival_rate > 0.55:
        reasons.append("death_cost_signal_not_detected")
    for metric_name in ("adr", "kast", "survival_rate"):
        sample = window.metric_samples.get(metric_name) or {}
        if sample.get("confidence") not in MISSION_ELIGIBLE_CONFIDENCE_LEVELS:
            reasons.append(f"{metric_name}_confidence_insufficient")
        if sample.get("usable_for_missions") is not True:
            reasons.append(f"{metric_name}_not_mission_usable")
    return {
        "canonical_domain_key": "impact_leak",
        "family": "impact_leak",
        "claim_supported": not reasons,
        "reason_codes": sorted(set(reasons)),
        "outcomes": dict(outcome_context),
        "metrics": {
            "adr": adr,
            "kast": kast,
            "survival_rate": survival_rate,
            "kills_per_round": window.metrics.get("kills_per_round"),
            "deaths": window.metrics.get("deaths"),
        },
        "minimums": {
            "matches": 5,
            "rounds": 40,
            "high_impact_non_wins": 2,
            "high_impact_adr": 80.0,
            "high_impact_kpr": 0.75,
            "max_win_rate": 0.5,
        },
    }


def _impact_leak_candidate(
    window: RollingMissionWindow,
    *,
    outcome_context: Mapping[str, Any],
    active_mission_summaries: Sequence[Mapping[str, Any]],
) -> RollingMissionCandidate | None:
    diagnostics = _impact_leak_diagnostics(window, outcome_context)
    if diagnostics["claim_supported"] is not True:
        return None
    adr = float(window.metrics["adr"])
    kast = float(window.metrics["kast"])
    survival_rate = float(window.metrics["survival_rate"])
    confidence_level = _lowest_confidence_level(
        [str(window.metric_samples[name]["confidence"]) for name in ("adr", "kast", "survival_rate")]
    )
    outcome_evidence = dict(outcome_context)
    outcome_evidence.update(
        {
            "metric_id": "match_outcome_window",
            "metric_name": "match_outcome_window",
            "source": "matches",
            "metric_confidence": confidence_level,
        }
    )
    readiness = {
        "can_become_mission": True,
        "canonical_domain_key": "impact_leak",
        "family": "impact_leak",
        "target_metric_candidate": "survival_rate",
        "baseline_value": survival_rate,
        "confidence_eligibility": {
            "level": confidence_level,
            "usable_for_missions": True,
            "hard_recommendation_eligible": True,
        },
        "missing_requirements": [],
        "blocking_reason_codes": [],
        "source": "canonical_domain_window",
        "window": window.to_dict(),
        "outcome_context": dict(outcome_context),
        "criteria": [
            {
                "metric_name": "survival_rate",
                "role": "primary",
                "direction": "higher_is_better",
                "baseline_value": survival_rate,
                "target_value": round(min(1.0, survival_rate + 0.05), 3),
                "min_sample_matches": 3,
                "min_sample_rounds": 24,
                "confidence_required": INSIGHT_CONFIDENCE_SCORES[confidence_level],
                "rule": {"source": "impact_leak_conversion", "claim": "death_cost_with_outcome_context"},
            },
            {
                "metric_name": "adr",
                "role": "guardrail",
                "direction": "stay_above",
                "baseline_value": adr,
                "target_value": round(adr * 0.9, 3),
                "min_sample_matches": 3,
                "confidence_required": INSIGHT_CONFIDENCE_SCORES[confidence_level],
                "rule": {"source": "impact_preservation_guardrail"},
            },
            {
                "metric_name": "kast",
                "role": "guardrail",
                "direction": "stay_above",
                "baseline_value": kast,
                "target_value": round(kast * 0.95, 3),
                "min_sample_matches": 3,
                "confidence_required": INSIGHT_CONFIDENCE_SCORES[confidence_level],
                "rule": {"source": "participation_guardrail"},
            },
        ],
    }
    insight_card = {
        "id": f"rolling:{window.window_type}:impact_leak:survival_rate",
        "canonical_domain_key": "impact_leak",
        "family": "impact_leak",
        "problem": (
            "Supported impact is not consistently converting into match outcomes, with repeated death-cost evidence."
        ),
        "evidence": [
            {
                "metric_id": "survival_rate",
                "metric_name": "survival_rate",
                "value": survival_rate,
                "metric_confidence": confidence_level,
                "sample_matches": window.sample_matches,
                "rounds": window.sample_rounds,
                "match_ids": list(window.match_ids),
                "metric_snapshot_ids": list(window.metric_snapshot_ids),
                "source": "coach_metric_performance",
            },
            {
                "metric_id": "adr",
                "metric_name": "adr",
                "value": adr,
                "metric_confidence": confidence_level,
                "source": "coach_metric_performance",
            },
            {
                "metric_id": "kast",
                "metric_name": "kast",
                "value": kast,
                "metric_confidence": confidence_level,
                "source": "coach_metric_performance",
            },
            outcome_evidence,
        ],
        "confidence": confidence_level,
        "caveats": [
            "This is a bounded outcome-versus-impact pattern, not an economy, positioning, clutch, "
            "or tactical-cause diagnosis.",
            "Utility and aim remain supporting context only.",
        ],
        "recommended_focus": "Reduce low-value deaths while preserving ADR and KAST participation.",
        "target_metric_candidates": ["survival_rate"],
        "mission_readiness": readiness,
    }
    mission_payload = mission_payload_from_insight_card(insight_card)
    if mission_payload is None:
        return None
    suppression_key = mission_suppression_key_from_payload(
        owner_user_id=window.user_id,
        owner_steam_id=window.owner_steam_id,
        mission_payload=mission_payload,
        domain_key="impact_leak",
        problem_key="impact_leak",
    )
    suppression = mission_suppression_decision_for_payload(
        candidate_key=suppression_key,
        active_mission_summaries=active_mission_summaries,
    )
    non_win_rate = float(outcome_context.get("non_win_rate") or 0.0)
    severity = round(non_win_rate * max(0.0, 0.55 - survival_rate) + max(0.0, adr - 85.0) / 500.0, 6)
    return RollingMissionCandidate(
        rank=0,
        candidate_id=f"{window.window_type}:impact_leak:survival_rate",
        family="impact_leak",
        primary_metric="survival_rate",
        severity=severity,
        confidence_score=INSIGHT_CONFIDENCE_SCORES[confidence_level],
        sample_size=window.sample_rounds,
        suppressed_by_active_mission=suppression.suppressed,
        suppression_reason=suppression.reason,
        explanation=(
            "Impact and participation are supported, but the outcome window and death-cost signal do not "
            "convert consistently."
        ),
        insight_card=insight_card,
        mission_payload=mission_payload,
        window_evidence={"metric_window": window.to_dict(), "outcome_context": dict(outcome_context)},
        suppression_key=suppression_key,
        suppression_reason_codes=suppression.reason_codes,
    )


def _rolling_candidate_for_family(
    window: RollingMissionWindow,
    *,
    family: str,
    metric_order: Sequence[str],
    active_mission_summaries: Sequence[Mapping[str, Any]],
) -> RollingMissionCandidate | None:
    primary_metric = next(
        (
            metric_name
            for metric_name in metric_order
            if _rolling_metric_is_mission_ready(window, metric_name)
        ),
        None,
    )
    if primary_metric is None:
        return None
    evidence = _rolling_evidence_for_family(window, family=family, primary_metric=primary_metric)
    if not evidence:
        return None
    primary = evidence[0]
    severity = _rolling_metric_severity(
        primary_metric,
        _optional_number(primary.get("value")),
        utility_trend=window.utility_trend,
    )
    if severity <= 0:
        return None
    confidence_level = str(primary.get("metric_confidence") or "low")
    confidence_score = INSIGHT_CONFIDENCE_SCORES.get(confidence_level, 0.25)
    sample_size = _optional_int(primary.get("sample_count") or primary.get("rounds")) or window.sample_rounds
    domain_key = _domain_key_for_metric(primary_metric, family=family)
    insight_card = _rolling_insight_card(
        window,
        family=family,
        primary_metric=primary_metric,
        evidence=evidence,
        confidence_level=confidence_level,
    )
    mission_payload = mission_payload_from_insight_card(insight_card)
    if mission_payload is None:
        return None
    suppression_key = mission_suppression_key_from_payload(
        owner_user_id=window.user_id,
        owner_steam_id=window.owner_steam_id,
        mission_payload=mission_payload,
        domain_key=domain_key,
        problem_key=domain_key,
    )
    suppression = mission_suppression_decision_for_payload(
        candidate_key=suppression_key,
        active_mission_summaries=active_mission_summaries,
    )
    window_evidence = {
        "source": "metric_snapshots",
        "window_type": window.window_type,
        "match_ids": list(window.match_ids),
        "metric_snapshot_ids": list(window.metric_snapshot_ids),
        "sample_matches": window.sample_matches,
        "sample_rounds": window.sample_rounds,
        "confidence": confidence_level,
        "caveats": list(window.caveats),
        "utility_trend": window.utility_trend.to_dict() if primary_metric == EFFECTIVE_UTILITY_METRIC else None,
    }
    explanation = _rolling_candidate_explanation(primary_metric, primary, window)
    return RollingMissionCandidate(
        rank=0,
        candidate_id=f"{window.window_type}:{family}:{primary_metric}",
        family=family,
        primary_metric=primary_metric,
        severity=severity,
        confidence_score=confidence_score,
        sample_size=sample_size,
        suppressed_by_active_mission=suppression.suppressed,
        suppression_reason=suppression.reason,
        explanation=explanation,
        insight_card=insight_card,
        mission_payload=mission_payload,
        window_evidence=window_evidence,
        suppression_key=suppression_key,
        suppression_reason_codes=suppression.reason_codes,
    )


def _rolling_evidence_for_family(
    window: RollingMissionWindow,
    *,
    family: str,
    primary_metric: str,
) -> list[dict[str, Any]]:
    if family == "bad_fight_trade":
        metrics = (primary_metric, "opening_death_rate", "traded_death_rate")
    else:
        metrics = (primary_metric, "survival_rate" if primary_metric == "opening_death_rate" else "opening_death_rate")
    evidence: list[dict[str, Any]] = []
    for metric_name in metrics:
        sample = window.metric_samples.get(metric_name)
        if sample is None or metric_name not in window.metrics:
            continue
        if metric_name == primary_metric and not _rolling_metric_is_mission_ready(window, metric_name):
            return []
        evidence.append(
            {
                "metric_id": metric_name,
                "metric_name": metric_name,
                "value": window.metrics[metric_name],
                "threshold": None,
                "metric_confidence": sample.get("confidence"),
                "sample_count": sample.get("sample_rounds") or sample.get("snapshot_count") or None,
                "rounds": sample.get("sample_rounds") or None,
                "sample_matches": sample.get("sample_matches"),
                "source": "rolling_metric_window",
                "window_type": window.window_type,
                "metric_snapshot_ids": list(window.metric_snapshot_ids),
                "match_ids": list(window.match_ids),
            }
        )
    return evidence


def _rolling_insight_card(
    window: RollingMissionWindow,
    *,
    family: str,
    primary_metric: str,
    evidence: Sequence[Mapping[str, Any]],
    confidence_level: str,
) -> dict[str, Any]:
    canonical_domain_key = canonical_domain_for_family(family)
    if canonical_domain_key not in CANONICAL_COACH_DOMAINS:
        raise ValueError(f"Rolling family is not mission-eligible: {family}")
    primary_value = _optional_number(evidence[0].get("value")) if evidence else None
    problem = {
        "opening_death_rate": "Rolling owner window shows too many opening deaths.",
        "survival_rate": "Rolling owner window shows low round survival.",
        "untraded_death_rate": "Rolling owner window shows too many untraded deaths.",
        EFFECTIVE_UTILITY_METRIC: (
            "Recent effective enemy utility damage has materially declined from the preceding personal baseline."
        ),
    }.get(primary_metric, f"Rolling owner window supports a {primary_metric} mission.")
    caveats = list(window.caveats)
    if primary_metric == EFFECTIVE_UTILITY_METRIC:
        caveats.extend(
            [
                "Utility damage supports personal damage-trend review only; it does not prove grenade quality, "
                "lineup quality, flash value, or an exact tactical cause.",
                "The recovery target is the player's preceding owner-scoped effective enemy utility damage segment.",
            ]
        )
    readiness: dict[str, Any] = {
        "can_become_mission": True,
        "canonical_domain_key": canonical_domain_key,
        "target_metric_candidate": primary_metric,
        "baseline_value": primary_value,
        "confidence_eligibility": {
            "level": confidence_level,
            "usable_for_missions": True,
            "hard_recommendation_eligible": True,
        },
        "missing_requirements": [],
        "blocking_reason_codes": [],
        "source": "rolling_metric_window",
        "family": family,
        "window": window.to_dict(),
    }
    if primary_metric == EFFECTIVE_UTILITY_METRIC:
        trend = window.utility_trend
        readiness["baseline_value"] = trend.recent_value
        readiness["trend_evidence"] = trend.to_dict()
        readiness["criteria"] = [
            {
                "metric_name": EFFECTIVE_UTILITY_METRIC,
                "role": "primary",
                "direction": "higher_is_better",
                "baseline_value": trend.recent_value,
                "target_value": trend.baseline_value,
                "min_sample_matches": 3,
                "confidence_required": INSIGHT_CONFIDENCE_SCORES.get(confidence_level, 0.6),
                "rule": {
                    "source": "personal_utility_negative_trend",
                    "target_source": "preceding_personal_baseline_segment",
                },
            },
            {
                "metric_name": EFFECTIVE_UTILITY_METRIC,
                "role": "guardrail",
                "direction": "stay_above",
                "baseline_value": trend.recent_value,
                "target_value": trend.recent_value,
                "confidence_required": INSIGHT_CONFIDENCE_SCORES.get(confidence_level, 0.6),
                "rule": {
                    "source": "recent_segment_deterioration_guardrail",
                    "baseline_comparison": "do_not_drop_below_recent_personal_segment",
                },
            },
        ]
    return {
        "id": f"rolling:{window.window_type}:{family}:{primary_metric}",
        "canonical_domain_key": canonical_domain_key,
        "family": family,
        "problem": problem,
        "evidence": [dict(item) for item in evidence],
        "confidence": confidence_level,
        "caveats": sorted(set(caveats)),
        "recommended_focus": _rolling_recommended_focus(primary_metric),
        "target_metric_candidates": [primary_metric],
        "mission_readiness": readiness,
    }


def _rolling_metric_is_mission_ready(window: RollingMissionWindow, metric_name: str) -> bool:
    if metric_name == EFFECTIVE_UTILITY_METRIC:
        return window.utility_trend.mission_ready
    sample = window.metric_samples.get(metric_name)
    if sample is None:
        return False
    if sample.get("usable_for_missions") is not True:
        return False
    if sample.get("confidence") not in MISSION_ELIGIBLE_CONFIDENCE_LEVELS:
        return False
    if metric_name not in window.metrics:
        return False
    if window.sample_matches < MIN_ROLLING_WINDOW_MATCHES:
        return False
    sample_rounds = _optional_int(sample.get("sample_rounds")) or 0
    return sample_rounds >= MIN_ROLLING_WINDOW_ROUNDS


def _rolling_metric_severity(
    metric_name: str,
    value: float | None,
    *,
    utility_trend: UtilityTrendEvidence | None = None,
) -> float:
    if value is None:
        return 0.0
    if metric_name == "untraded_death_rate":
        return round(max(0.0, value - 0.5), 3)
    if metric_name == "opening_death_rate":
        return round(max(0.0, value - 0.2), 3)
    if metric_name == "survival_rate":
        return round(max(0.0, 0.6 - value), 3)
    if metric_name == EFFECTIVE_UTILITY_METRIC:
        return utility_trend.severity if utility_trend is not None else 0.0
    return 0.0


def _metric_confidence_metadata(confidence_payload: Mapping[str, Any], metric_name: str) -> dict[str, Any]:
    metric_confidences = confidence_payload.get("metrics")
    raw_value = metric_confidences.get(metric_name) if isinstance(metric_confidences, Mapping) else None
    if isinstance(raw_value, Mapping):
        level = _optional_lower_str(raw_value.get("level") or raw_value.get("metric_confidence")) or "low"
        usable = raw_value.get("usable_for_missions") is True
        hard_eligible = raw_value.get("hard_recommendation_eligible") is True
    else:
        level = _optional_lower_str(raw_value) or "low"
        usable = level in MISSION_ELIGIBLE_CONFIDENCE_LEVELS
        hard_eligible = usable
    return {
        "level": level,
        "usable_for_missions": usable and hard_eligible,
    }


def _sample_rounds_for_metric(metric_name: str, metrics: Mapping[str, Any], snapshot: Mapping[str, Any]) -> int:
    if metric_name in {"untraded_death_rate", "traded_death_rate"}:
        known_deaths = _optional_int(metrics.get("trade_status_known_deaths"))
        if known_deaths is not None:
            return known_deaths
    rounds = _optional_int(metrics.get("rounds_played"))
    if rounds is not None:
        return rounds
    return _sample_count(snapshot, "rounds")


def _lowest_confidence_level(levels: Sequence[str]) -> str:
    ordered = {"low": 0, "medium": 1, "high": 2}
    known = [level for level in levels if level in ordered]
    if not known:
        return "low"
    return min(known, key=lambda item: ordered[item])


def _rolling_candidate_explanation(
    primary_metric: str,
    primary: Mapping[str, Any],
    window: RollingMissionWindow,
) -> str:
    if primary_metric == EFFECTIVE_UTILITY_METRIC:
        trend = window.utility_trend
        return (
            f"Generated from deterministic owner utility trend segments because recent {EFFECTIVE_UTILITY_METRIC} was "
            f"{_format_metric_value(trend.recent_value)} versus the preceding personal baseline of "
            f"{_format_metric_value(trend.baseline_value)} ({trend.relative_drop:.1%} decline)."
        )
    value = _optional_number(primary.get("value"))
    value_text = _format_metric_value(value)
    return (
        f"Generated from {window.window_type} owner metric snapshots because {primary_metric} was {value_text} "
        f"with {primary.get('metric_confidence')} confidence across {window.sample_matches} matches."
    )


def _rolling_recommended_focus(primary_metric: str) -> str:
    if primary_metric == "untraded_death_rate":
        return "Avoid isolated fights unless a teammate can trade the death."
    if primary_metric == "opening_death_rate":
        return "Delay first contact and take opening fights only with trade support."
    if primary_metric == "survival_rate":
        return "Prioritize staying alive through early fights before taking isolated space."
    if primary_metric == EFFECTIVE_UTILITY_METRIC:
        return (
            "Recover supported utility damage toward the preceding personal baseline without inferring tactical cause."
        )
    return f"Improve {primary_metric.replace('_', ' ')} with supported owner metrics."


def _rolling_suppression_reason(*, suppressed_by_metric: bool, suppressed_by_domain: bool) -> str | None:
    if suppressed_by_metric:
        return "active_mission_same_primary_metric"
    if suppressed_by_domain:
        return "active_mission_same_domain"
    return None


def _active_mission_primary_metrics(db: Session, *, user_id: int, owner_steam_id: str) -> set[str]:
    metrics: set[str] = set()
    for mission in list_active_coach_missions(db, user_id=user_id, owner_steam_id=owner_steam_id):
        source_payload = _json_load_mapping(mission.source_payload_json)
        mission_payload = _mapping(source_payload.get("mission_payload"))
        success_metric = _mapping(mission_payload.get("success_metric"))
        metric_name = success_metric.get("metric_name")
        if metric_name:
            metrics.add(str(metric_name))
    return metrics


def _active_mission_domain_keys(db: Session, *, user_id: int, owner_steam_id: str) -> set[str]:
    keys: set[str] = set()
    for mission in list_active_coach_missions(db, user_id=user_id, owner_steam_id=owner_steam_id):
        domain_key = mission_domain_key(mission)
        if domain_key:
            keys.add(domain_key)
    return keys


def _handle_duplicate_active_mission(
    db: Session,
    *,
    user_id: int,
    owner_steam_id: str | None,
    domain_key: str | None,
    duplicate_policy: str,
    replacement_reason: str,
    exclude_mission_id: int | None = None,
) -> None:
    require_canonical_domain(domain_key)
    duplicates = [
        mission
        for mission in list_active_coach_missions(
            db,
            user_id=user_id,
            owner_steam_id=owner_steam_id,
        )
        if mission.id != exclude_mission_id
        and mission.owner_steam_id == owner_steam_id
        and mission_domain_key(mission) == domain_key
    ]
    if not duplicates:
        return
    if duplicate_policy == "allow":
        return
    if duplicate_policy == "reject":
        raise ValueError(f"Duplicate active mission for owner/domain: {user_id}/{owner_steam_id}/{domain_key}")
    ended_at = datetime.now(UTC)
    for duplicate in duplicates:
        previous_status = duplicate.status
        duplicate.status = "cancelled"
        duplicate.ended_at = ended_at
        _record_lifecycle_transition(
            duplicate,
            previous_status=previous_status,
            next_status="cancelled",
            reason=replacement_reason,
            occurred_at=ended_at,
        )


def _validate_mission_transition(previous_status: str, next_status: str) -> None:
    if previous_status == next_status:
        return
    allowed = MISSION_TRANSITIONS.get(previous_status)
    if allowed is None:
        raise ValueError(f"Unsupported mission status: {previous_status}")
    if next_status not in allowed:
        raise ValueError(f"Cannot transition mission from {previous_status} to {next_status}")


def _record_lifecycle_transition(
    mission: CoachMission,
    *,
    previous_status: str,
    next_status: str,
    reason: str,
    occurred_at: datetime | None,
) -> None:
    source_payload = _json_load_mapping(mission.source_payload_json)
    events = source_payload.get("lifecycle_events")
    if not isinstance(events, list):
        events = []
    event_time = occurred_at or datetime.now(UTC)
    events.append(
        {
            "from": previous_status,
            "to": next_status,
            "reason": reason,
            "at": event_time.isoformat(),
        }
    )
    source_payload["lifecycle_events"] = events
    source_payload["lifecycle_status"] = next_status
    mission.source_payload_json = _json_object(source_payload)


def _mission_duration_exceeded(mission: CoachMission, *, observed_matches: int | None) -> bool:
    if observed_matches is None:
        return False
    source_payload = _json_load_mapping(mission.source_payload_json)
    mission_payload = _mapping(source_payload.get("mission_payload"))
    duration = _mapping(mission_payload.get("duration"))
    max_matches = _optional_positive_int(duration.get("max_matches"))
    return max_matches is not None and observed_matches >= max_matches


def _require_owned_analysis_run(db: Session, *, user_id: int, analysis_run_id: int) -> AnalysisRun:
    run = db.get(AnalysisRun, analysis_run_id)
    if run is None:
        raise ValueError(f"Analysis run does not exist: {analysis_run_id}")
    if run.user_id != user_id:
        raise PermissionError("Analysis run belongs to a different user.")
    return run


def _require_owned_hypothesis(db: Session, *, user_id: int, hypothesis_id: int) -> CoachHypothesis:
    hypothesis = db.get(CoachHypothesis, hypothesis_id)
    if hypothesis is None:
        raise ValueError(f"Coach hypothesis does not exist: {hypothesis_id}")
    if hypothesis.user_id != user_id:
        raise PermissionError("Coach hypothesis belongs to a different user.")
    return hypothesis


def _require_owned_mission(db: Session, *, user_id: int, mission_id: int) -> CoachMission:
    mission = db.get(CoachMission, mission_id)
    if mission is None:
        raise ValueError(f"Coach mission does not exist: {mission_id}")
    if mission.user_id != user_id:
        raise PermissionError("Coach mission belongs to a different user.")
    return mission


def _require_mission_hypothesis(db: Session, mission: CoachMission) -> CoachHypothesis:
    if mission.hypothesis_id is None:
        raise ValueError(f"Coach mission has no source hypothesis: {mission.id}")
    hypothesis = db.get(CoachHypothesis, mission.hypothesis_id)
    if hypothesis is None:
        raise ValueError(f"Coach mission source hypothesis does not exist: {mission.hypothesis_id}")
    if hypothesis.user_id != mission.user_id:
        raise PermissionError("Coach mission source hypothesis belongs to a different user.")
    return hypothesis


def _metric_snapshot_window(
    mission: CoachMission,
    evaluation_metric_snapshots: Sequence[Any],
    *,
    metric_names: set[str] | None = None,
) -> dict[str, Any]:
    candidates_by_metric_match: dict[str, dict[int, list[dict[str, Any]]]] = {}
    metric_reason_codes: dict[str, set[str]] = {}
    metric_lineage_ids: dict[str, list[int]] = {}
    caveats: list[str] = []
    snapshot_ids: list[int] = []
    seen_snapshot_keys: set[tuple[str, Any]] = set()
    for index, raw_snapshot in enumerate(evaluation_metric_snapshots):
        snapshot = _snapshot_to_mapping(raw_snapshot)
        _validate_snapshot_owner(mission, snapshot)
        snapshot_id = _optional_int(snapshot.get("id"))
        snapshot_key = ("id", snapshot_id) if snapshot_id is not None else ("position", index)
        if snapshot_key in seen_snapshot_keys:
            continue
        seen_snapshot_keys.add(snapshot_key)
        if snapshot_id is not None:
            snapshot_ids.append(snapshot_id)
        source = _optional_str(snapshot.get("source")) or "unknown"
        match_id = _optional_positive_int(snapshot.get("match_id"))
        metric_payload = _snapshot_payload_mapping(snapshot, "metrics", "metrics_json")
        for metric_name, raw_value in metric_payload.items():
            metric_name = str(metric_name)
            value = _metric_numeric_value(raw_value)
            if value is None:
                continue
            if snapshot_id is not None:
                metric_lineage_ids.setdefault(metric_name, []).append(snapshot_id)
            if match_id is None:
                metric_reason_codes.setdefault(metric_name, set()).add("missing_match_identity")
                continue
            candidates_by_metric_match.setdefault(metric_name, {}).setdefault(match_id, []).append(
                {
                    "snapshot_id": snapshot_id,
                    "source": source,
                    "value": value,
                    "confidence": _metric_snapshot_confidence(snapshot, metric_name),
                    "sample_rounds": _metric_sample_rounds(snapshot, metric_payload),
                    "source_parser_artifact_id": _optional_int(snapshot.get("source_parser_artifact_id")),
                    "source_event_set_id": _optional_str(snapshot.get("source_event_set_id")),
                }
            )
        caveats.extend(_snapshot_caveats(snapshot))

    metric_samples: dict[str, dict[str, Any]] = {}
    for metric_name in sorted(set(candidates_by_metric_match) | set(metric_reason_codes)):
        observations: list[dict[str, Any]] = []
        reason_codes = set(metric_reason_codes.get(metric_name, set()))
        deduplicated_snapshot_ids: list[int] = []
        unresolved_conflict = False
        for match_id, candidates in sorted(candidates_by_metric_match.get(metric_name, {}).items()):
            observation = _resolve_metric_observation(metric_name, match_id, candidates)
            reason_codes.update(observation["reason_codes"])
            deduplicated_snapshot_ids.extend(observation["deduplicated_snapshot_ids"])
            if observation["canonical"] is None:
                unresolved_conflict = True
                continue
            observations.append(observation["canonical"])
        missing_confidence = any(item["confidence"] is None for item in observations)
        if missing_confidence:
            reason_codes.add("missing_metric_specific_confidence")
        canonical_snapshot_ids = _ordered_ints(item["snapshot_id"] for item in observations)
        match_ids = [item["match_id"] for item in observations]
        confidence_values = [item["confidence"] for item in observations if item["confidence"] is not None]
        sources = sorted({item["source"] for item in observations})
        source_lineage = [
            {
                "match_id": match_id,
                "snapshot_id": candidate.get("snapshot_id"),
                "source": candidate.get("source"),
                "source_parser_artifact_id": candidate.get("source_parser_artifact_id"),
                "source_event_set_id": candidate.get("source_event_set_id"),
            }
            for match_id, candidates in sorted(candidates_by_metric_match.get(metric_name, {}).items())
            for candidate in candidates
        ]
        metric_samples[metric_name] = {
            "canonical_source": sources[0] if len(sources) == 1 else "+".join(sources),
            "snapshot_ids": canonical_snapshot_ids,
            "deduplicated_snapshot_ids": _ordered_ints(deduplicated_snapshot_ids),
            "source_snapshot_ids": _ordered_ints(metric_lineage_ids.get(metric_name, [])),
            "match_ids": match_ids,
            "sample_matches": len(match_ids),
            "sample_rounds": sum(item["sample_rounds"] for item in observations),
            "confidence": min(confidence_values) if confidence_values and not missing_confidence else None,
            "observations": [
                {
                    "match_id": item["match_id"],
                    "snapshot_id": item["snapshot_id"],
                    "source": item["source"],
                    "source_parser_artifact_id": item["source_parser_artifact_id"],
                    "source_event_set_id": item["source_event_set_id"],
                }
                for item in observations
            ],
            "source_lineage": source_lineage,
            "value": (
                sum(item["value"] for item in observations) / len(observations)
                if observations and not unresolved_conflict
                else None
            ),
            "reason_codes": sorted(reason_codes),
            "usable": bool(observations) and not unresolved_conflict,
        }

    relevant_names = metric_names if metric_names is not None else set(metric_samples)
    relevant_samples = [metric_samples[name] for name in sorted(relevant_names) if name in metric_samples]
    match_ids = sorted({match_id for sample in relevant_samples for match_id in sample["match_ids"]})
    relevant_confidences = [sample["confidence"] for sample in relevant_samples if sample["confidence"] is not None]
    relevant_confidence_missing = any(sample["confidence"] is None for sample in relevant_samples)
    return {
        "metrics": {
            metric_name: sample["value"]
            for metric_name, sample in metric_samples.items()
            if sample["usable"] and sample["value"] is not None
        },
        "metric_samples": metric_samples,
        "snapshot_ids": _ordered_ints(snapshot_ids),
        "snapshot_count": len(seen_snapshot_keys),
        "match_ids": match_ids,
        "sample_matches": len(match_ids),
        "sample_rounds": max((sample["sample_rounds"] for sample in relevant_samples), default=0),
        "confidence": (
            min(relevant_confidences)
            if relevant_confidences and not relevant_confidence_missing
            else None
        ),
        "caveats": sorted(set(caveats)),
    }


def _resolve_metric_observation(
    metric_name: str,
    match_id: int,
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    authoritative_source = _canonical_metric_source(metric_name)
    authoritative = [item for item in candidates if item.get("source") == authoritative_source]
    eligible = authoritative or list(candidates)
    values = {float(item["value"]) for item in eligible}
    all_values = {float(item["value"]) for item in candidates}
    reason_codes: set[str] = set()
    if len(candidates) > 1:
        reason_codes.add("duplicate_metric_source_deduplicated")
    if len(all_values) > 1:
        reason_codes.add("conflicting_metric_sources")
    if len(values) > 1 or (len(all_values) > 1 and not authoritative):
        return {
            "canonical": None,
            "deduplicated_snapshot_ids": _ordered_ints(item.get("snapshot_id") for item in candidates),
            "reason_codes": sorted(reason_codes),
        }
    selected = min(
        eligible,
        key=lambda item: (
            str(item.get("source") or ""),
            _optional_int(item.get("snapshot_id")) or 0,
        ),
    )
    canonical = dict(selected)
    canonical["match_id"] = match_id
    deduplicated = [
        item.get("snapshot_id")
        for item in candidates
        if item is not selected
    ]
    return {
        "canonical": canonical,
        "deduplicated_snapshot_ids": _ordered_ints(deduplicated),
        "reason_codes": sorted(reason_codes),
    }


def _canonical_metric_source(metric_name: str) -> str:
    if metric_name in UTILITY_SNAPSHOT_METRICS:
        return UTILITY_SNAPSHOT_SOURCE
    return CORE_COMBAT_SNAPSHOT_SOURCE


def _evaluate_criteria(
    criteria: MissionCriteria,
    snapshot_window: Mapping[str, Any],
    *,
    baseline_window: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = _mapping(snapshot_window.get("metrics"))
    metric_sample = _mapping(_mapping(snapshot_window.get("metric_samples")).get(criteria.metric_name))
    baseline_metrics = _mapping(baseline_window.get("metrics")) if baseline_window is not None else {}
    baseline_metric_sample = (
        _mapping(_mapping(baseline_window.get("metric_samples")).get(criteria.metric_name))
        if baseline_window is not None
        else {}
    )
    baseline_from_snapshot = (
        _optional_number(baseline_metrics.get(criteria.metric_name))
        if criteria.metric_name in baseline_metrics
        else None
    )
    baseline = baseline_from_snapshot if baseline_window is not None else criteria.baseline_value
    rule = _json_load_mapping(criteria.rule_json)
    component = {
        "criteria_id": criteria.id,
        "metric_name": criteria.metric_name,
        "role": criteria.role,
        "direction": criteria.direction,
        "baseline_value": baseline,
        "baseline_source": "metric_snapshots" if baseline_window is not None else "mission_activation",
        "baseline_metric_snapshot_ids": list(baseline_metric_sample.get("snapshot_ids") or []),
        "target_value": criteria.target_value,
        "observed_value": _optional_number(metrics.get(criteria.metric_name))
        if criteria.metric_name in metrics
        else None,
        "delta": None,
        "outcome": "insufficient_data",
        "reason_codes": list(metric_sample.get("reason_codes") or []),
        "canonical_source": metric_sample.get("canonical_source"),
        "metric_snapshot_ids": list(metric_sample.get("snapshot_ids") or []),
        "deduplicated_metric_snapshot_ids": list(metric_sample.get("deduplicated_snapshot_ids") or []),
        "match_ids": list(metric_sample.get("match_ids") or []),
        "sample_matches": metric_sample.get("sample_matches", 0),
        "sample_rounds": metric_sample.get("sample_rounds", 0),
        "confidence": metric_sample.get("confidence"),
        "rule": rule,
    }
    sample_reason = _insufficient_sample_reason(criteria, metric_sample)
    confidence_reason = _insufficient_confidence_reason(criteria, metric_sample)
    if criteria.metric_name not in metrics:
        component["reason_codes"].append("missing_metric")
        return component
    if baseline_window is not None and criteria.metric_name not in baseline_metrics:
        component["reason_codes"].append("missing_baseline_metric")
        return component
    if sample_reason:
        if sample_reason == "insufficient_sample_rounds" and not component["sample_rounds"]:
            component["reason_codes"].append("unavailable_round_sample")
        component["reason_codes"].append(sample_reason)
        return component
    if confidence_reason:
        component["reason_codes"].append(confidence_reason)
        return component

    follow_outcome = _not_following_outcome(rule, metrics)
    if follow_outcome is not None:
        component["outcome"] = follow_outcome
        component["reason_codes"].append(follow_outcome)
        return component

    observed = _optional_number(metrics.get(criteria.metric_name))
    if observed is not None and baseline is not None:
        component["delta"] = observed - baseline
    component["outcome"] = _directional_outcome(
        metric_name=criteria.metric_name,
        direction=criteria.direction,
        observed=observed,
        baseline=baseline,
        target=criteria.target_value,
        rule=rule,
    )
    component["target_reached"] = _target_reached(
        direction=criteria.direction,
        observed=observed,
        target=criteria.target_value,
        rule=rule,
    )
    component["reason_codes"].append(component["outcome"])
    return component


def _composite_progress_status(components: Sequence[Mapping[str, Any]]) -> str:
    if not components:
        return "insufficient_data"
    guardrail_outcomes = [
        component.get("outcome")
        for component in components
        if component.get("role") == "guardrail"
    ]
    if any(outcome == "regressing" for outcome in guardrail_outcomes):
        return "regressing"
    if any(outcome == "not_following" for outcome in guardrail_outcomes):
        return "not_following"
    outcomes = [str(component.get("outcome")) for component in components]
    if "insufficient_data" in outcomes:
        return "insufficient_data"
    if "not_following" in outcomes:
        return "not_following"
    if "regressing" in outcomes:
        return "regressing"
    if "improving" in outcomes:
        return "improving"
    return "unchanged"


def _directional_outcome(
    *,
    metric_name: str,
    direction: str,
    observed: float | None,
    baseline: float | None,
    target: float | None,
    rule: Mapping[str, Any],
) -> str:
    if observed is None or baseline is None:
        return "insufficient_data"
    if direction == "lower_is_better":
        return _compare_lower_is_better(observed, baseline)
    if direction == "higher_is_better":
        return _compare_higher_is_better(observed, baseline)
    if direction == "improve_or_same":
        metric_direction = str(rule.get("metric_direction") or _default_metric_direction(metric_name))
        if metric_direction == "lower_is_better":
            return _compare_lower_is_better(observed, baseline, unchanged_when_better=False)
        return _compare_higher_is_better(observed, baseline, unchanged_when_better=False)
    if direction == "not_drop_more_than":
        max_drop = _max_drop(rule, baseline, target)
        return "regressing" if observed < baseline - max_drop else "unchanged"
    if direction == "stay_above":
        floor = target if target is not None else baseline
        return "regressing" if observed < floor else "unchanged"
    if direction == "stay_below":
        ceiling = target if target is not None else baseline
        return "regressing" if observed > ceiling else "unchanged"
    return "insufficient_data"


def _compare_lower_is_better(
    observed: float,
    baseline: float,
    *,
    unchanged_when_better: bool = False,
) -> str:
    if observed < baseline:
        return "unchanged" if unchanged_when_better else "improving"
    if observed > baseline:
        return "regressing"
    return "unchanged"


def _compare_higher_is_better(
    observed: float,
    baseline: float,
    *,
    unchanged_when_better: bool = False,
) -> str:
    if observed > baseline:
        return "unchanged" if unchanged_when_better else "improving"
    if observed < baseline:
        return "regressing"
    return "unchanged"


def _target_reached(
    *,
    direction: str,
    observed: float | None,
    target: float | None,
    rule: Mapping[str, Any],
) -> bool | None:
    if observed is None or target is None:
        return None
    if direction in {"higher_is_better", "stay_above", "improve_or_same"}:
        return observed >= target
    if direction in {"lower_is_better", "stay_below"}:
        return observed <= target
    if direction == "not_drop_more_than":
        return observed >= target
    return None


def _target_met(components: Sequence[Mapping[str, Any]]) -> bool:
    progress_components = [
        component
        for component in components
        if component.get("role") in {"primary", "secondary"}
    ]
    if not progress_components:
        return False
    if not all(component.get("target_reached") is True for component in progress_components):
        return False
    return not any(
        component.get("role") == "guardrail" and component.get("outcome") in {"regressing", "not_following"}
        for component in components
    )


def _not_following_outcome(rule: Mapping[str, Any], metrics: Mapping[str, Any]) -> str | None:
    not_following_if = rule.get("not_following_if")
    if isinstance(not_following_if, Mapping) and _rule_condition_matches(not_following_if, metrics) is True:
        return "not_following"
    follow_rule = rule.get("follow_rule")
    if isinstance(follow_rule, Mapping):
        followed = _rule_condition_matches(follow_rule, metrics)
        if followed is None:
            return "insufficient_data"
        if followed is False:
            return "not_following"
    return None


def _rule_condition_matches(condition: Mapping[str, Any], metrics: Mapping[str, Any]) -> bool | None:
    metric_name = condition.get("metric_name") or condition.get("metric")
    if not metric_name or metric_name not in metrics:
        return None
    observed = _optional_number(metrics.get(str(metric_name)))
    expected = _optional_number(condition.get("value"))
    if observed is None or expected is None:
        return None
    operator = str(condition.get("operator") or ">=")
    if operator == ">=":
        return observed >= expected
    if operator == ">":
        return observed > expected
    if operator == "<=":
        return observed <= expected
    if operator == "<":
        return observed < expected
    if operator == "==":
        return observed == expected
    if operator == "!=":
        return observed != expected
    raise ValueError(f"Unsupported mission rule operator: {operator}")


def _insufficient_sample_reason(
    criteria: MissionCriteria,
    snapshot_window: Mapping[str, Any],
) -> str | None:
    sample_matches = _optional_int(snapshot_window.get("sample_matches")) or 0
    sample_rounds = _optional_int(snapshot_window.get("sample_rounds")) or 0
    if criteria.min_sample_matches is not None and sample_matches < criteria.min_sample_matches:
        return "insufficient_sample_matches"
    if criteria.min_sample_rounds is not None and sample_rounds < criteria.min_sample_rounds:
        return "insufficient_sample_rounds"
    return None


def _insufficient_confidence_reason(
    criteria: MissionCriteria,
    snapshot_window: Mapping[str, Any],
) -> str | None:
    if criteria.confidence_required is None:
        return None
    confidence = _optional_number(snapshot_window.get("confidence"))
    if confidence is None:
        return "missing_confidence"
    if confidence < criteria.confidence_required:
        return "insufficient_confidence"
    return None


def _evaluation_confidence(
    snapshot_window: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
) -> float | None:
    del snapshot_window
    confidences = [_optional_number(component.get("confidence")) for component in components]
    if not confidences or any(confidence is None for confidence in confidences):
        return None
    confidence = min(value for value in confidences if value is not None)
    if any(component.get("outcome") == "insufficient_data" for component in components):
        return min(confidence, 0.25)
    return confidence


def _evaluation_caveats(
    snapshot_window: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
) -> list[str]:
    caveats = [str(caveat) for caveat in snapshot_window.get("caveats") or []]
    for component in components:
        for reason in component.get("reason_codes") or []:
            if reason in {
                "missing_metric",
                "missing_baseline_metric",
                "insufficient_sample_matches",
                "insufficient_sample_rounds",
                "missing_confidence",
                "missing_match_identity",
                "missing_metric_specific_confidence",
                "insufficient_confidence",
                "conflicting_metric_sources",
                "duplicate_metric_source_deduplicated",
                "unavailable_round_sample",
                "not_following",
            }:
                caveats.append(f"{component.get('metric_name')}:{reason}")
    return sorted(set(caveats))


def _component_summary(component: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if component is None:
        return None
    return {
        "criteria_id": component.get("criteria_id"),
        "metric_name": component.get("metric_name"),
        "role": component.get("role"),
        "direction": component.get("direction"),
        "baseline_value": component.get("baseline_value"),
        "baseline_source": component.get("baseline_source"),
        "baseline_metric_snapshot_ids": list(component.get("baseline_metric_snapshot_ids") or []),
        "metric_snapshot_ids": list(component.get("metric_snapshot_ids") or []),
        "deduplicated_metric_snapshot_ids": list(component.get("deduplicated_metric_snapshot_ids") or []),
        "match_ids": list(component.get("match_ids") or []),
        "canonical_source": component.get("canonical_source"),
        "evaluation_value": component.get("observed_value"),
        "delta": component.get("delta"),
        "target_value": component.get("target_value"),
        "outcome": component.get("outcome"),
        "target_reached": component.get("target_reached"),
        "reason_codes": list(component.get("reason_codes") or []),
        "sample_matches": component.get("sample_matches"),
        "sample_rounds": component.get("sample_rounds"),
        "confidence": component.get("confidence"),
    }


def _mission_count_reason(status: str, components: Sequence[Mapping[str, Any]], target_met: bool) -> str:
    if target_met:
        return "Primary and secondary mission targets were reached without failing guardrails."
    blocking = [
        f"{component.get('metric_name')}:{component.get('outcome')}"
        for component in components
        if component.get("outcome") in {"regressing", "insufficient_data", "not_following"}
        or component.get("target_reached") is False
    ]
    if blocking:
        return f"Mission did not count because {', '.join(blocking)}."
    return f"Mission did not count because evaluation status is {status}."


def _snapshot_comparison(
    *,
    mission: CoachMission,
    baseline_window: Mapping[str, Any] | None,
    evaluation_window: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    primary = next((component for component in components if component.get("role") == "primary"), None)
    if primary is None:
        return {}
    success_metric = _mission_success_metric(mission, primary)
    metric_name = str(success_metric.get("metric_name") or primary.get("metric_name") or "")
    before_value = _optional_number(primary.get("baseline_value"))
    after_value = _optional_number(primary.get("observed_value"))
    delta = after_value - before_value if before_value is not None and after_value is not None else None
    baseline_metric_sample = (
        _mapping(_mapping(baseline_window.get("metric_samples")).get(metric_name))
        if baseline_window is not None
        else {}
    )
    return {
        "success_metric": success_metric,
        "before": {
            "metric_snapshot_ids": list(primary.get("baseline_metric_snapshot_ids") or []),
            "deduplicated_metric_snapshot_ids": list(
                baseline_metric_sample.get("deduplicated_snapshot_ids") or []
            ),
            "source_metric_snapshot_ids": list(baseline_metric_sample.get("source_snapshot_ids") or []),
            "canonical_source": baseline_metric_sample.get("canonical_source"),
            "value": before_value,
            "match_ids": list(baseline_metric_sample.get("match_ids") or []),
            "sample_matches": baseline_metric_sample.get("sample_matches") if baseline_window is not None else None,
            "sample_rounds": baseline_metric_sample.get("sample_rounds") if baseline_window is not None else None,
        },
        "after": {
            "metric_snapshot_ids": list(primary.get("metric_snapshot_ids") or []),
            "deduplicated_metric_snapshot_ids": list(primary.get("deduplicated_metric_snapshot_ids") or []),
            "source_metric_snapshot_ids": list(
                _mapping(_mapping(evaluation_window.get("metric_samples")).get(metric_name)).get(
                    "source_snapshot_ids"
                )
                or []
            ),
            "canonical_source": primary.get("canonical_source"),
            "value": after_value,
            "match_ids": list(primary.get("match_ids") or []),
            "sample_matches": primary.get("sample_matches"),
            "sample_rounds": primary.get("sample_rounds"),
        },
        "metric_name": metric_name,
        "direction": success_metric.get("direction") or primary.get("direction"),
        "target_value": success_metric.get("target_value"),
        "delta": delta,
        "status": primary.get("outcome"),
    }


def _mission_success_metric(mission: CoachMission, primary_component: Mapping[str, Any]) -> dict[str, Any]:
    source_payload = _json_load_mapping(mission.source_payload_json)
    mission_payload = _mapping(source_payload.get("mission_payload"))
    success_metric = _mapping(mission_payload.get("success_metric"))
    metric_name = success_metric.get("metric_name") or primary_component.get("metric_name")
    return {
        "metric_name": str(metric_name or ""),
        "direction": str(success_metric.get("direction") or primary_component.get("direction") or ""),
        "target_value": _optional_number(success_metric.get("target_value"))
        if "target_value" in success_metric
        else _optional_number(primary_component.get("target_value")),
        "source": "mission_payload.success_metric" if success_metric else "mission_primary_criteria",
    }


def _no_evaluation_progress_summary(mission: CoachMission, *, target_metric: str | None) -> dict[str, Any]:
    return {
        "evaluation_id": None,
        "mission_id": mission.id,
        "owner_steam_id": mission.owner_steam_id,
        "evaluated_window": {},
        "source_metric_snapshot_ids": [],
        "status": "no_evaluation_yet",
        "confidence": None,
        "caveats": ["no_evaluation_yet"],
        "primary_metric_result": {
            "metric_name": target_metric,
            "role": "primary",
            "reason_codes": ["no_evaluation_yet"],
        },
        "secondary_metric_results": [],
        "guardrail_results": [],
        "snapshot_comparison": {
            "metric_name": target_metric,
            "before": {"metric_snapshot_ids": [], "value": None},
            "after": {"metric_snapshot_ids": [], "value": None},
            "delta": None,
        },
        "target_met": False,
        "counted": False,
        "why_counted_or_not": "Mission has no persisted progress evaluation yet.",
        "progress_explanation": "No persisted mission progress evaluation is available yet.",
    }


def _active_mission_feedback(
    *,
    mission_title: str,
    progress_status: str,
    metric_name: str | None,
    progress_explanation: str | None,
) -> str:
    metric = metric_name or "mission metric"
    if progress_status == "improving":
        return f"{mission_title}: improving on {metric}; continue the active mission focus."
    if progress_status == "unchanged":
        return f"{mission_title}: {metric} is unchanged; continue the active mission focus."
    if progress_status == "regressing":
        return f"{mission_title}: regressing on {metric}; explain the failed metric before changing missions."
    if progress_status == "not_following":
        return f"{mission_title}: not_following; explain what rule was not followed before replacing the mission."
    if progress_status == "insufficient_data":
        return f"{mission_title}: insufficient_data for {metric}; do not make a hard progress or failure claim."
    if progress_status == "no_evaluation_yet":
        return f"{mission_title}: no_evaluation_yet; wait for persisted owner-scoped progress data."
    return progress_explanation or f"{mission_title}: continue the active mission focus."


def _mission_payload_type(payload: Mapping[str, Any], *, domain_key: str | None = None) -> str | None:
    success_metric = _mapping(payload.get("success_metric"))
    metric_name = _optional_str(success_metric.get("metric_name"))
    if domain_key:
        return f"{domain_key}_mission"
    if metric_name:
        return f"{_domain_key_for_metric(metric_name)}_mission"
    schema = _optional_str(payload.get("schema_version"))
    return schema


def _progress_explanation(
    status: str,
    snapshot_comparison: Mapping[str, Any],
    caveats: Sequence[Any],
) -> str:
    metric_name = str(snapshot_comparison.get("metric_name") or "mission metric")
    before = _mapping(snapshot_comparison.get("before")).get("value")
    after = _mapping(snapshot_comparison.get("after")).get("value")
    before_text = _format_metric_value(before)
    after_text = _format_metric_value(after)
    if status == "improving":
        return f"Improving on the assigned focus: {metric_name} moved from {before_text} to {after_text}."
    if status == "unchanged":
        return f"Unchanged on the assigned focus: {metric_name} stayed near {before_text}."
    if status == "regressing":
        return f"Regressing on the assigned focus: {metric_name} moved from {before_text} to {after_text}."
    if status == "not_following":
        return f"Not enough evidence of following the assigned focus rules for {metric_name}."
    reason = ", ".join(str(caveat) for caveat in caveats) or "missing comparable metric data"
    return f"Insufficient data to judge the assigned focus for {metric_name}: {reason}."


def _format_metric_value(value: Any) -> str:
    number = _optional_number(value)
    if number is None:
        return "unknown"
    return f"{number:.3f}".rstrip("0").rstrip(".")


def _snapshot_to_mapping(snapshot: Any) -> dict[str, Any]:
    if isinstance(snapshot, Mapping):
        return dict(snapshot)
    value: dict[str, Any] = {}
    for name in (
        "id",
        "match_id",
        "user_id",
        "owner_steam_id",
        "player_key",
        "player_steamid",
        "source",
        "source_parser_artifact_id",
        "source_event_set_id",
        "metrics",
        "metrics_json",
        "confidence",
        "confidence_baseline",
        "confidence_baseline_json",
        "caveats",
        "caveats_json",
        "metadata",
        "metadata_json",
        "sample_matches",
        "sample_rounds",
    ):
        if hasattr(snapshot, name):
            value[name] = getattr(snapshot, name)
    return value


def _validate_snapshot_owner(mission: CoachMission, snapshot: Mapping[str, Any]) -> None:
    snapshot_user_id = _optional_int(snapshot.get("user_id"))
    if snapshot_user_id is not None and snapshot_user_id != mission.user_id:
        raise PermissionError("Evaluation metric snapshot belongs to a different user.")
    owner_steam_id = snapshot.get("owner_steam_id") or snapshot.get("player_steamid")
    if mission.owner_steam_id and owner_steam_id and str(owner_steam_id) != mission.owner_steam_id:
        raise PermissionError("Evaluation metric snapshot belongs to a different owner.")


def _snapshot_payload_mapping(snapshot: Mapping[str, Any], direct_key: str, json_key: str) -> dict[str, Any]:
    direct = snapshot.get(direct_key)
    if isinstance(direct, Mapping):
        return dict(direct)
    encoded = snapshot.get(json_key)
    if isinstance(encoded, str):
        return _json_load_mapping(encoded)
    if isinstance(encoded, Mapping):
        return dict(encoded)
    return {}


def _metric_numeric_value(raw_value: Any) -> float | None:
    if isinstance(raw_value, Mapping):
        raw_value = raw_value.get("value")
    try:
        return _optional_number(raw_value)
    except (TypeError, ValueError):
        return None


def _metric_snapshot_confidence(snapshot: Mapping[str, Any], metric_name: str) -> float | None:
    confidence_payload = _snapshot_payload_mapping(snapshot, "confidence_baseline", "confidence_baseline_json")
    metric_confidences = confidence_payload.get("metrics")
    metric_confidence = metric_confidences.get(metric_name) if isinstance(metric_confidences, Mapping) else None
    if isinstance(metric_confidence, Mapping):
        for key in ("confidence", "score", "level", "metric_confidence"):
            if key in metric_confidence:
                return _confidence_value(metric_confidence[key])
    elif metric_confidence is not None:
        return _confidence_value(metric_confidence)
    direct_metric_confidences = snapshot.get("metric_confidence")
    if isinstance(direct_metric_confidences, Mapping) and metric_name in direct_metric_confidences:
        return _confidence_value(direct_metric_confidences[metric_name])
    metric_payload = _snapshot_payload_mapping(snapshot, "metrics", "metrics_json")
    if len(metric_payload) == 1 and snapshot.get("confidence") is not None:
        return _confidence_value(snapshot.get("confidence"))
    return None


def _confidence_value(value: Any) -> float | None:
    try:
        return _optional_float(value)
    except (TypeError, ValueError):
        return None


def _metric_sample_rounds(snapshot: Mapping[str, Any], metrics: Mapping[str, Any]) -> int:
    rounds = _optional_int(metrics.get("rounds_played")) if metrics.get("rounds_played") is not None else None
    if rounds is not None and rounds > 0:
        return rounds
    return _sample_count(snapshot, "rounds")


def _ordered_ints(values: Sequence[Any] | Any) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()
    for value in values:
        parsed = _optional_int(value)
        if parsed is not None and parsed not in seen:
            seen.add(parsed)
            ordered.append(parsed)
    return ordered


def _snapshot_caveats(snapshot: Mapping[str, Any]) -> list[str]:
    direct = snapshot.get("caveats")
    if isinstance(direct, Sequence) and not isinstance(direct, str):
        return [str(item) for item in direct]
    encoded = snapshot.get("caveats_json")
    if isinstance(encoded, str):
        return [str(item) for item in _json_load_sequence(encoded)]
    return []


def _sample_count(snapshot: Mapping[str, Any], name: str) -> int:
    direct_key = f"sample_{name}"
    if direct_key in snapshot:
        return _optional_int(snapshot.get(direct_key)) or 0
    sample = snapshot.get("sample")
    if isinstance(sample, Mapping) and name in sample:
        return _optional_int(sample.get(name)) or 0
    metadata = _snapshot_payload_mapping(snapshot, "metadata", "metadata_json")
    if direct_key in metadata:
        return _optional_int(metadata.get(direct_key)) or 0
    if name in metadata:
        return _optional_int(metadata.get(name)) or 0
    return 0


def _max_drop(rule: Mapping[str, Any], baseline: float, target: float | None) -> float:
    configured = _optional_number(rule["max_drop"]) if "max_drop" in rule else None
    if configured is None and "accepted_drop" in rule:
        configured = _optional_number(rule["accepted_drop"])
    if configured is not None:
        return configured
    if target is not None and target < baseline:
        return baseline - target
    return 0.0


def _validate_hypothesis_can_activate(
    hypothesis: CoachHypothesis,
    criteria_specs: Sequence[Mapping[str, Any]],
) -> None:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    confidence_eligibility = readiness.get("confidence_eligibility")
    confidence_level = (
        _optional_lower_str(confidence_eligibility.get("level"))
        if isinstance(confidence_eligibility, Mapping)
        else None
    )
    blocking_reasons = _string_sequence(readiness.get("blocking_reason_codes"))
    if readiness.get("can_become_mission") is not True:
        reason = ",".join(blocking_reasons) or "mission_readiness_not_eligible"
        raise ValueError(f"Coach hypothesis cannot become an active mission: {reason}")
    if confidence_level not in MISSION_ELIGIBLE_CONFIDENCE_LEVELS:
        raise ValueError("Coach hypothesis cannot become an active mission: low_or_unavailable_confidence")
    if isinstance(confidence_eligibility, Mapping):
        if confidence_eligibility.get("usable_for_missions") is not True:
            raise ValueError("Coach hypothesis cannot become an active mission: confidence_not_mission_eligible")
        if confidence_eligibility.get("hard_recommendation_eligible") is not True:
            raise ValueError(
                "Coach hypothesis cannot become an active mission: metric_not_hard_recommendation_eligible"
            )
    if not criteria_specs:
        raise ValueError("Coach hypothesis cannot become an active mission: missing_mission_criteria")
    family = _optional_str(readiness.get("family"))
    domain_key = _optional_str(readiness.get("canonical_domain_key")) or canonical_domain_for_family(family)
    if domain_key is None:
        primary = _primary_criteria_spec(criteria_specs)
        if primary is not None:
            domain_key = _domain_key_for_metric(str(primary.get("metric_name") or ""))
    require_canonical_domain(domain_key)


def _readiness_allows_mission_payload(readiness: Mapping[str, Any]) -> bool:
    if readiness.get("can_become_mission") is not True:
        return False
    if _string_sequence(readiness.get("blocking_reason_codes")):
        return False
    confidence_eligibility = readiness.get("confidence_eligibility")
    if not isinstance(confidence_eligibility, Mapping):
        return False
    confidence_level = _optional_lower_str(confidence_eligibility.get("level"))
    return (
        confidence_level in MISSION_ELIGIBLE_CONFIDENCE_LEVELS
        and confidence_eligibility.get("usable_for_missions") is True
        and confidence_eligibility.get("hard_recommendation_eligible") is True
    )


def _mission_source_payload(
    hypothesis: CoachHypothesis,
    source_payload: Mapping[str, Any] | None,
    mission_payload: Mapping[str, Any] | None,
    *,
    criteria_specs: Sequence[Mapping[str, Any]],
    domain_key: str | None,
) -> dict[str, Any]:
    payload = dict(source_payload or {})
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    payload.update(
        {
            "source_hypothesis_id": hypothesis.id,
            "analysis_run_id": hypothesis.analysis_run_id,
            "source_insight_card_id": hypothesis.source_insight_card_id,
            "baseline_source": "coach_hypothesis_mission_readiness",
            "mission_readiness": readiness,
            "mission_domain_key": domain_key,
            "problem_key": domain_key,
            "activation_metadata": _mission_activation_metadata(
                hypothesis=hypothesis,
                readiness=readiness,
                criteria_specs=criteria_specs,
                domain_key=domain_key,
            ),
        }
    )
    if mission_payload is not None:
        payload["mission_payload"] = dict(mission_payload)
    return payload


def _mission_activation_metadata(
    *,
    hypothesis: CoachHypothesis,
    readiness: Mapping[str, Any],
    criteria_specs: Sequence[Mapping[str, Any]],
    domain_key: str | None,
) -> dict[str, Any]:
    primary = _primary_criteria_spec(criteria_specs)
    return {
        "source_hypothesis_id": hypothesis.id,
        "analysis_run_id": hypothesis.analysis_run_id,
        "source_insight_card_id": hypothesis.source_insight_card_id,
        "owner_steam_id": hypothesis.owner_steam_id,
        "domain_key": domain_key,
        "problem_key": domain_key,
        "primary_metric": primary.get("metric_name") if primary else None,
        "criteria_count": len(criteria_specs),
        "baseline_values": _criteria_values_by_metric(criteria_specs, "baseline_value"),
        "target_values": _criteria_values_by_metric(criteria_specs, "target_value"),
        "confidence_required": primary.get("confidence_required") if primary else None,
        "confidence_eligibility": _mapping(readiness.get("confidence_eligibility")),
        "window": _mapping(readiness.get("window")),
    }


def _mission_domain_key_from_parts(
    *,
    hypothesis: CoachHypothesis,
    criteria_specs: Sequence[Mapping[str, Any]],
    mission_payload: Mapping[str, Any] | None,
) -> str | None:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    source = _optional_str(readiness.get("source"))
    if source == "rolling_metric_window":
        window = _mapping(readiness.get("window"))
        candidate_source = _optional_str(window.get("candidate_family") or readiness.get("family"))
        if candidate_source:
            return _domain_key_for_family(candidate_source)
    mission_payload_metric = _mapping(_mapping(mission_payload).get("success_metric")).get("metric_name")
    if mission_payload_metric:
        return _domain_key_for_metric(str(mission_payload_metric))
    primary = _primary_criteria_spec(criteria_specs)
    if primary is not None:
        return _domain_key_for_metric(str(primary["metric_name"]))
    readiness_metric = _readiness_target_metric(
        readiness,
        _json_load_sequence(hypothesis.target_metric_candidates_json),
    )
    if readiness_metric:
        return _domain_key_for_metric(readiness_metric)
    return None


def _domain_key_for_metric(metric_name: str, *, family: str | None = None) -> str | None:
    if family:
        return _domain_key_for_family(family)
    if metric_name in BAD_FIGHT_TRADE_MISSION_METRICS or metric_name == "traded_death_rate":
        return "bad_fight_selection"
    if metric_name in SURVIVAL_OPENING_MISSION_METRICS or metric_name == "opening_duel_win_rate":
        return "bad_fight_selection"
    if metric_name in UTILITY_VALUE_MISSION_METRICS or metric_name.startswith(("utility_", "flash_", "he_")):
        return None
    return canonicalize_domain_key(metric_name)


def _domain_key_for_family(family: str) -> str | None:
    return canonical_domain_for_family(family)


def _criteria_values_by_metric(criteria_specs: Sequence[Mapping[str, Any]], field: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in criteria_specs:
        value = item.get(field)
        if value is None:
            continue
        metric_name = str(item["metric_name"])
        if item.get("role") == "primary" or metric_name not in values:
            values[metric_name] = value
    return values


def _criteria_specs_from_hypothesis(hypothesis: CoachHypothesis) -> list[dict[str, Any]]:
    readiness = _json_load_mapping(hypothesis.mission_readiness_json)
    evidence = _json_load_sequence(hypothesis.evidence_json)
    return _criteria_specs_from_parts(
        readiness=readiness,
        evidence=evidence,
        target_metric_candidates=_json_load_sequence(hypothesis.target_metric_candidates_json),
    )


def _criteria_specs_from_insight_card(insight_card: Mapping[str, Any]) -> list[dict[str, Any]]:
    readiness = _mapping(_mission_readiness(insight_card))
    evidence = insight_card.get("evidence") if isinstance(insight_card.get("evidence"), list) else []
    return _criteria_specs_from_parts(
        readiness=readiness,
        evidence=evidence,
        target_metric_candidates=_target_metric_candidates(insight_card),
    )


def _criteria_specs_from_parts(
    *,
    readiness: Mapping[str, Any],
    evidence: Sequence[Any],
    target_metric_candidates: Sequence[Any],
) -> list[dict[str, Any]]:
    explicit = readiness.get("criteria") or readiness.get("mission_criteria")
    if isinstance(explicit, Sequence) and not isinstance(explicit, str):
        return [_normalize_criteria_spec(item) for item in explicit if isinstance(item, Mapping)]
    first_evidence = evidence[0] if evidence and isinstance(evidence[0], Mapping) else {}
    primary_metric = _readiness_target_metric(readiness, target_metric_candidates) or _evidence_metric_name(
        first_evidence
    )
    baseline = _optional_number(readiness.get("baseline_value"))
    if baseline is None and evidence:
        baseline = _optional_number(evidence[0].get("value")) if isinstance(evidence[0], Mapping) else None
    if not primary_metric:
        return []

    direction = _default_metric_direction(primary_metric)
    primary = {
        "metric_name": primary_metric,
        "role": "primary",
        "direction": direction,
        "baseline_value": baseline,
        "target_value": _target_value(primary_metric, baseline, direction),
        "min_sample_rounds": _mission_min_sample_rounds(primary_metric, first_evidence),
        "confidence_required": _confidence_required(readiness),
        "rule": {
            "source": _criteria_rule_source(primary_metric),
            "target_source": "mission_readiness_or_default",
            "blocking_reason_codes": _string_sequence(readiness.get("blocking_reason_codes")),
        },
    }
    specs = [_normalize_criteria_spec(primary)]

    for item in evidence[1:]:
        if not isinstance(item, Mapping):
            continue
        metric_name = _evidence_metric_name(item)
        baseline_value = _optional_number(item.get("value"))
        if not metric_name or metric_name == primary_metric or baseline_value is None:
            continue
        secondary_direction = _default_metric_direction(metric_name)
        specs.append(
            _normalize_criteria_spec(
                {
                    "metric_name": metric_name,
                    "role": "secondary",
                    "direction": secondary_direction,
                    "baseline_value": baseline_value,
                    "target_value": _target_value(metric_name, baseline_value, secondary_direction),
                    "min_sample_rounds": _mission_min_sample_rounds(metric_name, item),
                    "confidence_required": _confidence_required(readiness),
                    "rule": {"source": _criteria_rule_source(metric_name), "evidence_role": "supporting_evidence"},
                }
            )
        )

    if baseline is not None:
        guardrail_direction = "stay_below" if direction == "lower_is_better" else "stay_above"
        specs.append(
            _normalize_criteria_spec(
                {
                    "metric_name": primary_metric,
                    "role": "guardrail",
                    "direction": guardrail_direction,
                    "baseline_value": baseline,
                    "target_value": baseline,
                    "confidence_required": _confidence_required(readiness),
                    "rule": {
                        "source": "baseline_regression_guardrail",
                        "baseline_comparison": "do_not_regress_from_activation_baseline",
                    },
                }
            )
        )
    return specs


def _mission_payload_from_parts(
    *,
    title: str,
    problem: str,
    recommended_focus: str,
    caveats: Sequence[Any],
    readiness: Mapping[str, Any],
    criteria_specs: Sequence[Mapping[str, Any]],
    duration: Mapping[str, Any] | None,
    linked_insight: Mapping[str, Any],
) -> dict[str, Any]:
    primary = _primary_criteria_spec(criteria_specs)
    if primary is None:
        raise ValueError("Mission payload requires primary mission criteria.")
    failure_condition = _failure_condition(criteria_specs)
    payload = MissionPayload(
        title=title.strip(),
        goal=_mission_goal(problem=problem, primary=primary),
        rules=tuple(_mission_rules(recommended_focus, caveats, primary, failure_condition)),
        duration=dict(duration or _mission_duration(primary)),
        success_metric=_success_metric(primary),
        failure_condition=failure_condition,
        linked_insight=dict(linked_insight),
    ).to_dict()
    issues = validate_mission_payload(payload)
    if issues:
        codes = ",".join(issue.code for issue in issues)
        raise ValueError(f"Invalid mission payload: {codes}")
    return payload


def _primary_criteria_spec(criteria_specs: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for criteria_spec in criteria_specs:
        if criteria_spec.get("role") == "primary":
            return dict(criteria_spec)
    return dict(criteria_specs[0]) if criteria_specs else None


def _mission_title(*, problem: str, primary_metric: str) -> str:
    if primary_metric == "untraded_death_rate":
        return "Reduce untraded deaths"
    if primary_metric == "opening_death_rate":
        return "Reduce opening deaths"
    if primary_metric == "survival_rate":
        return "Improve round survival"
    if primary_metric == EFFECTIVE_UTILITY_METRIC:
        return "Recover utility damage toward personal baseline"
    cleaned_problem = problem.strip().rstrip(".")
    if cleaned_problem:
        return cleaned_problem[:120]
    return f"Improve {primary_metric.replace('_', ' ')}"


def _mission_goal(*, problem: str, primary: Mapping[str, Any]) -> str:
    metric_name = str(primary["metric_name"])
    baseline = primary.get("baseline_value")
    target = primary.get("target_value")
    if baseline is not None and target is not None:
        if metric_name == "untraded_death_rate":
            return (
                f"Reduce untraded_death_rate from {float(baseline):.3f} to {float(target):.3f} "
                "over upcoming owner matches using supported trade-status metric snapshots."
            )
        if metric_name == "opening_death_rate":
            return (
                f"Reduce opening_death_rate from {float(baseline):.3f} to {float(target):.3f} "
                "over upcoming owner matches using supported metric snapshots."
            )
        if metric_name == "survival_rate":
            return (
                f"Raise survival_rate from {float(baseline):.3f} to {float(target):.3f} "
                "over upcoming owner matches using supported metric snapshots."
            )
        if metric_name == EFFECTIVE_UTILITY_METRIC:
            return (
                f"Recover recent effective enemy utility damage from {float(baseline):.3f} toward the player's "
                "preceding "
                f"personal baseline of {float(target):.3f} using supported owner metric snapshots."
            )
        return (
            f"Move {metric_name} from {float(baseline):.3f} toward {float(target):.3f} "
            "using only supported owner metric snapshots."
        )
    return f"Improve {metric_name} using only supported owner metric snapshots."


def _mission_rules(
    recommended_focus: str,
    caveats: Sequence[Any],
    primary: Mapping[str, Any],
    failure_condition: Mapping[str, Any],
) -> list[str]:
    metric_name = str(primary["metric_name"])
    if metric_name == "untraded_death_rate":
        rules = [
            "For each upcoming match, avoid taking isolated fights unless a teammate can trade the death.",
            "Success is measured only by lowering untraded_death_rate in owner-scoped metric snapshots.",
            (
                "Failure is triggered if untraded_death_rate is above the activation baseline or cannot be "
                "evaluated with supported trade-status metrics."
            ),
        ]
    elif metric_name == "opening_death_rate":
        rules = [
            "For each upcoming match, avoid voluntary first contact in the opening phase unless trade support is set.",
            "Success is measured only by lowering opening_death_rate in owner-scoped metric snapshots.",
            (
                "Failure is triggered if opening_death_rate is above the activation baseline or cannot be "
                "evaluated with supported metrics."
            ),
        ]
    elif metric_name == "survival_rate":
        rules = [
            "For each upcoming match, prioritize staying alive through early fights before taking isolated space.",
            "Success is measured only by raising survival_rate in owner-scoped metric snapshots.",
            (
                "Failure is triggered if survival_rate drops below the activation baseline or cannot be "
                "evaluated with supported metrics."
            ),
        ]
    elif metric_name == EFFECTIVE_UTILITY_METRIC:
        rules = [
            "Measure recovery only with canonical owner-scoped effective_enemy_utility_damage observations.",
            (
                "Recover toward the preceding personal baseline without treating an absolute utility value "
                "as universally good or bad."
            ),
            "Treat a drop below the recent-segment activation baseline as further deterioration.",
            (
                "Do not infer grenade quality, lineup quality, flash value, or an exact tactical cause "
                "from utility damage."
            ),
        ]
    else:
        rules = []
    if rules and recommended_focus.strip():
        rules.append(f"Focus: {recommended_focus.strip()}")
    if not rules:
        rules = [
            recommended_focus.strip() or f"Work on {metric_name.replace('_', ' ')} in the next matches.",
            f"Count progress only when {primary['metric_name']} is present in owner-scoped metric snapshots.",
            f"Do not count the mission if {failure_condition['metric_name']} triggers the failure condition.",
        ]
    for caveat in _string_sequence(caveats)[:2]:
        rules.append(f"Caveat: {caveat}")
    return rules


def _mission_duration(primary: Mapping[str, Any]) -> dict[str, Any]:
    min_matches = _optional_int(primary.get("min_sample_matches")) or 3
    max_matches = max(min_matches, 5)
    return {
        "unit": "matches",
        "min_matches": min_matches,
        "max_matches": max_matches,
        "min_sample_rounds": primary.get("min_sample_rounds"),
        "description": f"Evaluate after {min_matches}-{max_matches} owner matches with supported metrics.",
    }


def _success_metric(primary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "metric_name": primary["metric_name"],
        "direction": primary["direction"],
        "baseline_value": primary.get("baseline_value"),
        "target_value": primary.get("target_value"),
        "min_sample_matches": primary.get("min_sample_matches"),
        "min_sample_rounds": primary.get("min_sample_rounds"),
        "confidence_required": primary.get("confidence_required"),
    }


def _failure_condition(criteria_specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    guardrail = next((dict(item) for item in criteria_specs if item.get("role") == "guardrail"), None)
    primary = _primary_criteria_spec(criteria_specs)
    source = guardrail or primary
    if source is None:
        raise ValueError("Mission payload requires failure criteria.")
    threshold = source.get("target_value")
    if threshold is None:
        threshold = source.get("baseline_value")
    return {
        "metric_name": source["metric_name"],
        "direction": source["direction"],
        "threshold_value": threshold,
        "reason": _failure_reason(source),
    }


def _validate_payload_non_empty_string(
    payload: Mapping[str, Any],
    field: str,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(payload.get(field), str) or not payload.get(field, "").strip():
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_payload_field",
                f"Mission payload field must be a non-empty string: {field}.",
                f"{path}.{field}",
            )
        )


def _validate_mission_rules(
    rules: Any,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(rules, list):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_rules",
                "Mission rules must be a list.",
                f"{path}.rules",
            )
        )
        return
    if not rules:
        issues.append(
            MissionPayloadValidationIssue(
                "missing_mission_rules",
                "Mission rules must include at least one rule.",
                f"{path}.rules",
            )
        )
    if any(not isinstance(rule, str) or not rule.strip() for rule in rules):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_rule",
                "Mission rules must be non-empty strings.",
                f"{path}.rules",
            )
        )


def _validate_mission_duration(
    duration: Any,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(duration, Mapping):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_duration",
                "Mission duration must be an object.",
                f"{path}.duration",
            )
        )
        return
    if not isinstance(duration.get("unit"), str) or not duration.get("unit", "").strip():
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_duration_unit",
                "Mission duration requires a non-empty unit.",
                f"{path}.duration.unit",
            )
        )
    min_matches = _optional_positive_int(duration.get("min_matches"))
    max_matches = _optional_positive_int(duration.get("max_matches"))
    if min_matches is None and max_matches is None:
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_duration_window",
                "Mission duration requires min_matches or max_matches.",
                f"{path}.duration",
            )
        )
    if min_matches is not None and max_matches is not None and max_matches < min_matches:
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_duration_window",
                "Mission duration max_matches must be greater than or equal to min_matches.",
                f"{path}.duration.max_matches",
            )
        )


def _validate_mission_success_metric(
    success_metric: Any,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(success_metric, Mapping):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_success_metric",
                "Mission success_metric must be an object.",
                f"{path}.success_metric",
            )
        )
        return
    _validate_metric_payload(success_metric, path, "success_metric", issues)
    if _optional_number_or_none(success_metric.get("target_value")) is None:
        issues.append(
            MissionPayloadValidationIssue(
                "missing_mission_success_target",
                "Mission success_metric requires a numeric target_value.",
                f"{path}.success_metric.target_value",
            )
        )


def _validate_mission_failure_condition(
    failure_condition: Any,
    path: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(failure_condition, Mapping):
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_failure_condition",
                "Mission failure_condition must be an object.",
                f"{path}.failure_condition",
            )
        )
        return
    _validate_metric_payload(failure_condition, path, "failure_condition", issues)
    if _optional_number_or_none(failure_condition.get("threshold_value")) is None:
        issues.append(
            MissionPayloadValidationIssue(
                "missing_mission_failure_threshold",
                "Mission failure_condition requires a numeric threshold_value.",
                f"{path}.failure_condition.threshold_value",
            )
        )


def _validate_metric_payload(
    metric_payload: Mapping[str, Any],
    path: str,
    field: str,
    issues: list[MissionPayloadValidationIssue],
) -> None:
    if not isinstance(metric_payload.get("metric_name"), str) or not metric_payload.get("metric_name", "").strip():
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_metric_name",
                "Mission metric payload requires a non-empty metric_name.",
                f"{path}.{field}.metric_name",
            )
        )
    if metric_payload.get("direction") not in CRITERIA_DIRECTIONS:
        issues.append(
            MissionPayloadValidationIssue(
                "invalid_mission_metric_direction",
                "Mission metric direction is unsupported.",
                f"{path}.{field}.direction",
            )
        )


def _add_mission_criteria_from_spec(
    db: Session,
    *,
    user_id: int,
    mission: CoachMission,
    criteria_spec: Mapping[str, Any],
) -> MissionCriteria:
    return add_mission_criteria(
        db,
        user_id=user_id,
        mission_id=mission.id,
        metric_name=str(criteria_spec["metric_name"]),
        role=str(criteria_spec["role"]),
        direction=str(criteria_spec["direction"]),
        baseline_value=_optional_number(criteria_spec.get("baseline_value")),
        target_value=_optional_number(criteria_spec.get("target_value")),
        min_sample_matches=_optional_int(criteria_spec.get("min_sample_matches")),
        min_sample_rounds=_optional_int(criteria_spec.get("min_sample_rounds")),
        confidence_required=_optional_number(criteria_spec.get("confidence_required")),
        rule=_mapping(criteria_spec.get("rule")),
    )


def _normalize_criteria_spec(value: Mapping[str, Any]) -> dict[str, Any]:
    metric_name = str(value.get("metric_name") or value.get("metric_id") or "").strip()
    role = str(value.get("role") or "primary").strip()
    direction = str(value.get("direction") or _default_metric_direction(metric_name)).strip()
    if not metric_name:
        raise ValueError("Mission criteria requires metric_name")
    if role not in CRITERIA_ROLES:
        raise ValueError(f"Unsupported mission criteria role: {role}")
    if direction not in CRITERIA_DIRECTIONS:
        raise ValueError(f"Unsupported mission criteria direction: {direction}")
    return {
        "metric_name": metric_name,
        "role": role,
        "direction": direction,
        "baseline_value": _optional_number(value.get("baseline_value")),
        "target_value": _optional_number(value.get("target_value")),
        "min_sample_matches": _optional_int(value.get("min_sample_matches")),
        "min_sample_rounds": _optional_int(value.get("min_sample_rounds")),
        "confidence_required": _optional_number(value.get("confidence_required")),
        "rule": _mapping(value.get("rule")),
    }


def _readiness_target_metric(readiness: Mapping[str, Any], target_metric_candidates: Sequence[Any]) -> str | None:
    target = readiness.get("target_metric_candidate")
    if target:
        return str(target)
    candidates = readiness.get("target_metric_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, str):
        candidates = target_metric_candidates
    for item in candidates:
        if item:
            return str(item)
    return None


def _evidence_metric_name(evidence: Mapping[str, Any]) -> str | None:
    metric_name = evidence.get("metric_name") or evidence.get("metric_id")
    return str(metric_name) if metric_name else None


def _default_metric_direction(metric_name: str) -> str:
    lower_is_better = {
        "opening_death_rate",
        "untraded_death_rate",
        "death_rate",
        "deaths",
        "ambiguous_traded_deaths",
    }
    if metric_name in lower_is_better:
        return "lower_is_better"
    return "higher_is_better"


def _target_value(metric_name: str, baseline: float | None, direction: str) -> float | None:
    if baseline is None:
        return None
    if direction == "lower_is_better":
        if metric_name.endswith("_rate"):
            return round(max(0.0, baseline - 0.05), 3)
        return round(max(0.0, baseline * 0.9), 3)
    if direction == "higher_is_better":
        if metric_name.endswith("_rate"):
            return round(min(1.0, baseline + 0.05), 3)
        return round(baseline * 1.1, 3)
    return baseline


def _mission_min_sample_rounds(metric_name: str, evidence: Mapping[str, Any]) -> int | None:
    if metric_name in BAD_FIGHT_TRADE_MISSION_METRICS:
        rounds = _optional_int(evidence.get("rounds_played"))
        if rounds is not None and rounds > 0:
            return rounds
        return None
    if metric_name not in SURVIVAL_OPENING_MISSION_METRICS:
        return None
    sample_count = _optional_int(evidence.get("sample_count"))
    if sample_count is None or sample_count <= 0:
        return None
    return sample_count


def _criteria_rule_source(metric_name: str) -> str:
    if metric_name in BAD_FIGHT_TRADE_MISSION_METRICS:
        return "bad_fight_trade_mission_template"
    if metric_name in SURVIVAL_OPENING_MISSION_METRICS:
        return "survival_opening_mission_template"
    return "mission_readiness"


def _failure_reason(source: Mapping[str, Any]) -> str:
    metric_name = str(source.get("metric_name") or "")
    if metric_name == "untraded_death_rate":
        return (
            "Mission fails if untraded_death_rate rises above the activation baseline or cannot be evaluated "
            "with supported trade-status metrics."
        )
    if metric_name == "opening_death_rate":
        return (
            "Mission fails if opening_death_rate rises above the activation baseline or cannot be evaluated "
            "with supported metrics."
        )
    if metric_name == "survival_rate":
        return (
            "Mission fails if survival_rate drops below the activation baseline or cannot be evaluated "
            "with supported metrics."
        )
    if metric_name == EFFECTIVE_UTILITY_METRIC:
        return (
            "Mission guardrail triggers if effective_enemy_utility_damage drops below the recent "
            "personal-segment baseline."
        )
    return "Mission fails if this condition regresses or cannot be evaluated with supported metrics."


def _confidence_required(readiness: Mapping[str, Any]) -> float:
    confidence_eligibility = readiness.get("confidence_eligibility")
    level = (
        _optional_lower_str(confidence_eligibility.get("level"))
        if isinstance(confidence_eligibility, Mapping)
        else None
    )
    if level == "high":
        return INSIGHT_CONFIDENCE_SCORES["high"]
    return INSIGHT_CONFIDENCE_SCORES["medium"]


def _mission_readiness(insight_card: Mapping[str, Any]) -> Any:
    return insight_card.get("mission_readiness") or insight_card.get("mission_readiness_metadata") or {}


def _target_metric_candidates(insight_card: Mapping[str, Any]) -> Any:
    if "target_metric_candidates" in insight_card:
        return insight_card["target_metric_candidates"]
    mission_readiness = _mission_readiness(insight_card)
    if isinstance(mission_readiness, Mapping):
        if "target_metric_candidates" in mission_readiness:
            return mission_readiness["target_metric_candidates"]
        if "target_metrics" in mission_readiness:
            return mission_readiness["target_metrics"]
    if "target_metrics" in insight_card:
        return insight_card["target_metrics"]
    return []


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in INSIGHT_CONFIDENCE_SCORES:
            return INSIGHT_CONFIDENCE_SCORES[normalized]
    return float(value)


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_number_or_none(value: Any) -> float | None:
    try:
        return _optional_number(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_positive_int(value: Any) -> int | None:
    try:
        parsed = _optional_int(value)
    except (TypeError, ValueError):
        return None
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    output: list[int] = []
    for item in value:
        try:
            output.append(int(item))
        except (TypeError, ValueError):
            continue
    return output


def _optional_lower_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_object(value: Mapping[str, Any]) -> str:
    return _json_any(dict(value))


def _json_list(value: Sequence[Any]) -> str:
    return _json_any(list(value))


def _json_any(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _json_load_mapping(value: str) -> dict[str, Any]:
    loaded = json.loads(value)
    return dict(loaded) if isinstance(loaded, Mapping) else {}


def _json_load_sequence(value: str) -> list[Any]:
    loaded = json.loads(value)
    return list(loaded) if isinstance(loaded, list) else []


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_sequence(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [str(item) for item in value]
