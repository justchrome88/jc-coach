"""Parser evidence validation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.shared.metric_policy import (
    USAGES,
    MetricUsage,
    is_metric_allowed_for_hard_claim,
)

PARSER_EVIDENCE_SCHEMA_VERSION = "parser-evidence-v1"
CONFIDENCE_LEVELS = {"high", "medium", "low", "unavailable"}
PARSER_CONFIDENCE_LEVELS = {"high", "medium", "low"}
HARD_CLAIM_CONFIDENCE_LEVELS = {"high", "medium"}
EXACT_SOURCE_DATE_PROVENANCE = {
    "steam_gc_match_time": {
        "source_system": "steam_history",
        "source_field": "played_at",
        "trust_class": "source_provided",
        "timezone_semantics": "UTC instant normalized from the persisted Steam GC match time",
    },
    "demo_header": {
        "source_system": "demo_parser",
        "source_field": "header.played_at",
        "trust_class": "source_provided",
        "timezone_semantics": "parser-provided value; an offset is not persisted in the match row",
    },
}


@dataclass(frozen=True)
class ParserEvidence:
    schema_version: str
    parser_identity: dict[str, str]
    source_refs: dict[str, Any]
    event_counts: dict[str, int]
    metric_confidence: dict[str, str]
    parser_confidence: str
    warnings: tuple[str, ...]
    data_gaps: tuple[str, ...]
    hard_claim_support: dict[MetricUsage, tuple[str, ...]]


class ParserEvidenceError(ValueError):
    def __init__(self, issues: list[str]):
        super().__init__("Parser evidence failed validation: " + ", ".join(issues))
        self.issues = issues


def parser_evidence_from_payload(
    payload: dict[str, Any],
    *,
    hard_claim_support: dict[str, list[str]] | None = None,
    data_gaps: list[str] | None = None,
) -> dict[str, Any]:
    """Build a fixture-safe evidence artifact from an already parsed payload."""
    match = payload.get("match") if isinstance(payload.get("match"), dict) else {}
    metric_confidence = _dict_or_empty(payload.get("metric_confidence"))
    gaps = _ordered_unique(
        [
            *(data_gaps if data_gaps is not None else _list_or_empty(payload.get("data_gaps"))),
            *_list_or_empty(payload.get("aim_data_gaps")),
            *[metric_id for metric_id, level in metric_confidence.items() if level == "unavailable"],
        ]
    )
    return {
        "schema_version": PARSER_EVIDENCE_SCHEMA_VERSION,
        "parser_identity": {
            "name": str(payload.get("parser") or ""),
            "version": str(payload.get("parser_version") or ""),
            "payload_version": str(payload.get("payload_version") or ""),
        },
        "source_refs": {
            "demo_file": payload.get("file"),
            "demo_sha1": payload.get("demo_sha1"),
            "external_match_id": match.get("external_match_id"),
            "played_at_source": payload.get("played_at_source") or match.get("played_at_source"),
            "match_date_source": payload.get("match_date_source") or match.get("match_date_source"),
            "match_date_status": payload.get("match_date_status") or match.get("match_date_status"),
            "source_date_provenance": source_date_provenance(payload),
        },
        "event_counts": _dict_or_empty(payload.get("event_counts")),
        "metric_confidence": metric_confidence,
        "parser_confidence": payload.get("parser_confidence"),
        "warnings": _list_or_empty(payload.get("warnings")),
        "data_gaps": gaps,
        "hard_claim_support": hard_claim_support or {},
    }


def source_date_provenance(payload: dict[str, Any], *, date_value_present: bool | None = None) -> dict[str, Any]:
    """Describe only the persisted source evidence for a match date."""
    match = payload.get("match") if isinstance(payload.get("match"), dict) else {}
    source = (
        payload.get("played_at_source")
        or payload.get("match_date_source")
        or match.get("played_at_source")
        or match.get("match_date_source")
    )
    played_at = payload.get("played_at") or match.get("played_at")
    has_date = bool(played_at) if date_value_present is None else bool(date_value_present)
    if source in EXACT_SOURCE_DATE_PROVENANCE:
        return {"status": "available", **EXACT_SOURCE_DATE_PROVENANCE[str(source)]}
    if source == "file_modified_fallback":
        return {
            "status": "available",
            "source_system": "demo_storage",
            "source_field": "file_modified_timestamp",
            "trust_class": "approximate_fallback",
            "timezone_semantics": "UTC-derived value persisted without an offset",
        }
    reason_code = "source_marker_unavailable" if source == "unavailable" else "source_marker_not_persisted"
    return {
        "status": "unavailable",
        "reason_code": reason_code,
        "date_value_preserved": has_date,
    }


def validate_parser_evidence(evidence: dict[str, Any]) -> ParserEvidence:
    issues: list[str] = []

    schema_version = evidence.get("schema_version")
    if schema_version != PARSER_EVIDENCE_SCHEMA_VERSION:
        issues.append("unsupported_schema_version")

    parser_identity = _dict_or_empty(evidence.get("parser_identity"))
    for field in ("name", "version", "payload_version"):
        if not parser_identity.get(field):
            issues.append(f"missing_parser_identity_{field}")

    source_refs = _dict_or_empty(evidence.get("source_refs"))
    for field in ("demo_file", "demo_sha1", "external_match_id"):
        if not source_refs.get(field):
            issues.append(f"missing_source_ref_{field}")

    event_counts = _dict_or_empty(evidence.get("event_counts"))
    if not event_counts:
        issues.append("missing_event_counts")
    for event_name, count in event_counts.items():
        if not isinstance(event_name, str) or not isinstance(count, int) or count < 0:
            issues.append("invalid_event_counts")
            break

    metric_confidence = _dict_or_empty(evidence.get("metric_confidence"))
    if not metric_confidence:
        issues.append("missing_metric_confidence")
    for metric_id, level in metric_confidence.items():
        if not isinstance(metric_id, str) or level not in CONFIDENCE_LEVELS:
            issues.append("invalid_metric_confidence")
            break

    parser_confidence = evidence.get("parser_confidence")
    if parser_confidence not in PARSER_CONFIDENCE_LEVELS:
        issues.append("missing_parser_confidence")

    warnings = _list_or_empty(evidence.get("warnings"))
    if any(not isinstance(warning, str) or not warning.strip() for warning in warnings):
        issues.append("invalid_warnings")

    data_gaps = _list_or_empty(evidence.get("data_gaps"))
    if any(not isinstance(gap, str) or not gap.strip() for gap in data_gaps):
        issues.append("invalid_data_gaps")

    hard_claim_support = _validate_hard_claim_support(evidence.get("hard_claim_support"), metric_confidence, issues)

    if issues:
        raise ParserEvidenceError(_ordered_unique(issues))

    return ParserEvidence(
        schema_version=schema_version,
        parser_identity={str(key): str(value) for key, value in parser_identity.items()},
        source_refs=source_refs,
        event_counts={str(key): int(value) for key, value in event_counts.items()},
        metric_confidence={str(key): str(value) for key, value in metric_confidence.items()},
        parser_confidence=str(parser_confidence),
        warnings=tuple(warnings),
        data_gaps=tuple(data_gaps),
        hard_claim_support=hard_claim_support,
    )


def _validate_hard_claim_support(
    value: Any,
    metric_confidence: dict[str, str],
    issues: list[str],
) -> dict[MetricUsage, tuple[str, ...]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        issues.append("invalid_hard_claim_support")
        return {}

    validated: dict[MetricUsage, tuple[str, ...]] = {}
    for usage, metric_ids in value.items():
        if usage not in USAGES:
            issues.append("invalid_hard_claim_usage")
            continue
        if not isinstance(metric_ids, list):
            issues.append("invalid_hard_claim_metrics")
            continue
        accepted: list[str] = []
        for metric_id in metric_ids:
            if not isinstance(metric_id, str) or not metric_id.strip():
                issues.append("invalid_hard_claim_metric")
                continue
            confidence = metric_confidence.get(metric_id)
            if confidence is None:
                issues.append(f"missing_hard_claim_metric_confidence:{metric_id}")
                continue
            if confidence not in HARD_CLAIM_CONFIDENCE_LEVELS:
                issues.append(f"insufficient_hard_claim_metric_confidence:{metric_id}")
                continue
            if not is_metric_allowed_for_hard_claim(metric_id, usage):
                issues.append(f"unsupported_hard_claim_support:{metric_id}:{usage}")
                continue
            accepted.append(metric_id)
        validated[usage] = tuple(accepted)
    return validated


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
