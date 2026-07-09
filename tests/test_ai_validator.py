import json

from app.services.ai_coach import (
    AI_COACH_DOMAIN_CONTRACT_VERSION,
    AI_COACH_PROMPT_VERSION,
    save_ai_coach_result,
    serialize_ai_coach_report,
)
from app.services.ai_validator import validate_ai_coach_output
from app.services.importer import import_rows
from app.services.metric_truth import METRIC_REGISTRY_VERSION


def _valid_output(**overrides):
    payload = {
        "summary": "Main issue is survivability in opening duels.",
        "diagnoses": [
            {
                "category": "survival",
                "severity": "medium",
                "claim": "Entry deaths are too frequent.",
                "evidence_metric_ids": ["entry_deaths"],
                "confidence": "medium",
                "caveats": ["Opening duel detection depends on parser/source order."],
            }
        ],
        "recommendations": [
            {
                "category": "survival",
                "action": "Play first 20 seconds slower and trade with teammate.",
                "rationale": "Reduce opening deaths before taking wider fights.",
                "target_metric_ids": ["entry_deaths"],
                "confidence": "medium",
                "caveats": ["Track over the next 5 matches."],
            }
        ],
        "warnings": ["Do not infer crosshair placement from current data."],
        "evidence": [{"metric_id": "entry_deaths", "value": 3, "caveats": ["Source/order dependent."]}],
        "confidence": "medium",
    }
    payload.update(overrides)
    return payload


def test_valid_structured_output_passes():
    result = validate_ai_coach_output(_valid_output())

    assert result.valid is True
    assert result.output is not None
    assert result.fallback_markdown is None


def test_missing_required_sections_rejected_with_fallback():
    result = validate_ai_coach_output({"summary": "too small"})

    assert result.valid is False
    assert result.fallback_markdown
    assert any(issue.code == "missing_required_key" for issue in result.issues)


def test_unknown_metric_id_rejected():
    output = _valid_output(
        diagnoses=[
            {
                "category": "aim",
                "severity": "high",
                "claim": "Unknown metric proves aim issue.",
                "evidence_metric_ids": ["imaginary_metric"],
                "confidence": "high",
                "caveats": [],
            }
        ]
    )

    result = validate_ai_coach_output(output)

    assert result.valid is False
    assert any(issue.code == "unknown_metric_id" for issue in result.issues)


def test_suppressed_metric_cannot_support_hard_diagnosis():
    output = _valid_output(
        diagnoses=[
            {
                "category": "trade",
                "severity": "high",
                "claim": "Trade kills prove a hard diagnosis.",
                "evidence_metric_ids": ["trade_kills"],
                "confidence": "high",
                "caveats": ["Parser trade inference is weak."],
            }
        ]
    )

    result = validate_ai_coach_output(output)

    assert result.valid is False
    assert any(issue.code == "suppressed_metric_claim" for issue in result.issues)


def test_unavailable_metric_cannot_support_recommendation():
    output = _valid_output(
        recommendations=[
            {
                "category": "aim",
                "action": "Train crosshair placement.",
                "rationale": "AI claimed unavailable aim rating is low.",
                "target_metric_ids": ["aim_rating"],
                "confidence": "high",
                "caveats": [],
            }
        ]
    )

    result = validate_ai_coach_output(output)

    assert result.valid is False
    assert any(issue.code == "suppressed_metric_claim" for issue in result.issues)


def test_approximate_metric_requires_caveat():
    output = _valid_output(
        diagnoses=[
            {
                "category": "survival",
                "severity": "medium",
                "claim": "KAST is the main issue.",
                "evidence_metric_ids": ["kast"],
                "confidence": "medium",
                "caveats": [],
            }
        ]
    )

    result = validate_ai_coach_output(output)

    assert result.valid is False
    assert any(issue.code == "metric_requires_caveat" for issue in result.issues)


def test_invalid_provider_output_does_not_crash_and_saves_safe_fallback(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    report = save_ai_coach_result(db, "Free-form confident advice based on crosshair_placement.", source_ref="mock")
    serialized = serialize_ai_coach_report(report)

    assert "AI output rejected by validator" in report.report_markdown
    assert serialized["metadata"]["ai_validation"]["valid"] is False
    assert serialized["metadata"]["ai_validation"]["fallback_used"] is True
    assert serialized["metadata"]["ai_coach_prompt_version"] == AI_COACH_PROMPT_VERSION
    assert serialized["metadata"]["metric_registry_version"] == METRIC_REGISTRY_VERSION
    assert serialized["metadata"]["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert serialized["metadata"]["domain_constraints"]["accepted_active_hard_recommendation_id"] == 5
    assert serialized["metadata"]["metric_confidence_policy"]["weak_metrics_must_remain_caveated"] is True
    assert serialized["metadata"]["playlist_mode_policy"]["mode_status"] == "unknown_or_provenance_only"
    assert serialized["metadata"]["public_readiness_policy"]["v1_0_claim_allowed"] is False
    assert serialized["metadata"]["public_readiness_policy"]["friends_readiness"] == "blocked"


def test_valid_json_output_is_rendered_and_metadata_keeps_structured_output(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    report = save_ai_coach_result(db, json.dumps(_valid_output()), source_ref="mock")
    serialized = serialize_ai_coach_report(report)

    assert "Entry deaths are too frequent" in report.report_markdown
    assert serialized["metadata"]["ai_validation"]["valid"] is True
    assert serialized["metadata"]["ai_structured_output"]["confidence"] == "medium"
