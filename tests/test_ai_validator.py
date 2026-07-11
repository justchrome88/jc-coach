import json
from copy import deepcopy

from app.services.ai_coach import (
    AI_COACH_DOMAIN_CONTRACT_VERSION,
    AI_COACH_PAYLOAD_SCHEMA_VERSION,
    AI_COACH_PROMPT_VERSION,
    AI_COACH_SNAPSHOT_CONTRACT_VERSION,
    AI_COACH_SNAPSHOT_GENERATED_BY,
    build_ai_coach_payload,
    save_ai_coach_result,
    serialize_ai_coach_report,
)
from app.services.ai_validator import validate_ai_coach_output
from app.services.ingestion.structured_import import import_rows
from app.services.metric_truth import METRIC_REGISTRY_VERSION


def _valid_output(**overrides):
    payload = {
        "summary": "Main issue is survivability in opening duels.",
        "insight_cards": [
            {
                "problem": "Opening duel survival is the current evidence-backed focus.",
                "evidence": [
                    {
                        "metric_id": "entry_deaths",
                        "value": 3,
                        "metric_confidence": "medium",
                        "description": "Entry deaths are elevated in the current sample.",
                    }
                ],
                "confidence": "medium",
                "caveats": ["Opening duel detection depends on parser/source order."],
                "recommended_focus": "Play first 20 seconds slower and avoid isolated opening fights.",
            }
        ],
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
        "evidence": [
            {
                "metric_id": "entry_deaths",
                "value": 3,
                "metric_confidence": "medium",
                "caveats": ["Source/order dependent."],
            }
        ],
        "confidence": "medium",
    }
    payload.update(overrides)
    return payload


def _valid_payload_snapshot():
    return {
        "contract_snapshot": {
            "ai_coach_prompt_version": AI_COACH_PROMPT_VERSION,
            "ai_coach_payload_schema_version": AI_COACH_PAYLOAD_SCHEMA_VERSION,
            "metric_registry_version": METRIC_REGISTRY_VERSION,
            "snapshot_generated_by": AI_COACH_SNAPSHOT_GENERATED_BY,
            "snapshot_contract_version": AI_COACH_SNAPSHOT_CONTRACT_VERSION,
        },
        "domain_contract_version": AI_COACH_DOMAIN_CONTRACT_VERSION,
        "domain_constraints": {
            "current_product_version": "v0.9",
            "v1_0_claim_allowed": False,
            "accepted_active_hard_recommendation_id": 5,
            "legacy_recommendation_ids_blocked_for_new_hard_evaluations": [1, 3, 4],
        },
        "claim_guardrails": {"do_not_invent_parser_data": True},
        "metric_confidence_policy": {
            "missing_metric_confidence_blocks_hard_advice": True,
            "weak_metrics_must_remain_caveated": True,
        },
        "playlist_mode_policy": {
            "mode_status": "unknown_or_provenance_only",
            "unsupported_exact_playlist_claims": [
                "Premier",
                "Competitive",
                "Wingman",
                "Casual",
                "Deathmatch",
                "FACEIT",
                "custom",
            ],
        },
        "recommendation_policy": {
            "current_accepted_active_hard_recommendation_id": 5,
            "legacy_recommendations_not_for_new_hard_evaluations": [1, 3, 4],
        },
        "public_readiness_policy": {
            "current_product_version": "v0.9",
            "v1_0_claim_allowed": False,
            "public_readiness": "blocked",
            "friends_readiness": "blocked",
            "public_or_friends_claim_allowed": False,
        },
        "metric_confidence": {
            "metrics": {
                "entry_deaths": {"level": "medium"},
                "early_deaths": {"level": "low"},
            }
        },
    }


def test_valid_structured_output_passes():
    result = validate_ai_coach_output(_valid_output())

    assert result.valid is True
    assert result.output is not None
    assert result.fallback_markdown is None


def test_valid_structured_output_passes_semantic_runtime_contract():
    result = validate_ai_coach_output(_valid_output(), payload_snapshot=_valid_payload_snapshot())

    assert result.valid is True
    assert result.output is not None
    assert result.fallback_markdown is None


def test_missing_required_sections_rejected_with_fallback():
    result = validate_ai_coach_output({"summary": "too small"})

    assert result.valid is False
    assert result.fallback_markdown
    assert any(issue.code == "missing_required_key" for issue in result.issues)


def test_missing_insight_card_required_field_is_rejected():
    output = _valid_output(
        insight_cards=[
            {
                "problem": "Opening deaths are elevated.",
                "evidence": [{"metric_id": "entry_deaths", "metric_confidence": "medium"}],
                "confidence": "medium",
                "caveats": ["Source/order dependent."],
            }
        ]
    )

    result = validate_ai_coach_output(output)

    assert result.valid is False
    assert any(issue.code == "missing_insight_card_field" for issue in result.issues)


def test_no_data_insight_card_requires_low_confidence_and_caveat():
    output = _valid_output(
        insight_cards=[
            {
                "problem": "No validated coach insight is available yet.",
                "evidence": [],
                "confidence": "low",
                "caveats": ["No supported evidence was available for this card."],
                "recommended_focus": "Use the current accepted recommendation until more evidence exists.",
            }
        ]
    )

    result = validate_ai_coach_output(output)

    assert result.valid is True


def test_no_data_insight_card_without_caveat_is_rejected():
    output = _valid_output(
        insight_cards=[
            {
                "problem": "No validated coach insight is available yet.",
                "evidence": [],
                "confidence": "medium",
                "caveats": [],
                "recommended_focus": "Use the current accepted recommendation until more evidence exists.",
            }
        ]
    )

    result = validate_ai_coach_output(output)

    assert result.valid is False
    codes = {issue.code for issue in result.issues}
    assert "insight_no_evidence_requires_low_confidence" in codes
    assert "insight_no_evidence_requires_caveat" in codes


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
    assert any(issue.code == "suppressed_metric_claim" for issue in result.issues)


def test_public_friends_and_v1_readiness_claims_are_rejected():
    output = _valid_output(summary="JC Coach is v1.0 ready and safe for public and friends use.")

    result = validate_ai_coach_output(output, payload_snapshot=_valid_payload_snapshot())

    assert result.valid is False
    codes = {issue.code for issue in result.issues}
    assert "unsupported_public_readiness_claim" in codes
    assert "unsupported_v1_claim" in codes


def test_exact_playlist_mode_claim_is_rejected_when_mode_is_provenance_only():
    output = _valid_output(
        diagnoses=[
            {
                "category": "mode",
                "severity": "medium",
                "claim": "This Premier match proves the current mode-specific issue.",
                "evidence_metric_ids": ["entry_deaths"],
                "confidence": "medium",
                "caveats": ["Opening duel detection depends on parser/source order."],
            }
        ],
    )

    result = validate_ai_coach_output(output, payload_snapshot=_valid_payload_snapshot())

    assert result.valid is False
    assert any(issue.code == "unsupported_exact_playlist_claim" for issue in result.issues)


def test_weak_metric_hard_advice_without_caveat_is_rejected():
    output = _valid_output(
        recommendations=[
            {
                "category": "survival",
                "action": "You must change opening pathing because early deaths prove the main issue.",
                "rationale": "This is a hard recommendation from early deaths.",
                "target_metric_ids": ["early_deaths"],
                "confidence": "high",
                "caveats": [],
            }
        ],
        evidence=[
            {
                "metric_id": "early_deaths",
                "value": 2,
                "metric_confidence": "low",
                "caveats": ["Parser timing anchors are limited."],
            }
        ],
    )

    result = validate_ai_coach_output(output, payload_snapshot=_valid_payload_snapshot())

    assert result.valid is False
    codes = {issue.code for issue in result.issues}
    assert "metric_requires_caveat" in codes
    assert "weak_metric_hard_advice" in codes


def test_unavailable_utility_metric_cannot_support_hard_advice_without_caveat():
    payload_snapshot = deepcopy(_valid_payload_snapshot())
    payload_snapshot["metric_confidence"]["metrics"]["grenade_rating"] = {"level": "unavailable"}
    output = _valid_output(
        diagnoses=[
            {
                "category": "grenades",
                "severity": "high",
                "claim": "Grenade rating proves utility quality is poor.",
                "evidence_metric_ids": ["grenade_rating"],
                "confidence": "high",
                "caveats": [],
            }
        ],
        recommendations=[
            {
                "category": "grenades",
                "action": "Replace all grenade routines because grenade rating is bad.",
                "rationale": "The metric is treated as hard evidence.",
                "target_metric_ids": ["grenade_rating"],
                "confidence": "high",
                "caveats": [],
            }
        ],
        evidence=[
            {
                "metric_id": "grenade_rating",
                "value": None,
                "metric_confidence": "unavailable",
                "caveats": ["Unsupported grenade_rating is omitted rather than inferred from weak utility events."],
            }
        ],
    )

    result = validate_ai_coach_output(output, payload_snapshot=payload_snapshot)

    assert result.valid is False
    codes = {issue.code for issue in result.issues}
    assert "suppressed_metric_claim" in codes
    assert "weak_metric_hard_advice" in codes


def test_legacy_recommendation_hard_evaluation_is_rejected_without_refresh():
    output = _valid_output(
        summary="Recommendation #1 is working and completed successfully.",
        evidence=[
            {
                "metric_id": "entry_deaths",
                "value": 2,
                "metric_confidence": "medium",
                "recommendation_id": 1,
                "caveats": ["New hard evaluation attempted without refresh."],
            }
        ],
    )

    result = validate_ai_coach_output(output, payload_snapshot=_valid_payload_snapshot())

    assert result.valid is False
    assert any(issue.code == "legacy_recommendation_hard_evaluation" for issue in result.issues)


def test_unsupported_invented_cs2_model_claim_is_rejected():
    output = _valid_output(
        recommendations=[
            {
                "category": "economy",
                "action": "Use a new buy strategy because the economy model proves bad force-buy choices.",
                "rationale": "The model shows hard economy mistakes.",
                "target_metric_ids": ["entry_deaths"],
                "confidence": "medium",
                "caveats": ["Opening duel detection depends on parser/source order."],
            }
        ],
    )

    result = validate_ai_coach_output(output, payload_snapshot=_valid_payload_snapshot())

    assert result.valid is False
    assert any(issue.code == "unsupported_economy_model_claim" for issue in result.issues)


def test_missing_version_snapshot_or_domain_metadata_is_rejected():
    payload_snapshot = deepcopy(_valid_payload_snapshot())
    payload_snapshot.pop("contract_snapshot")
    payload_snapshot.pop("domain_constraints")

    result = validate_ai_coach_output(_valid_output(), payload_snapshot=payload_snapshot)

    assert result.valid is False
    codes = {issue.code for issue in result.issues}
    assert "missing_contract_metadata" in codes
    assert "missing_domain_contract_metadata" in codes


def test_invalid_provider_output_does_not_crash_and_saves_safe_fallback(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    report = save_ai_coach_result(db, "Free-form confident advice based on crosshair_placement.", source_ref="mock")
    serialized = serialize_ai_coach_report(report)

    assert "AI output rejected by validator" in report.report_markdown
    assert serialized["insight_cards"][0]["confidence"] == "low"
    assert serialized["insight_cards"][0]["evidence"] == []
    assert serialized["insight_cards"][0]["caveats"]
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


def test_semantic_invalid_json_saves_safe_fallback_with_metadata(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    report = save_ai_coach_result(
        db,
        json.dumps(_valid_output(summary="JC Coach is v1.0 ready for public and friends use.")),
        source_ref="mock",
    )
    serialized = serialize_ai_coach_report(report)

    assert "AI output rejected by validator" in report.report_markdown
    assert serialized["metadata"]["ai_validation"]["valid"] is False
    assert serialized["metadata"]["ai_validation"]["fallback_used"] is True
    assert "ai_structured_output" not in serialized["metadata"]
    assert serialized["metadata"]["ai_coach_prompt_version"] == AI_COACH_PROMPT_VERSION
    assert serialized["metadata"]["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert serialized["metadata"]["public_readiness_policy"]["public_or_friends_claim_allowed"] is False


def test_valid_json_output_is_rendered_and_metadata_keeps_structured_output(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    report = save_ai_coach_result(db, json.dumps(_valid_output()), source_ref="mock")
    serialized = serialize_ai_coach_report(report)

    assert "Entry deaths are too frequent" in report.report_markdown
    assert "Insight Cards" in report.report_markdown
    assert serialized["insight_cards"][0]["problem"] == "Opening duel survival is the current evidence-backed focus."
    assert serialized["metadata"]["insight_cards"] == serialized["insight_cards"]
    assert serialized["metadata"]["ai_validation"]["valid"] is True
    assert serialized["metadata"]["ai_structured_output"]["confidence"] == "medium"
    assert serialized["metadata"]["ai_coach_prompt_version"] == AI_COACH_PROMPT_VERSION
    assert serialized["metadata"]["ai_coach_payload_schema_version"] == AI_COACH_PAYLOAD_SCHEMA_VERSION
    assert serialized["metadata"]["metric_registry_version"] == METRIC_REGISTRY_VERSION
    assert serialized["metadata"]["snapshot_generated_by"] == AI_COACH_SNAPSHOT_GENERATED_BY
    assert serialized["metadata"]["snapshot_contract_version"] == AI_COACH_SNAPSHOT_CONTRACT_VERSION
    assert serialized["metadata"]["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert serialized["metadata"]["domain_constraints"]["accepted_active_hard_recommendation_id"] == 5
    assert serialized["metadata"]["metric_confidence_policy"]["weak_metrics_must_remain_caveated"] is True
    assert serialized["metadata"]["playlist_mode_policy"]["mode_status"] == "unknown_or_provenance_only"
    assert serialized["metadata"]["public_readiness_policy"]["v1_0_claim_allowed"] is False


def test_runtime_payload_snapshot_metadata_passes_semantic_validator(db, sample_rows):
    import_rows(db, sample_rows, source="test")
    payload_snapshot = build_ai_coach_payload(db)

    result = validate_ai_coach_output(_valid_output(), payload_snapshot=payload_snapshot)

    assert result.valid is True
