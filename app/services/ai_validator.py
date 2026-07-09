from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.services.metric_truth import metric_definition, usage_decision

AIConfidence = Literal["low", "medium", "high"]

REQUIRED_TOP_LEVEL_KEYS = ("summary", "diagnoses", "recommendations", "warnings", "evidence", "confidence")
VALID_CONFIDENCE: set[str] = {"low", "medium", "high"}
REQUIRED_CONTRACT_SNAPSHOT_KEYS = (
    "ai_coach_prompt_version",
    "ai_coach_payload_schema_version",
    "metric_registry_version",
    "snapshot_generated_by",
    "snapshot_contract_version",
)
REQUIRED_DOMAIN_CONTRACT_KEYS = (
    "domain_contract_version",
    "domain_constraints",
    "claim_guardrails",
    "metric_confidence_policy",
    "playlist_mode_policy",
    "recommendation_policy",
    "public_readiness_policy",
)
HARD_ADVICE_PATTERN = re.compile(
    r"\b(proves?|guarantees?|must|always|definitely|certainly|main issue|primary problem|"
    r"hard recommendation|complete[sd]?|failed?|success|working|ready)\b"
    r"|главн(?:ая|ый|ое)\s+проблем|точно|обязан|доказ|готов",
    re.IGNORECASE,
)
PUBLIC_READY_PATTERN = re.compile(
    r"\b(public|friends?)\b.{0,50}\b(ready|available|supported|enabled|safe|can use|open)\b"
    r"|\b(ready|available|supported|enabled|safe|open)\b.{0,50}\b(public|friends?)\b",
    re.IGNORECASE,
)
V1_READY_PATTERN = re.compile(
    r"\b(v1\.0|version\s+1\.0|1\.0)\b.{0,50}\b(ready|released|accepted|promoted|complete|production)\b"
    r"|\b(ready|released|accepted|promoted|complete|production)\b.{0,50}\b(v1\.0|version\s+1\.0)\b",
    re.IGNORECASE,
)
UNSUPPORTED_CONCEPT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "unsupported_economy_model_claim",
        re.compile(r"\b(economy model|buy strategy|force[- ]?buy|full[- ]?buy|eco round|save call)\b", re.I),
    ),
    (
        "unsupported_positioning_model_claim",
        re.compile(
            r"\b(positioning model|positioning|rotations?|spacing|angle discipline|crosshair placement|heatmap)\b",
            re.I,
        ),
    ),
    (
        "unsupported_clutch_model_claim",
        re.compile(r"\b(clutch model|clutch win(?:rate)?|clutch conversion|clutch mistakes?|1v[1-5])\b", re.I),
    ),
    (
        "unsupported_trade_model_claim",
        re.compile(r"\b(trade model|trade quality|traded deaths?|untraded deaths?|trade window)\b", re.I),
    ),
    (
        "unsupported_parser_data_claim",
        re.compile(r"\b(parser data shows|parser proves|view[- ]?angle|position timeline|round timeline)\b", re.I),
    ),
    (
        "unsupported_exact_match_date_claim",
        re.compile(r"\b(exact match date|played exactly on|\d{4}-\d{2}-\d{2})\b", re.I),
    ),
)
NEGATION_PATTERN = re.compile(
    r"\b(not|no|do not|don't|cannot|can't|blocked|unknown|unavailable|unsupported|data gap|"
    r"не|нет|нельзя|заблок|недоступ|неизвест)\b",
    re.IGNORECASE,
)


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


def validate_ai_coach_output(
    raw_output: str | dict[str, Any],
    payload_snapshot: dict[str, Any] | None = None,
) -> AIValidationResult:
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

    if payload_snapshot is not None:
        _validate_runtime_metadata(payload_snapshot, issues)
        _validate_semantic_contract(output, payload_snapshot, issues)

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


def _validate_runtime_metadata(payload_snapshot: dict[str, Any], issues: list[AIValidationIssue]) -> None:
    snapshot = payload_snapshot.get("contract_snapshot")
    if not isinstance(snapshot, dict):
        issues.append(
            AIValidationIssue(
                "missing_contract_metadata",
                "AI coach payload snapshot is missing contract_snapshot metadata.",
                "$.payload_snapshot.contract_snapshot",
            )
        )
    else:
        for key in REQUIRED_CONTRACT_SNAPSHOT_KEYS:
            if not isinstance(snapshot.get(key), str) or not snapshot.get(key, "").strip():
                issues.append(
                    AIValidationIssue(
                        "missing_contract_metadata",
                        f"AI coach payload snapshot is missing contract snapshot field: {key}.",
                        f"$.payload_snapshot.contract_snapshot.{key}",
                    )
                )

    for key in REQUIRED_DOMAIN_CONTRACT_KEYS:
        value = payload_snapshot.get(key)
        if key == "domain_contract_version":
            if not isinstance(value, str) or not value.strip():
                issues.append(
                    AIValidationIssue(
                        "missing_domain_contract_metadata",
                        "AI coach payload snapshot is missing domain_contract_version.",
                        "$.payload_snapshot.domain_contract_version",
                    )
                )
            continue
        if not isinstance(value, dict) or not value:
            issues.append(
                AIValidationIssue(
                    "missing_domain_contract_metadata",
                    f"AI coach payload snapshot is missing domain contract field: {key}.",
                    f"$.payload_snapshot.{key}",
                )
            )

    public_policy = payload_snapshot.get("public_readiness_policy") or {}
    if public_policy.get("v1_0_claim_allowed") is not False:
        issues.append(
            AIValidationIssue(
                "malformed_domain_contract_metadata",
                "Domain contract must keep v1.0 claims blocked.",
                "$.payload_snapshot.public_readiness_policy.v1_0_claim_allowed",
            )
        )
    if public_policy.get("public_or_friends_claim_allowed") is not False:
        issues.append(
            AIValidationIssue(
                "malformed_domain_contract_metadata",
                "Domain contract must keep public/friends readiness claims blocked.",
                "$.payload_snapshot.public_readiness_policy.public_or_friends_claim_allowed",
            )
        )

    playlist_policy = payload_snapshot.get("playlist_mode_policy") or {}
    if playlist_policy.get("mode_status") != "unknown_or_provenance_only":
        issues.append(
            AIValidationIssue(
                "malformed_domain_contract_metadata",
                "Domain contract must keep playlist/mode unknown or provenance-only.",
                "$.payload_snapshot.playlist_mode_policy.mode_status",
            )
        )


def _validate_semantic_contract(
    output: dict[str, Any],
    payload_snapshot: dict[str, Any],
    issues: list[AIValidationIssue],
) -> None:
    _validate_claim_text_boundaries(output, payload_snapshot, issues)
    _validate_evidence_links(output, issues)
    _validate_weak_metric_hard_advice(output, payload_snapshot, issues)
    _validate_legacy_recommendation_claims(output, payload_snapshot, issues)


def _validate_claim_text_boundaries(
    output: dict[str, Any],
    payload_snapshot: dict[str, Any],
    issues: list[AIValidationIssue],
) -> None:
    for path, text in _semantic_claim_texts(output):
        if PUBLIC_READY_PATTERN.search(text) and not _is_negated_claim(text, PUBLIC_READY_PATTERN):
            issues.append(
                AIValidationIssue(
                    "unsupported_public_readiness_claim",
                    "AI output must not claim public or friends readiness.",
                    path,
                )
            )
        if V1_READY_PATTERN.search(text) and not _is_negated_claim(text, V1_READY_PATTERN):
            issues.append(AIValidationIssue("unsupported_v1_claim", "AI output must not claim v1.0 readiness.", path))
        _validate_playlist_claim_text(text, path, payload_snapshot, issues)
        for code, pattern in UNSUPPORTED_CONCEPT_PATTERNS:
            if pattern.search(text) and not _is_negated_claim(text, pattern):
                issues.append(
                    AIValidationIssue(
                        code,
                        "AI output claimed an unsupported CS2 model or parser fact not accepted by the payload.",
                        path,
                    )
                )


def _validate_playlist_claim_text(
    text: str,
    path: str,
    payload_snapshot: dict[str, Any],
    issues: list[AIValidationIssue],
) -> None:
    policy = payload_snapshot.get("playlist_mode_policy") if isinstance(payload_snapshot, dict) else {}
    if not isinstance(policy, dict) or policy.get("mode_status") != "unknown_or_provenance_only":
        return
    unsupported = policy.get("unsupported_exact_playlist_claims") or []
    for label in unsupported:
        if not isinstance(label, str) or not label.strip():
            continue
        pattern = re.compile(
            rf"\b{re.escape(label)}\b(?:\W+\w+){{0,4}}\W+\b(mode|playlist|match|queue|режим|матч)\b"
            rf"|\b(mode|playlist|match|queue|режим|матч)\b(?:\W+\w+){{0,4}}\W+\b{re.escape(label)}\b",
            re.IGNORECASE,
        )
        if pattern.search(text) and not _is_negated_claim(text, pattern):
            issues.append(
                AIValidationIssue(
                    "unsupported_exact_playlist_claim",
                    f"AI output must not claim exact playlist/mode: {label}.",
                    path,
                )
            )


def _validate_evidence_links(output: dict[str, Any], issues: list[AIValidationIssue]) -> None:
    evidence_items = [item for item in output.get("evidence") or [] if isinstance(item, dict)]
    evidence_by_metric = {str(item.get("metric_id")): item for item in evidence_items if item.get("metric_id")}
    for metric_id in _claimed_metric_ids(output):
        evidence = evidence_by_metric.get(metric_id)
        if evidence is None:
            issues.append(
                AIValidationIssue(
                    "missing_evidence_link",
                    f"{metric_id} is claimed but has no evidence item.",
                    "$.evidence",
                )
            )
            continue
        if not evidence.get("metric_confidence"):
            issues.append(
                AIValidationIssue(
                    "missing_metric_confidence",
                    f"{metric_id} evidence is missing metric_confidence.",
                    f"$.evidence[{metric_id}].metric_confidence",
                )
            )


def _validate_weak_metric_hard_advice(
    output: dict[str, Any],
    payload_snapshot: dict[str, Any],
    issues: list[AIValidationIssue],
) -> None:
    payload_confidence = _payload_metric_confidence(payload_snapshot)
    for section, metric_field in (("diagnoses", "evidence_metric_ids"), ("recommendations", "target_metric_ids")):
        for index, item in enumerate(output.get(section) or []):
            if not isinstance(item, dict):
                continue
            metric_ids = item.get(metric_field) if isinstance(item.get(metric_field), list) else []
            caveats = item.get("caveats") if isinstance(item.get("caveats"), list) else []
            has_caveat = any(str(caveat).strip() for caveat in caveats)
            text = " ".join(str(item.get(key) or "") for key in ("claim", "action", "rationale"))
            if not HARD_ADVICE_PATTERN.search(text):
                continue
            for metric_id in metric_ids:
                if not isinstance(metric_id, str):
                    continue
                definition = metric_definition(metric_id)
                usage = "diagnosis" if section == "diagnoses" else "recommendation"
                decision = usage_decision(definition.metric_id, usage)
                confidence = payload_confidence.get(definition.metric_id)
                if (
                    decision != "allowed"
                    or definition.reliability in {"approximate", "low", "unavailable"}
                    or confidence in {"low", "low_confidence", "unavailable"}
                ) and not has_caveat:
                    issues.append(
                        AIValidationIssue(
                            "weak_metric_hard_advice",
                            f"{definition.metric_id} cannot support hard advice without visible caveats.",
                            f"$.{section}[{index}]",
                        )
                    )


def _validate_legacy_recommendation_claims(
    output: dict[str, Any],
    payload_snapshot: dict[str, Any],
    issues: list[AIValidationIssue],
) -> None:
    policy = payload_snapshot.get("recommendation_policy") if isinstance(payload_snapshot, dict) else {}
    blocked = set(policy.get("legacy_recommendations_not_for_new_hard_evaluations") or [1, 3, 4])
    for path, text in _semantic_claim_texts(output):
        for rec_id in blocked:
            legacy_ref = re.search(rf"\b(?:recommendation|rec)\s*#?\s*{rec_id}\b", text, re.I)
            if legacy_ref and HARD_ADVICE_PATTERN.search(text):
                issues.append(
                    AIValidationIssue(
                        "legacy_recommendation_hard_evaluation",
                        f"Legacy recommendation #{rec_id} must not receive a new hard evaluation without refresh.",
                        path,
                    )
                )
    for index, evidence in enumerate(output.get("evidence") or []):
        if not isinstance(evidence, dict):
            continue
        rec_id = _coerce_int(evidence.get("recommendation_id"))
        if rec_id in blocked and not _legacy_refresh_caveated(evidence):
            issues.append(
                AIValidationIssue(
                    "legacy_recommendation_hard_evaluation",
                    f"Legacy recommendation #{rec_id} must not receive a new hard evaluation without refresh.",
                    f"$.evidence[{index}].recommendation_id",
                )
            )


def _semantic_claim_texts(output: dict[str, Any]) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    if isinstance(output.get("summary"), str):
        texts.append(("$.summary", output["summary"]))
    for section in ("diagnoses", "recommendations"):
        for index, item in enumerate(output.get(section) or []):
            if not isinstance(item, dict):
                continue
            fields = ("claim",) if section == "diagnoses" else ("action", "rationale")
            value = " ".join(str(item.get(field) or "") for field in fields)
            texts.append((f"$.{section}[{index}]", value))
    return texts


def _is_negated_claim(text: str, pattern: re.Pattern[str]) -> bool:
    match = pattern.search(text)
    if not match:
        return False
    start = max(match.start() - 36, 0)
    end = min(match.end() + 24, len(text))
    return bool(NEGATION_PATTERN.search(text[start:end]))


def _payload_metric_confidence(payload_snapshot: dict[str, Any]) -> dict[str, str]:
    metrics = ((payload_snapshot.get("metric_confidence") or {}).get("metrics") or {}) if payload_snapshot else {}
    confidence: dict[str, str] = {}
    if not isinstance(metrics, dict):
        return confidence
    for metric_id, value in metrics.items():
        if isinstance(value, dict):
            confidence[str(metric_id)] = str(value.get("level") or value.get("confidence") or "")
        elif value is not None:
            confidence[str(metric_id)] = str(value)
    return confidence


def _claimed_metric_ids(output: dict[str, Any]) -> set[str]:
    claimed: set[str] = set()
    for diagnosis in output.get("diagnoses") or []:
        if isinstance(diagnosis, dict):
            claimed.update(str(metric_id) for metric_id in diagnosis.get("evidence_metric_ids") or [])
    for recommendation in output.get("recommendations") or []:
        if isinstance(recommendation, dict):
            claimed.update(str(metric_id) for metric_id in recommendation.get("target_metric_ids") or [])
    return claimed


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _legacy_refresh_caveated(evidence: dict[str, Any]) -> bool:
    caveats = evidence.get("caveats") if isinstance(evidence.get("caveats"), list) else []
    text = " ".join(str(item) for item in caveats)
    return bool(re.search(r"\b(refresh|refreshed|legacy|not hard|context only)\b", text, re.I))
