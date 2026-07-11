import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.services.ai_coach import (
    AI_COACH_DOMAIN_CONTRACT_VERSION,
    AI_COACH_PAYLOAD_SCHEMA_VERSION,
    AI_COACH_PROMPT_VERSION,
    AI_COACH_SNAPSHOT_CONTRACT_VERSION,
    AI_COACH_SNAPSHOT_GENERATED_BY,
    save_ai_coach_result,
    serialize_ai_coach_report,
)
from app.services.ai_validator import validate_ai_coach_output
from app.services.ingestion.structured_import import import_rows
from app.services.metric_truth import METRIC_REGISTRY_VERSION
from tests.semantic_ai_eval import evaluate_semantic_ai_output, issue_codes

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ai_semantic_eval" / "output_quality_cases.json"


def _cases() -> list[dict]:
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)["cases"]


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
def test_ai_output_quality_acceptance_fixtures(case):
    validation = validate_ai_coach_output(
        case["output"],
        payload_snapshot=_payload_snapshot(case["payload_snapshot"]),
    )
    runtime_codes = {issue.code for issue in validation.issues}
    semantic_codes = issue_codes(
        evaluate_semantic_ai_output(case["output"], case["evidence_payload"]),
    )

    expected_runtime_codes = set(case["expected_runtime_issue_codes"])
    expected_semantic_codes = set(case["expected_semantic_issue_codes"])

    if case["acceptance"] == "accepted":
        assert validation.valid is True
        assert runtime_codes == set()
        assert semantic_codes == set()
        return

    assert case["acceptance"] == "rejected"
    assert validation.valid is False or expected_semantic_codes
    assert expected_runtime_codes.issubset(runtime_codes)
    assert expected_semantic_codes.issubset(semantic_codes)
    assert validation.fallback_markdown or expected_semantic_codes
    _assert_diagnostic_issues_are_debuggable(validation.issues, expected_runtime_codes)


def test_output_quality_fixture_safe_fallback_persists_metadata_failure(db, sample_rows):
    import_rows(db, sample_rows, source="test")
    case = next(item for item in _cases() if item["id"] == "rejected_missing_wp018_metadata")

    report = save_ai_coach_result(
        db,
        json.dumps(case["output"]),
        source_ref="output-quality-fixture",
        payload_snapshot=_payload_snapshot(case["payload_snapshot"]),
    )
    serialized = serialize_ai_coach_report(report)
    issue_codes_from_report = {
        issue["code"]
        for issue in serialized["metadata"]["ai_validation"]["issues"]
    }

    assert "AI output rejected by validator" in report.report_markdown
    assert serialized["metadata"]["ai_validation"]["valid"] is False
    assert serialized["metadata"]["ai_validation"]["fallback_used"] is True
    assert "ai_structured_output" not in serialized["metadata"]
    assert set(case["expected_runtime_issue_codes"]).issubset(issue_codes_from_report)


def test_output_quality_fixture_set_covers_required_acceptance_classes():
    coverage = {
        marker
        for case in _cases()
        for marker in case["coverage"]
    }

    assert {
        "recommendation_5",
        "metric_confidence",
        "weak_metric_caveats",
        "playlist_mode_uncertainty",
        "public_readiness_blocked",
        "v1_claim_blocked",
        "unsupported_economy_claim",
        "unsupported_positioning_claim",
        "unsupported_clutch_claim",
        "unsupported_trade_claim",
        "unsupported_parser_claim",
        "unsupported_exact_match_date_claim",
        "safe_fallback_expectations",
        "evidence_chain_complete",
        "wp018_02_metadata_required",
        "wp018_03_domain_metadata_required",
    }.issubset(coverage)


def _payload_snapshot(kind: str) -> dict:
    snapshot = _valid_payload_snapshot()
    if kind == "valid":
        return snapshot
    if kind == "missing_metadata":
        broken = deepcopy(snapshot)
        broken.pop("contract_snapshot")
        broken.pop("domain_constraints")
        broken.pop("playlist_mode_policy")
        return broken
    raise AssertionError(f"Unknown payload snapshot fixture kind: {kind}")


def _valid_payload_snapshot() -> dict:
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
            "steam_import_max_demos_per_run": 1,
        },
        "claim_guardrails": {"do_not_invent_parser_data": True},
        "metric_confidence_policy": {
            "missing_metric_confidence_blocks_hard_advice": True,
            "weak_metrics_must_remain_caveated": True,
        },
        "playlist_mode_policy": {
            "mode_status": "unknown_or_provenance_only",
            "source_labels_are_provenance_not_playlist": True,
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
                "kast": {"level": "low"},
            }
        },
    }


def _assert_diagnostic_issues_are_debuggable(issues, expected_codes: set[str]) -> None:
    if not expected_codes:
        return
    matched = [issue for issue in issues if issue.code in expected_codes]
    assert matched
    for issue in matched:
        assert issue.message
        assert issue.path.startswith("$")
