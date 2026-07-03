from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.services.metric_truth import metric_definition, usage_decision

AIConfidence = Literal["low", "medium", "high"]

REQUIRED_TOP_LEVEL_KEYS = ("summary", "diagnoses", "recommendations", "warnings", "evidence", "confidence")
VALID_CONFIDENCE: set[str] = {"low", "medium", "high"}


@dataclass(frozen=True)
class AIValidationIssue:
    code: str
    message: str
    path: str
    severity: Literal["warning", "error"] = "error"


@dataclass(frozen=True)
class AIValidationResult:
    valid: bool
    output: dict[str, Any] | None
    issues: tuple[AIValidationIssue, ...]
    fallback_markdown: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [asdict(issue) for issue in self.issues],
            "fallback_used": self.fallback_markdown is not None,
        }


def validate_ai_coach_output(raw_output: str | dict[str, Any]) -> AIValidationResult:
    output, parse_issue = _coerce_output(raw_output)
    issues: list[AIValidationIssue] = []
    if parse_issue:
        issues.append(parse_issue)
        return _invalid_result(issues)
    if output is None:
        issues.append(AIValidationIssue("invalid_output", "AI output is empty or not an object.", "$"))
        return _invalid_result(issues)

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in output:
            issues.append(AIValidationIssue("missing_required_key", f"Missing required section: {key}.", f"$.{key}"))

    if output.get("confidence") not in VALID_CONFIDENCE:
        issues.append(
            AIValidationIssue(
                "invalid_confidence",
                "Top-level confidence must be one of: low, medium, high.",
                "$.confidence",
            )
        )

    _validate_list(output, "diagnoses", issues)
    _validate_list(output, "recommendations", issues)
    _validate_list(output, "warnings", issues)
    _validate_list(output, "evidence", issues)

    for index, diagnosis in enumerate(output.get("diagnoses") or []):
        if not isinstance(diagnosis, dict):
            issues.append(
                AIValidationIssue("invalid_diagnosis", "Diagnosis item must be an object.", f"$.diagnoses[{index}]")
            )
            continue
        _require_string(diagnosis, "category", f"$.diagnoses[{index}]", issues)
        _require_string(diagnosis, "claim", f"$.diagnoses[{index}]", issues)
        _validate_confidence(diagnosis, f"$.diagnoses[{index}]", issues)
        _validate_metric_claims(
            diagnosis.get("evidence_metric_ids"),
            usage="diagnosis",
            caveats=diagnosis.get("caveats"),
            path=f"$.diagnoses[{index}].evidence_metric_ids",
            issues=issues,
        )

    for index, recommendation in enumerate(output.get("recommendations") or []):
        if not isinstance(recommendation, dict):
            issues.append(
                AIValidationIssue(
                    "invalid_recommendation",
                    "Recommendation item must be an object.",
                    f"$.recommendations[{index}]",
                )
            )
            continue
        _require_string(recommendation, "category", f"$.recommendations[{index}]", issues)
        _require_string(recommendation, "action", f"$.recommendations[{index}]", issues)
        _require_string(recommendation, "rationale", f"$.recommendations[{index}]", issues)
        _validate_confidence(recommendation, f"$.recommendations[{index}]", issues)
        _validate_metric_claims(
            recommendation.get("target_metric_ids"),
            usage="recommendation",
            caveats=recommendation.get("caveats"),
            path=f"$.recommendations[{index}].target_metric_ids",
            issues=issues,
        )

    for index, evidence in enumerate(output.get("evidence") or []):
        if not isinstance(evidence, dict):
            issues.append(
                AIValidationIssue("invalid_evidence", "Evidence item must be an object.", f"$.evidence[{index}]")
            )
            continue
        metric_id = evidence.get("metric_id")
        if metric_id is not None:
            _validate_metric_claims(
                [metric_id],
                usage="ai",
                caveats=evidence.get("caveats") or evidence.get("warning"),
                path=f"$.evidence[{index}].metric_id",
                issues=issues,
            )

    errors = tuple(issue for issue in issues if issue.severity == "error")
    if errors:
        return _invalid_result(issues)
    return AIValidationResult(valid=True, output=output, issues=tuple(issues))


def render_ai_output_markdown(output: dict[str, Any]) -> str:
    lines = [
        "# AI Coach Report",
        "",
        str(output.get("summary") or "Структурированный AI-отчёт без summary."),
        "",
        f"Confidence: {output.get('confidence')}",
        "",
        "## Диагнозы",
    ]
    for diagnosis in output.get("diagnoses") or []:
        metrics = ", ".join(diagnosis.get("evidence_metric_ids") or []) or "no metrics"
        caveats = "; ".join(diagnosis.get("caveats") or [])
        suffix = f" Caveats: {caveats}" if caveats else ""
        lines.append(f"- {diagnosis.get('category')}: {diagnosis.get('claim')} [{metrics}].{suffix}")
    lines.extend(["", "## Рекомендации"])
    for recommendation in output.get("recommendations") or []:
        metrics = ", ".join(recommendation.get("target_metric_ids") or []) or "no metrics"
        caveats = "; ".join(recommendation.get("caveats") or [])
        suffix = f" Caveats: {caveats}" if caveats else ""
        lines.append(
            f"- {recommendation.get('category')}: {recommendation.get('action')} "
            f"Rationale: {recommendation.get('rationale')} [{metrics}].{suffix}"
        )
    warnings = output.get("warnings") or []
    if warnings:
        lines.extend(["", "## Предупреждения"])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines).strip()


def safe_ai_fallback_markdown(issues: list[AIValidationIssue] | tuple[AIValidationIssue, ...]) -> str:
    lines = [
        "# AI Coach Report",
        "",
        "AI output rejected by validator.",
        "",
        "Этот отчёт не принят как уверенный coaching advice, потому что структура или metric evidence "
        "не прошли проверку.",
        "Используйте dashboard, Metric Truth Layer и текущие рекомендации как source of truth.",
        "",
        "## Validation issues",
    ]
    lines.extend(f"- {issue.code}: {issue.message} ({issue.path})" for issue in issues)
    return "\n".join(lines)


def _invalid_result(issues: list[AIValidationIssue]) -> AIValidationResult:
    return AIValidationResult(
        valid=False,
        output=None,
        issues=tuple(issues),
        fallback_markdown=safe_ai_fallback_markdown(issues),
    )


def _coerce_output(raw_output: str | dict[str, Any]) -> tuple[dict[str, Any] | None, AIValidationIssue | None]:
    if isinstance(raw_output, dict):
        return raw_output, None
    text = raw_output.strip()
    if not text:
        return None, AIValidationIssue("empty_output", "AI output is empty.", "$")
    candidate = _extract_json_candidate(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, AIValidationIssue("invalid_json", f"AI output is not valid structured JSON: {exc.msg}.", "$")
    if not isinstance(parsed, dict):
        return None, AIValidationIssue("invalid_json_type", "AI output JSON must be an object.", "$")
    return parsed, None


def _extract_json_candidate(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)
    return text


def _validate_list(output: dict[str, Any], key: str, issues: list[AIValidationIssue]) -> None:
    if key in output and not isinstance(output[key], list):
        issues.append(AIValidationIssue("invalid_section_type", f"{key} must be a list.", f"$.{key}"))


def _require_string(item: dict[str, Any], key: str, path: str, issues: list[AIValidationIssue]) -> None:
    if not isinstance(item.get(key), str) or not item.get(key).strip():
        issues.append(AIValidationIssue("missing_required_field", f"Missing required field: {key}.", f"{path}.{key}"))


def _validate_confidence(item: dict[str, Any], path: str, issues: list[AIValidationIssue]) -> None:
    if item.get("confidence") not in VALID_CONFIDENCE:
        issues.append(
            AIValidationIssue(
                "invalid_confidence",
                "Item confidence must be one of: low, medium, high.",
                f"{path}.confidence",
            )
        )


def _validate_metric_claims(
    metric_ids: Any,
    usage: Literal["diagnosis", "recommendation", "ai"],
    caveats: Any,
    path: str,
    issues: list[AIValidationIssue],
) -> None:
    if not isinstance(metric_ids, list) or not metric_ids:
        issues.append(AIValidationIssue("missing_metric_evidence", "Metric evidence list is required.", path))
        return
    caveat_items = caveats if isinstance(caveats, list) else ([caveats] if isinstance(caveats, str) else [])
    has_caveat = any(str(item).strip() for item in caveat_items)
    for metric_id in metric_ids:
        if not isinstance(metric_id, str) or not metric_id.strip():
            issues.append(AIValidationIssue("invalid_metric_id", "Metric id must be a non-empty string.", path))
            continue
        definition = metric_definition(metric_id)
        if definition.metric_id == "unknown":
            issues.append(AIValidationIssue("unknown_metric_id", f"Unknown metric id: {metric_id}.", path))
            continue
        decision = usage_decision(definition.metric_id, usage)
        if decision == "suppressed" or definition.reliability == "unavailable":
            issues.append(
                AIValidationIssue(
                    "suppressed_metric_claim",
                    f"{definition.metric_id} cannot support {usage}: {definition.reliability}/{decision}.",
                    path,
                )
            )
            continue
        if decision == "warn" and not has_caveat:
            issues.append(
                AIValidationIssue(
                    "metric_requires_caveat",
                    f"{definition.metric_id} requires caveat for {usage}: {definition.reliability}.",
                    path,
                )
            )
