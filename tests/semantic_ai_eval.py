from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from app.services.ai_validator import validate_ai_coach_output
from app.services.shared.metric_policy import metric_definition, usage_decision

SemanticConfidence = Literal["low", "medium", "high"]

_CONFIDENCE_RANK = {"unavailable": 0, "low_confidence": 1, "low": 1, "medium": 2, "high": 3}
_HARD_CLAIM_PATTERN = re.compile(
    r"\b(proves?|guarantees?|must|always|definitely|certainly|main issue|primary problem|hard recommendation)\b",
    re.IGNORECASE,
)
_NO_DATA_WARNING_PATTERN = re.compile(r"\b(no data|not enough|insufficient|data gap|нет данных|мало данных)\b", re.I)


@dataclass(frozen=True)
class SemanticEvalIssue:
    code: str
    path: str
    message: str


def evaluate_semantic_ai_output(
    output: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> tuple[SemanticEvalIssue, ...]:
    """Deterministic local semantic checks for AI coach output fixtures."""

    issues: list[SemanticEvalIssue] = []
    validation = validate_ai_coach_output(output)
    for issue in validation.issues:
        issues.append(SemanticEvalIssue(f"schema_{issue.code}", issue.path, issue.message))
    if not isinstance(output, dict):
        return tuple(issues)

    available_metrics = _available_metric_ids(evidence_payload)
    metric_confidence = _metric_confidence(evidence_payload)
    no_data = bool(evidence_payload.get("no_data")) or not available_metrics

    if no_data:
        _check_no_data_fallback(output, issues)

    for section, metric_field in (("diagnoses", "evidence_metric_ids"), ("recommendations", "target_metric_ids")):
        for index, item in enumerate(output.get(section) or []):
            if not isinstance(item, dict):
                continue
            path = f"$.{section}[{index}]"
            metric_ids = item.get(metric_field) if isinstance(item.get(metric_field), list) else []
            _check_supplied_metrics(metric_ids, available_metrics, path, issues)
            _check_claim_strength(item, metric_ids, metric_confidence, section, path, issues)

    _check_evidence_links(output, evidence_payload, metric_confidence, issues)
    return tuple(issues)


def issue_codes(issues: tuple[SemanticEvalIssue, ...]) -> set[str]:
    return {issue.code for issue in issues}


def _available_metric_ids(evidence_payload: dict[str, Any]) -> set[str]:
    explicit = set(evidence_payload.get("available_metric_ids") or [])
    confidence_metrics = set((evidence_payload.get("metric_confidence") or {}).keys())
    link_metrics = {link.get("metric_id") for link in evidence_payload.get("required_evidence_links") or []}
    return {str(metric_id) for metric_id in explicit | confidence_metrics | link_metrics if metric_id}


def _metric_confidence(evidence_payload: dict[str, Any]) -> dict[str, str]:
    confidence: dict[str, str] = {}
    for metric_id, value in (evidence_payload.get("metric_confidence") or {}).items():
        if isinstance(value, dict):
            confidence[metric_id] = str(value.get("level") or value.get("confidence") or "unavailable")
        else:
            confidence[metric_id] = str(value)
    return confidence


def _check_no_data_fallback(output: dict[str, Any], issues: list[SemanticEvalIssue]) -> None:
    if output.get("confidence") != "low":
        issues.append(
            SemanticEvalIssue(
                "no_data_confidence_not_low",
                "$.confidence",
                "No-data AI output must keep top-level confidence low.",
            )
        )
    if output.get("diagnoses") or output.get("recommendations"):
        issues.append(
            SemanticEvalIssue(
                "no_data_hard_advice",
                "$",
                "No-data AI output must not produce diagnoses or hard recommendations.",
            )
        )
    warnings = " ".join(str(warning) for warning in output.get("warnings") or [])
    if not _NO_DATA_WARNING_PATTERN.search(warnings):
        issues.append(
            SemanticEvalIssue(
                "no_data_gap_warning_missing",
                "$.warnings",
                "No-data AI output must visibly state the data gap.",
            )
        )


def _check_supplied_metrics(
    metric_ids: list[Any],
    available_metrics: set[str],
    path: str,
    issues: list[SemanticEvalIssue],
) -> None:
    for metric_id in metric_ids:
        if isinstance(metric_id, str) and metric_id not in available_metrics:
            issues.append(
                SemanticEvalIssue(
                    "metric_not_in_supplied_evidence",
                    path,
                    f"{metric_id} is registered but absent from the supplied evidence payload.",
                )
            )


def _check_claim_strength(
    item: dict[str, Any],
    metric_ids: list[Any],
    metric_confidence: dict[str, str],
    section: str,
    path: str,
    issues: list[SemanticEvalIssue],
) -> None:
    item_confidence = str(item.get("confidence") or "")
    weakest = min((_confidence_rank(metric_confidence.get(str(metric_id))) for metric_id in metric_ids), default=0)
    if item_confidence == "high" and weakest < _CONFIDENCE_RANK["high"]:
        issues.append(
            SemanticEvalIssue(
                "advice_confidence_overstated",
                f"{path}.confidence",
                "Advice confidence may not exceed the weakest supplied metric confidence.",
            )
        )

    caveats = item.get("caveats") if isinstance(item.get("caveats"), list) else []
    has_caveat = any(str(caveat).strip() for caveat in caveats)
    for metric_id in metric_ids:
        if not isinstance(metric_id, str):
            continue
        if _requires_caveat(metric_id, section, metric_confidence.get(metric_id)) and not has_caveat:
            issues.append(
                SemanticEvalIssue(
                    "missing_weak_metric_caveat",
                    f"{path}.caveats",
                    f"{metric_id} requires visible caveats for semantic coach advice.",
                )
            )

    claim_text = " ".join(
        str(item.get(key) or "")
        for key in ("claim", "action", "rationale", "summary")
    )
    if _HARD_CLAIM_PATTERN.search(claim_text) and weakest < _CONFIDENCE_RANK["high"]:
        issues.append(
            SemanticEvalIssue(
                "unsupported_hard_claim",
                path,
                "Hard claim wording is not supported by the supplied evidence confidence.",
            )
        )


def _check_evidence_links(
    output: dict[str, Any],
    evidence_payload: dict[str, Any],
    metric_confidence: dict[str, str],
    issues: list[SemanticEvalIssue],
) -> None:
    evidence_items = [item for item in output.get("evidence") or [] if isinstance(item, dict)]
    evidence_by_metric = {str(item.get("metric_id")): item for item in evidence_items if item.get("metric_id")}
    required_links = {
        str(link.get("metric_id")): link for link in evidence_payload.get("required_evidence_links") or []
    }
    claimed_metric_ids = _claimed_metric_ids(output)
    for metric_id in claimed_metric_ids:
        evidence = evidence_by_metric.get(metric_id)
        if evidence is None:
            issues.append(
                SemanticEvalIssue(
                    "missing_evidence_link",
                    "$.evidence",
                    f"{metric_id} is claimed but has no evidence item.",
                )
            )
            continue
        reported_confidence = evidence.get("metric_confidence")
        if not reported_confidence:
            issues.append(
                SemanticEvalIssue(
                    "missing_metric_confidence",
                    f"$.evidence[{metric_id}]",
                    f"{metric_id} evidence is missing metric_confidence.",
                )
            )
        elif _confidence_rank(str(reported_confidence)) > _confidence_rank(metric_confidence.get(metric_id)):
            issues.append(
                SemanticEvalIssue(
                    "metric_confidence_overstated",
                    f"$.evidence[{metric_id}].metric_confidence",
                    f"{metric_id} evidence overstates supplied metric confidence.",
                )
            )

        required = required_links.get(metric_id)
        if required and not _evidence_link_present(evidence):
            issues.append(
                SemanticEvalIssue(
                    "missing_evidence_link",
                    f"$.evidence[{metric_id}]",
                    f"{metric_id} evidence must preserve problem -> metric -> match -> recommendation.",
                )
            )


def _claimed_metric_ids(output: dict[str, Any]) -> set[str]:
    claimed: set[str] = set()
    for diagnosis in output.get("diagnoses") or []:
        if isinstance(diagnosis, dict):
            claimed.update(str(metric_id) for metric_id in diagnosis.get("evidence_metric_ids") or [])
    for recommendation in output.get("recommendations") or []:
        if isinstance(recommendation, dict):
            claimed.update(str(metric_id) for metric_id in recommendation.get("target_metric_ids") or [])
    return claimed


def _evidence_link_present(evidence: dict[str, Any]) -> bool:
    has_problem = bool(evidence.get("problem") or evidence.get("problem_id"))
    has_match = bool(evidence.get("match_ids") or evidence.get("sample_count") or evidence.get("window"))
    has_recommendation = bool(evidence.get("recommendation_id") or evidence.get("recommendation"))
    return has_problem and has_match and has_recommendation


def _requires_caveat(metric_id: str, section: str, confidence: str | None) -> bool:
    usage = "diagnosis" if section == "diagnoses" else "recommendation"
    definition = metric_definition(metric_id)
    decision = usage_decision(definition.metric_id, usage)
    return (
        decision == "warn"
        or definition.reliability in {"approximate", "low", "unavailable"}
        or _confidence_rank(confidence) < _CONFIDENCE_RANK["high"]
    )


def _confidence_rank(confidence: str | None) -> int:
    return _CONFIDENCE_RANK.get(str(confidence or "unavailable"), 0)
