"""Owner-scoped composition for the two-domain coach web experience."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.services.coach.domain_analysis import coach_domain_slots_payload
from app.services.coach_domain_model import CANONICAL_COACH_DOMAINS
from app.services.shared.i18n import normalize_locale, translate

SCHEMA_VERSION = "coach-two-card-ui-v1"

logger = logging.getLogger(__name__)

_DOMAIN_KEYS = {
    "impact_leak": ("coach.domain.impact_leak", "coach.domain.impact_leak.focus"),
    "bad_fight_selection": (
        "coach.domain.bad_fight_selection",
        "coach.domain.bad_fight_selection.focus",
    ),
}

_STATE_KEYS = {
    "insufficient_baseline": ("coach.state.insufficient_baseline", "coach.state.insufficient_baseline.help"),
    "not_enough_data": ("coach.state.not_enough_data", "coach.state.not_enough_data.help"),
    "analyzing": ("coach.state.analyzing", "coach.state.analyzing.help"),
    "proposal_ready": ("coach.state.proposal_ready", "coach.state.proposal_ready.help"),
    "active": ("coach.state.active", "coach.state.active.help"),
    "insufficient_data": ("coach.state.insufficient_data", "coach.state.insufficient_data.help"),
    "no_material_problem": ("coach.state.no_material_problem", "coach.state.no_material_problem.help"),
    "analysis_failed": ("coach.state.analysis_failed", "coach.state.analysis_failed.help"),
    "stale_or_superseded": ("coach.state.stale", "coach.state.stale.help"),
    "paused": ("coach.state.paused", "coach.state.paused.help"),
    "completed": ("coach.state.completed", "coach.state.completed.help"),
    "unavailable": ("coach.state.unavailable", "coach.state.unavailable.help"),
}

_PROGRESS_KEYS = {
    "no_evaluation_yet": "coach.progress.no_evaluation_yet",
    "insufficient_data": "coach.progress.insufficient_data",
    "improving": "coach.progress.improving",
    "unchanged": "coach.progress.unchanged",
    "regressing": "coach.progress.regressing",
    "not_following": "coach.progress.not_following",
    "unavailable": "coach.progress.unavailable",
}

_REASON_KEYS = {
    "no_evaluation_yet": "coach.reason.no_evaluation_yet",
    "insufficient_sample_matches": "coach.reason.insufficient_sample_matches",
    "insufficient_sample_rounds": "coach.reason.insufficient_sample_rounds",
    "unavailable_round_sample": "coach.reason.unavailable_round_sample",
    "missing_metric": "coach.reason.missing_metric",
    "missing_baseline_metric": "coach.reason.missing_baseline_metric",
    "insufficient_confidence": "coach.reason.insufficient_confidence",
    "low_sample_caveat": "coach.reason.low_sample",
}


def compose_coach_workspace(
    db: Session,
    *,
    owner_user_id: int,
    locale: str | None = None,
) -> dict[str, Any]:
    """Build the side-effect-free owner UI model from the canonical serializer."""
    normalized_locale = normalize_locale(locale)
    try:
        payload = coach_domain_slots_payload(db, owner_user_id=owner_user_id)
    except Exception:
        logger.exception("coach_ui_payload_unavailable owner_user_id=%s", owner_user_id)
        cards = [_unavailable_card(domain, normalized_locale) for domain in CANONICAL_COACH_DOMAINS]
        return _workspace(cards, normalized_locale, backend_schema_version=None)
    return compose_coach_workspace_from_payload(payload, locale=normalized_locale)


def compose_coach_workspace_from_payload(
    payload: Mapping[str, Any],
    *,
    locale: str | None = None,
) -> dict[str, Any]:
    """Pure normalization boundary used by routes and deterministic state tests."""
    normalized_locale = normalize_locale(locale)
    source_cards = {
        str(_mapping(card.get("domain")).get("key")): card
        for card in _sequence(payload.get("cards"))
        if isinstance(card, Mapping)
    }
    cards = [
        _compose_card(domain, _mapping(source_cards.get(domain)), normalized_locale)
        if domain in source_cards
        else _unavailable_card(domain, normalized_locale)
        for domain in CANONICAL_COACH_DOMAINS
    ]
    return _workspace(
        cards,
        normalized_locale,
        backend_schema_version=str(payload.get("schema_version") or "") or None,
    )


def compose_match_feedback(
    workspace: Mapping[str, Any],
    *,
    match_id: int,
) -> dict[str, Any]:
    """Return one safe feedback row for each canonical domain for an owned match."""
    locale = normalize_locale(str(workspace.get("locale") or ""))
    rows = [_match_feedback_row(card, match_id=match_id, locale=locale) for card in workspace.get("cards", [])]
    return {
        "schema_version": SCHEMA_VERSION,
        "match_id": match_id,
        "cards": rows,
        "card_count": len(rows),
    }


def dashboard_coach_summary(workspace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "cards": [
            {
                "domain_key": card["domain_key"],
                "domain_label": card["domain_label"],
                "state": card["presentation_state"],
                "state_label": card["state_label"],
                "progress_status": card["progress"]["status"],
                "progress_label": card["progress"]["status_label"],
            }
            for card in workspace.get("cards", [])
        ],
    }


def _workspace(cards: list[dict[str, Any]], locale: str, *, backend_schema_version: str | None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "backend_schema_version": backend_schema_version,
        "locale": locale,
        "cards": cards,
        "card_count": len(cards),
        "domain_order": list(CANONICAL_COACH_DOMAINS),
        "technical": {"backend_schema_version": backend_schema_version},
    }


def _compose_card(domain: str, raw: Mapping[str, Any], locale: str) -> dict[str, Any]:
    analysis = _mapping(raw.get("analysis_summary") or raw.get("hypothesis_summary"))
    proposal = _mapping(raw.get("proposal") or raw.get("proposal_summary"))
    proposal_ref = _mapping(raw.get("proposal_ref"))
    mission = _mapping(raw.get("mission_lifecycle") or raw.get("current_mission"))
    evidence = _mapping(raw.get("evidence"))
    baseline = _mapping(raw.get("baseline_summary"))
    history = [_progress_item(item, proposal, locale) for item in _sequence(raw.get("progress_history"))]
    latest = history[0] if history else _empty_progress(proposal, locale)
    backend_state = str(raw.get("state") or raw.get("slot_status") or "unavailable")
    presentation_state = _presentation_state(
        backend_state,
        analysis_status=str(analysis.get("status") or raw.get("ai_analysis_status") or ""),
        proposal_ref=proposal_ref,
        mission=mission,
        latest_progress=latest,
    )
    state_key, state_help_key = _STATE_KEYS.get(presentation_state, _STATE_KEYS["unavailable"])
    activation_allowed = bool(
        raw.get("activation_eligibility")
        and presentation_state == "proposal_ready"
        and proposal_ref.get("id")
        and proposal_ref.get("is_current") is True
    )
    evidence_refs = set(str(value) for value in _sequence(analysis.get("evidence_refs")))
    counter_refs = set(str(value) for value in _sequence(analysis.get("counterevidence_refs")))
    metric_refs = [dict(item) for item in _sequence(evidence.get("metric_refs")) if isinstance(item, Mapping)]
    domain_label_key, focus_label_key = _DOMAIN_KEYS[domain]
    source_payload = _mapping(mission.get("source_payload"))
    activation_baseline = _mapping(source_payload.get("activation_baseline"))
    return {
        "domain_key": domain,
        "domain_label": translate(locale, domain_label_key),
        "focus_label": translate(locale, focus_label_key),
        "backend_state": backend_state,
        "presentation_state": presentation_state,
        "state_label": translate(locale, state_key),
        "state_explanation": translate(locale, state_help_key),
        "analysis": {
            "headline": analysis.get("headline"),
            "hypothesis": analysis.get("hypothesis"),
            "reasoning_summary": analysis.get("reasoning_summary"),
            "primary_pattern": analysis.get("primary_pattern"),
            "recommended_focus": analysis.get("recommended_focus") or proposal.get("behavioral_focus"),
            "confidence_rationale": analysis.get("confidence_rationale"),
        },
        "confidence": {
            "level": raw.get("confidence"),
            "label": _confidence_label(raw.get("confidence"), locale),
            "rationale": analysis.get("confidence_rationale"),
        },
        "evidence": [item for item in metric_refs if not evidence_refs or item.get("evidence_ref") in evidence_refs],
        "counterevidence": [item for item in metric_refs if item.get("evidence_ref") in counter_refs],
        "sample_matches": list(evidence.get("match_refs") or []),
        "caveats": list(raw.get("caveats") or []),
        "provenance_warning": translate(locale, "coach.provenance_warning"),
        "baseline": {
            "matches_count": baseline.get("matches_count"),
            "analysis_cutoff": baseline.get("analysis_cutoff"),
        },
        "proposal": proposal,
        "metrics": {
            "name": proposal.get("primary_metric") or latest.get("metric_name"),
            "baseline": latest.get("baseline_value")
            if latest.get("baseline_value") is not None
            else proposal.get("baseline_value"),
            "current": latest.get("current_value"),
            "target": latest.get("target_value")
            if latest.get("target_value") is not None
            else proposal.get("target_value"),
            "target_delta": proposal.get("target_delta"),
            "direction": proposal.get("target_direction"),
        },
        "mission": {
            "active": mission.get("status") == "active",
            "status": mission.get("status"),
            "title": mission.get("title") or proposal.get("title"),
            "focus": mission.get("focus") or proposal.get("behavioral_focus"),
            "activated_at": mission.get("activated_at"),
            "activation_baseline_match_ids": list(activation_baseline.get("match_ids") or []),
        },
        "activation": {
            "allowed": activation_allowed,
            "proposal_id": proposal_ref.get("id") if activation_allowed else None,
            "reason": None if activation_allowed else translate(locale, _activation_reason_key(presentation_state)),
        },
        "progress": {
            **latest,
            "minimum_matches": proposal.get("minimum_future_matches"),
            "maximum_matches": proposal.get("maximum_future_matches"),
            "history": history,
        },
        "technical": {
            "proposal_id": proposal_ref.get("id"),
            "proposal_is_current": proposal_ref.get("is_current"),
            "mission_id": mission.get("mission_id"),
            "analysis_id": _mapping(raw.get("technical_provenance")).get("analysis_id"),
            "baseline_hash": evidence.get("baseline_hash"),
            "evidence_schema_version": evidence.get("evidence_schema_version"),
            "reason_codes": latest.get("reason_codes", []),
        },
    }


def _presentation_state(
    backend_state: str,
    *,
    analysis_status: str,
    proposal_ref: Mapping[str, Any],
    mission: Mapping[str, Any],
    latest_progress: Mapping[str, Any],
) -> str:
    if mission.get("status") == "active":
        return "active"
    if backend_state == "proposal_superseded" or (proposal_ref and proposal_ref.get("is_current") is not True):
        return "stale_or_superseded"
    if analysis_status == "insufficient_evidence":
        return "not_enough_data"
    if backend_state == "active" and latest_progress.get("status") == "insufficient_data":
        return "insufficient_data"
    if backend_state in _STATE_KEYS:
        return backend_state
    return "unavailable"


def _progress_item(value: Any, proposal: Mapping[str, Any], locale: str) -> dict[str, Any]:
    item = _mapping(value)
    primary = _mapping(item.get("primary_metric_result"))
    window = _mapping(item.get("evaluated_window"))
    status = str(item.get("status") or "unavailable")
    reason_codes = list(primary.get("reason_codes") or [])
    return {
        "evaluation_id": item.get("evaluation_id"),
        "status": status,
        "status_label": translate(locale, _PROGRESS_KEYS.get(status, "coach.progress.unavailable")),
        "metric_name": primary.get("metric_name") or proposal.get("primary_metric"),
        "baseline_value": primary.get("baseline_value")
        if primary.get("baseline_value") is not None
        else proposal.get("baseline_value"),
        "current_value": primary.get("evaluation_value"),
        "target_value": primary.get("target_value")
        if primary.get("target_value") is not None
        else proposal.get("target_value"),
        "sample_matches": primary.get("sample_matches")
        if primary.get("sample_matches") is not None
        else window.get("sample_matches", 0),
        "sample_rounds": primary.get("sample_rounds"),
        "match_ids": list(window.get("match_ids") or primary.get("match_ids") or []),
        "confidence": item.get("confidence"),
        "caveats": list(item.get("caveats") or []),
        "counted_target": item.get("counted") is True,
        "reason_codes": reason_codes,
        "reason_labels": _reason_labels(reason_codes, locale),
        "explanation": item.get("progress_explanation"),
    }


def _empty_progress(proposal: Mapping[str, Any], locale: str) -> dict[str, Any]:
    return {
        "evaluation_id": None,
        "status": "no_evaluation_yet",
        "status_label": translate(locale, _PROGRESS_KEYS["no_evaluation_yet"]),
        "metric_name": proposal.get("primary_metric"),
        "baseline_value": proposal.get("baseline_value"),
        "current_value": None,
        "target_value": proposal.get("target_value"),
        "sample_matches": 0,
        "sample_rounds": None,
        "match_ids": [],
        "confidence": None,
        "caveats": [],
        "counted_target": False,
        "reason_codes": ["no_evaluation_yet"],
        "reason_labels": [translate(locale, _REASON_KEYS["no_evaluation_yet"])],
        "explanation": translate(locale, "coach.progress.no_evaluation_yet.help"),
    }


def _match_feedback_row(card: Mapping[str, Any], *, match_id: int, locale: str) -> dict[str, Any]:
    progress = _mapping(card.get("progress"))
    mission = _mapping(card.get("mission"))
    history = [_mapping(item) for item in _sequence(progress.get("history"))]
    evaluation = next((item for item in history if match_id in item.get("match_ids", [])), None)
    if card.get("presentation_state") == "unavailable":
        status = "unavailable"
        explanation = translate(locale, "coach.match.unavailable")
        included = False
    elif not mission.get("active"):
        status = "not_active"
        explanation = translate(locale, "coach.match.not_active")
        included = False
    elif match_id in mission.get("activation_baseline_match_ids", []):
        status = "pre_activation"
        explanation = translate(locale, "coach.match.pre_activation")
        included = False
    elif evaluation is None:
        status = "no_evaluation"
        explanation = translate(locale, "coach.match.no_evaluation")
        included = False
    else:
        status = str(evaluation.get("status") or "unavailable")
        explanation = evaluation.get("explanation") or translate(locale, "coach.match.evaluated")
        included = True
    selected = evaluation or progress
    return {
        "domain_key": card.get("domain_key"),
        "domain_label": card.get("domain_label"),
        "status": status,
        "status_label": _match_status_label(status, locale),
        "explanation": explanation,
        "included_in_progress_window": included,
        "target_result_counted": bool(evaluation and evaluation.get("counted_target")),
        "metric_name": _mapping(card.get("metrics")).get("name"),
        "match_value": selected.get("current_value") if evaluation else None,
        "baseline_value": _mapping(card.get("metrics")).get("baseline"),
        "target_value": _mapping(card.get("metrics")).get("target"),
        "sample_matches": selected.get("sample_matches") if evaluation else 0,
        "minimum_matches": progress.get("minimum_matches"),
        "confidence": selected.get("confidence"),
        "caveats": list(selected.get("caveats") or card.get("caveats") or []),
        "reason_labels": list(selected.get("reason_labels") or []),
        "technical_reason_codes": list(selected.get("reason_codes") or []),
        "coach_href": f"/coach#{card.get('domain_key')}",
    }


def _unavailable_card(domain: str, locale: str) -> dict[str, Any]:
    return _compose_card(
        domain,
        {"state": "unavailable", "slot_status": "unavailable", "caveats": []},
        locale,
    )


def _reason_labels(reason_codes: Sequence[Any], locale: str) -> list[str]:
    labels = []
    for reason in reason_codes:
        key = _REASON_KEYS.get(str(reason), "coach.reason.other")
        label = translate(locale, key)
        if label not in labels:
            labels.append(label)
    return labels


def _confidence_label(value: Any, locale: str) -> str:
    key = str(value or "unavailable").lower()
    if key not in {"low", "medium", "high"}:
        key = "unavailable"
    return translate(locale, f"coach.confidence.{key}")


def _activation_reason_key(state: str) -> str:
    return {
        "active": "coach.activation.already_active",
        "analyzing": "coach.activation.analyzing",
        "insufficient_baseline": "coach.activation.insufficient_baseline",
        "not_enough_data": "coach.activation.not_enough_data",
        "no_material_problem": "coach.activation.no_problem",
        "analysis_failed": "coach.activation.failed",
        "stale_or_superseded": "coach.activation.stale",
    }.get(state, "coach.activation.unavailable")


def _match_status_label(status: str, locale: str) -> str:
    key = (
        status
        if status
        in {
            "pre_activation",
            "no_evaluation",
            "not_active",
            "insufficient_data",
            "improving",
            "unchanged",
            "regressing",
            "not_following",
            "unavailable",
        }
        else "unavailable"
    )
    return translate(locale, f"coach.match.status.{key}")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else []


__all__ = (
    "SCHEMA_VERSION",
    "compose_coach_workspace",
    "compose_coach_workspace_from_payload",
    "compose_match_feedback",
    "dashboard_coach_summary",
)
