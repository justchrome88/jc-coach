"""Mission activation constraints and lifecycle transitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    CoachHypothesis,
    CoachMission,
    MissionCriteria,
)
from app.services.coach_domain_model import (
    canonical_domain_for_family,
    canonicalize_domain_key,
    require_canonical_domain,
)
from app.services.missions.payloads import (
    _criteria_specs_from_hypothesis,
    _domain_key_for_metric,
    _json_load_mapping,
    _json_object,
    _mapping,
    _mission_domain_key_from_parts,
    _mission_source_payload,
    _optional_int,
    _optional_lower_str,
    _optional_number,
    _optional_positive_int,
    _optional_str,
    _primary_criteria_spec,
    _string_sequence,
    mission_domain_key,
    mission_payload_from_hypothesis,
)
from app.services.missions.repository import (
    _require_mission_hypothesis,
    _require_owned_hypothesis,
    _require_owned_mission,
    add_mission_criteria,
    list_active_coach_missions,
    list_mission_criteria,
)
from app.services.missions.types import (
    MISSION_DUPLICATE_POLICIES,
    MISSION_ELIGIBLE_CONFIDENCE_LEVELS,
    MISSION_STATUSES,
    MISSION_TRANSITIONS,
    TERMINAL_MISSION_STATUSES,
)


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

__all__ = (
    'activate_coach_mission',
    'activate_draft_coach_mission',
    'cancel_coach_mission',
    'complete_coach_mission',
    'create_draft_coach_mission',
    'expire_coach_mission',
    'fail_coach_mission',
    'pause_coach_mission',
    'reconcile_noncanonical_active_missions',
    'resume_coach_mission',
    'update_coach_mission_status',
)
