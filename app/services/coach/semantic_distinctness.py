"""Safe semantic-distinctness evidence for the canonical two coach cards."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from difflib import SequenceMatcher
from typing import Any

from app.services.coach_domain_model import CANONICAL_COACH_DOMAINS

SEMANTIC_DISTINCTNESS_VERSION = "two-card-semantic-distinctness-v1"
NEAR_DUPLICATE_THRESHOLD = 0.90
_TEXT_FIELDS = (
    "headline",
    "hypothesis",
    "primary_pattern",
    "reasoning_summary",
    "recommended_focus",
)
_EXACT_DUPLICATE_FIELDS = ("headline", "hypothesis", "recommended_focus")
_UNSUPPORTED_CAUSE = re.compile(
    r"\b(exact (angle|position|rotation|spacing)|crosshair placement|economy mistake|clutch decision)\b",
    re.IGNORECASE,
)


class DuplicateDomainCardSemanticsError(ValueError):
    """Raised when the canonical cards express the same diagnosis under two labels."""


def two_card_semantic_distinctness(cards: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return hash-only semantic comparison evidence or reject duplicate diagnoses."""
    if len(cards) != 2:
        raise DuplicateDomainCardSemanticsError("exactly_two_domain_cards_required")
    by_domain = {str(card.get("domain") or ""): card for card in cards}
    if set(by_domain) != set(CANONICAL_COACH_DOMAINS):
        raise DuplicateDomainCardSemanticsError("canonical_domain_keys_required")

    normalized = {
        domain: {field: _normalize(card.get(field)) for field in _TEXT_FIELDS}
        for domain, card in by_domain.items()
    }
    exact_duplicate_fields = [
        field
        for field in _EXACT_DUPLICATE_FIELDS
        if normalized[CANONICAL_COACH_DOMAINS[0]][field]
        == normalized[CANONICAL_COACH_DOMAINS[1]][field]
    ]
    combined = {
        domain: " ".join(normalized[domain][field] for field in _TEXT_FIELDS)
        for domain in CANONICAL_COACH_DOMAINS
    }
    combined_similarity = SequenceMatcher(
        None,
        combined[CANONICAL_COACH_DOMAINS[0]],
        combined[CANONICAL_COACH_DOMAINS[1]],
    ).ratio()
    field_similarity = {
        field: round(
            SequenceMatcher(
                None,
                normalized[CANONICAL_COACH_DOMAINS[0]][field],
                normalized[CANONICAL_COACH_DOMAINS[1]][field],
            ).ratio(),
            6,
        )
        for field in _TEXT_FIELDS
    }
    hashes = {
        domain: {
            **{field: _hash(normalized[domain][field]) for field in _TEXT_FIELDS},
            "evidence_references": _hash(_normalized_sequence(by_domain[domain].get("evidence_references"))),
            "counterevidence_references": _hash(
                _normalized_sequence(by_domain[domain].get("counterevidence_references"))
            ),
            "caveats": _hash(_normalized_sequence(by_domain[domain].get("caveats"))),
            "mission_target": _hash(_canonical(by_domain[domain].get("mission_target") or {})),
        }
        for domain in CANONICAL_COACH_DOMAINS
    }
    reasoning_distinct = (
        hashes[CANONICAL_COACH_DOMAINS[0]]["reasoning_summary"]
        != hashes[CANONICAL_COACH_DOMAINS[1]]["reasoning_summary"]
    )
    evidence_distinct = (
        hashes[CANONICAL_COACH_DOMAINS[0]]["evidence_references"]
        != hashes[CANONICAL_COACH_DOMAINS[1]]["evidence_references"]
    )
    unsupported_domains = [
        domain
        for domain in CANONICAL_COACH_DOMAINS
        if _UNSUPPORTED_CAUSE.search(combined[domain])
    ]
    primary_metrics = {
        domain: str((by_domain[domain].get("mission_target") or {}).get("primary_metric") or "")
        for domain in CANONICAL_COACH_DOMAINS
    }
    shared_metric = (
        primary_metrics[CANONICAL_COACH_DOMAINS[0]]
        if primary_metrics[CANONICAL_COACH_DOMAINS[0]]
        and len(set(primary_metrics.values())) == 1
        else None
    )
    issues: list[str] = []
    if exact_duplicate_fields:
        issues.append("normalized_headline_hypothesis_or_focus_duplicate")
    if combined_similarity >= NEAR_DUPLICATE_THRESHOLD:
        issues.append("near_duplicate_diagnosis")
    if not (reasoning_distinct or evidence_distinct):
        issues.append("missing_domain_specific_reasoning_or_evidence")
    if unsupported_domains:
        issues.append("unsupported_spatial_or_tactical_cause")
    result = {
        "schema_version": SEMANTIC_DISTINCTNESS_VERSION,
        "status": "PASS" if not issues else "BLOCKED_DUPLICATE_DOMAIN_CARD_SEMANTICS",
        "domain_keys": list(CANONICAL_COACH_DOMAINS),
        "domain_keys_distinct": True,
        "normalized_exact_duplicate_fields": exact_duplicate_fields,
        "normalized_field_similarity": field_similarity,
        "combined_diagnosis_similarity": round(combined_similarity, 6),
        "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
        "domain_specific_reasoning_distinct": reasoning_distinct,
        "domain_specific_evidence_distinct": evidence_distinct,
        "safe_field_hashes": hashes,
        "shared_primary_metric": shared_metric,
        "shared_metric_explanation": (
            f"{shared_metric} supports distinct impact-conversion and fight-selection hypotheses."
            if shared_metric
            else None
        ),
        "unsupported_cause_domains": unsupported_domains,
        "issues": issues,
    }
    if issues:
        raise DuplicateDomainCardSemanticsError(",".join(issues))
    return result


def _normalize(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _normalized_sequence(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return sorted(_canonical(item) for item in value)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()


__all__ = (
    "DuplicateDomainCardSemanticsError",
    "NEAR_DUPLICATE_THRESHOLD",
    "SEMANTIC_DISTINCTNESS_VERSION",
    "two_card_semantic_distinctness",
)
