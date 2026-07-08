import json
from pathlib import Path

import pytest

from tests.semantic_ai_eval import evaluate_semantic_ai_output, issue_codes

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ai_semantic_eval" / "e1_cases.json"


def _cases() -> list[dict]:
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)["cases"]


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
def test_e1_semantic_ai_eval_cases_are_deterministic_and_local(case):
    issues = evaluate_semantic_ai_output(case["output"], case["evidence_payload"])
    actual_codes = issue_codes(issues)
    expected_codes = set(case["expected_issue_codes"])

    if expected_codes:
        assert expected_codes.issubset(actual_codes)
    else:
        assert actual_codes == set()


def test_e1_valid_case_preserves_batch_d_advice_confidence_contract():
    case = next(item for item in _cases() if item["id"] == "fh090_fh095_valid_advice_confidence_evidence_link")

    issues = evaluate_semantic_ai_output(case["output"], case["evidence_payload"])
    evidence = case["output"]["evidence"][0]

    assert issues == ()
    assert evidence["metric_confidence"] == "medium"
    assert evidence["problem"] == "survival_opening_deaths"
    assert evidence["match_ids"] == [101, 102, 103]
    assert evidence["recommendation_id"] == "rec-survival-1"
