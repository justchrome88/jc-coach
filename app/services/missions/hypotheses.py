"""Rolling evidence windows and mission candidate generation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AnalysisRun,
    CoachHypothesis,
    Match,
    MetricSnapshot,
)
from app.services.coach_domain_model import (
    CANONICAL_COACH_DOMAINS,
    canonical_domain_for_family,
)
from app.services.missions.payloads import (
    _domain_key_for_metric,
    _int_list,
    _json_load_mapping,
    _json_load_sequence,
    _mapping,
    _optional_int,
    _optional_lower_str,
    _optional_number,
    _optional_positive_int,
    _optional_str,
    mission_payload_from_insight_card,
)
from app.services.missions.presentation import (
    active_mission_context_for_owner,
    mission_suppression_decision_for_payload,
    mission_suppression_key_from_payload,
)
from app.services.missions.progress import (
    _format_metric_value,
    _metric_numeric_value,
    _metric_sample_rounds,
    _ordered_ints,
    _resolve_metric_observation,
    _sample_count,
    _snapshot_caveats,
    _snapshot_payload_mapping,
    _snapshot_to_mapping,
)
from app.services.missions.repository import (
    create_analysis_run,
    create_coach_hypothesis,
    list_coach_hypotheses,
)
from app.services.missions.types import (
    EFFECTIVE_UTILITY_METRIC,
    INSIGHT_CONFIDENCE_SCORES,
    MAX_UTILITY_TREND_SUPPORTED_MATCHES,
    MIN_ROLLING_WINDOW_MATCHES,
    MIN_ROLLING_WINDOW_ROUNDS,
    MIN_UTILITY_TREND_SEGMENT_MATCHES,
    MIN_UTILITY_TREND_SUPPORTED_MATCHES,
    MISSION_ELIGIBLE_CONFIDENCE_LEVELS,
    ROLLING_MISSION_METRICS,
    ROLLING_MISSION_WINDOW_TYPES,
    UTILITY_NEGATIVE_TREND_MATERIALITY,
    UTILITY_SNAPSHOT_SOURCE,
    RollingMissionCandidate,
    RollingMissionWindow,
    UtilityTrendEvidence,
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

__all__ = (
    'build_rolling_mission_window',
    'generate_rolling_mission_candidates',
    'persist_rolling_mission_candidates',
)
