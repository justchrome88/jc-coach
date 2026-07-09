from __future__ import annotations

from dataclasses import dataclass
from typing import Any

INSIGHT_CARD_SCHEMA_VERSION = "coach-insight-card-v1"
VALID_INSIGHT_CONFIDENCE = {"low", "medium", "high"}
REQUIRED_INSIGHT_CARD_FIELDS = ("problem", "evidence", "confidence", "caveats", "recommended_focus")


@dataclass(frozen=True)
class InsightCardValidationIssue:
    code: str
    message: str
    path: str


def validate_insight_cards(raw_cards: Any, *, path: str = "$.insight_cards") -> tuple[InsightCardValidationIssue, ...]:
    issues: list[InsightCardValidationIssue] = []
    if not isinstance(raw_cards, list):
        return (
            InsightCardValidationIssue(
                "invalid_insight_cards",
                "insight_cards must be a list.",
                path,
            ),
        )
    if not raw_cards:
        return (
            InsightCardValidationIssue(
                "missing_insight_cards",
                "At least one insight card is required.",
                path,
            ),
        )

    for index, card in enumerate(raw_cards):
        card_path = f"{path}[{index}]"
        if not isinstance(card, dict):
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_card",
                    "Insight card must be an object.",
                    card_path,
                )
            )
            continue
        for field in REQUIRED_INSIGHT_CARD_FIELDS:
            if field not in card:
                issues.append(
                    InsightCardValidationIssue(
                        "missing_insight_card_field",
                        f"Missing required insight card field: {field}.",
                        f"{card_path}.{field}",
                    )
                )
        _validate_non_empty_string(card, "problem", card_path, issues)
        _validate_non_empty_string(card, "recommended_focus", card_path, issues)
        confidence = card.get("confidence")
        if confidence not in VALID_INSIGHT_CONFIDENCE:
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_confidence",
                    "Insight card confidence must be one of: low, medium, high.",
                    f"{card_path}.confidence",
                )
            )
        evidence = card.get("evidence")
        caveats = _string_list(card.get("caveats"))
        if not isinstance(card.get("caveats"), list):
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_caveats",
                    "Insight card caveats must be a list.",
                    f"{card_path}.caveats",
                )
            )
        elif any(not str(item).strip() for item in card.get("caveats") or []):
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_caveat",
                    "Insight card caveats must be non-empty strings.",
                    f"{card_path}.caveats",
                )
            )
        _validate_evidence(evidence, confidence, caveats, card_path, issues)
    return tuple(issues)


def serialize_insight_cards(raw_cards: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_cards, list):
        return []
    serialized: list[dict[str, Any]] = []
    for card in raw_cards:
        if not isinstance(card, dict):
            continue
        evidence = card.get("evidence") if isinstance(card.get("evidence"), list) else []
        caveats = _string_list(card.get("caveats"))
        serialized.append(
            {
                "schema_version": INSIGHT_CARD_SCHEMA_VERSION,
                "problem": str(card.get("problem") or "").strip(),
                "evidence": [dict(item) for item in evidence if isinstance(item, dict)],
                "confidence": str(card.get("confidence") or "").strip(),
                "caveats": caveats,
                "recommended_focus": str(card.get("recommended_focus") or "").strip(),
            }
        )
    return serialized


def no_data_insight_card(reason: str) -> dict[str, Any]:
    recommended_focus = "Use the dashboard and current accepted recommendation until validated insight data exists."
    return {
        "schema_version": INSIGHT_CARD_SCHEMA_VERSION,
        "problem": "No validated coach insight is available from the submitted AI output.",
        "evidence": [],
        "confidence": "low",
        "caveats": [reason],
        "recommended_focus": recommended_focus,
    }


def _validate_non_empty_string(
    card: dict[str, Any],
    field: str,
    path: str,
    issues: list[InsightCardValidationIssue],
) -> None:
    if not isinstance(card.get(field), str) or not card.get(field, "").strip():
        issues.append(
            InsightCardValidationIssue(
                "invalid_insight_card_field",
                f"Insight card field must be a non-empty string: {field}.",
                f"{path}.{field}",
            )
        )


def _validate_evidence(
    evidence: Any,
    confidence: Any,
    caveats: list[str],
    path: str,
    issues: list[InsightCardValidationIssue],
) -> None:
    if not isinstance(evidence, list):
        issues.append(
            InsightCardValidationIssue(
                "invalid_insight_evidence",
                "Insight card evidence must be a list.",
                f"{path}.evidence",
            )
        )
        return
    if not evidence:
        if confidence != "low":
            issues.append(
                InsightCardValidationIssue(
                    "insight_no_evidence_requires_low_confidence",
                    "Insight cards without evidence must use low confidence.",
                    f"{path}.confidence",
                )
            )
        if not caveats:
            issues.append(
                InsightCardValidationIssue(
                    "insight_no_evidence_requires_caveat",
                    "Insight cards without evidence must include a caveat.",
                    f"{path}.caveats",
                )
            )
        return
    for evidence_index, item in enumerate(evidence):
        evidence_path = f"{path}.evidence[{evidence_index}]"
        if not isinstance(item, dict):
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_evidence_item",
                    "Insight card evidence item must be an object.",
                    evidence_path,
                )
            )
            continue
        if not _has_evidence_content(item):
            issues.append(
                InsightCardValidationIssue(
                    "empty_insight_evidence_item",
                    "Insight card evidence item needs metric_id, description, match_ids, sample_count or value.",
                    evidence_path,
                )
            )


def _has_evidence_content(item: dict[str, Any]) -> bool:
    return any(
        key in item and item[key] not in (None, "", [])
        for key in ("metric_id", "description", "match_ids", "sample_count", "value")
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
