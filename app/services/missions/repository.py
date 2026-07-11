"""Owner-scoped mission persistence and query helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AnalysisRun,
    CoachHypothesis,
    CoachMission,
    MissionCriteria,
    MissionProgressEvaluation,
)
from app.services.missions.payloads import (
    _json_any,
    _json_list,
    _json_load_mapping,
    _json_object,
    _mapping,
    _mission_readiness,
    _optional_float,
    _optional_str,
    _target_metric_candidates,
    mission_domain_key,
)
from app.services.missions.types import (
    CRITERIA_DIRECTIONS,
    CRITERIA_ROLES,
    MISSION_PROGRESS_STATUSES,
)


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

__all__ = (
    'add_mission_criteria',
    'create_analysis_run',
    'create_coach_hypothesis',
    'get_analysis_run',
    'get_coach_hypothesis',
    'get_coach_mission',
    'list_active_coach_missions',
    'list_analysis_runs',
    'list_coach_hypotheses',
    'list_coach_missions',
    'list_mission_criteria',
    'list_mission_progress_evaluations',
    'record_mission_progress_evaluation',
)
