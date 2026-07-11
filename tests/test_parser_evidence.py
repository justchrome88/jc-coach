import json
from pathlib import Path

import pytest

from app.services.parsing.evidence import (
    PARSER_EVIDENCE_SCHEMA_VERSION,
    ParserEvidenceError,
    parser_evidence_from_payload,
    validate_parser_evidence,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "parser"


def _load_json(name: str):
    return json.loads((FIXTURE_DIR / name).read_text())


def test_accepted_parser_evidence_fixture_is_valid_and_complete():
    evidence = _load_json("parser_evidence_accepted_c2.json")

    artifact = validate_parser_evidence(evidence)

    assert artifact.schema_version == PARSER_EVIDENCE_SCHEMA_VERSION
    assert artifact.parser_identity == {
        "name": "demoparser2",
        "version": "synthetic-test-version",
        "payload_version": "synthetic-c2",
    }
    assert artifact.source_refs["external_match_id"] == "synthetic-parser-c2"
    assert artifact.event_counts["player_death"] == 36
    assert artifact.metric_confidence["adr"] == "medium"
    assert artifact.parser_confidence == "medium"
    assert artifact.warnings
    assert "traded_deaths" in artifact.data_gaps
    assert artifact.hard_claim_support["diagnosis"] == ()


def test_parser_evidence_builder_preserves_sanitized_payload_metadata():
    payload = _load_json("sanitized_parser_payload_c2.json")["payload"]

    evidence = parser_evidence_from_payload(
        payload,
        hard_claim_support={"diagnosis": []},
        data_gaps=["economy_model", "positioning_model", "clutch_model"],
    )
    artifact = validate_parser_evidence(evidence)

    assert artifact.parser_identity["name"] == payload["parser"]
    assert artifact.parser_identity["payload_version"] == payload["payload_version"]
    assert artifact.source_refs["demo_sha1"] == payload["demo_sha1"]
    assert artifact.event_counts == payload["event_counts"]
    assert artifact.metric_confidence == payload["metric_confidence"]
    assert artifact.parser_confidence == payload["parser_confidence"]
    assert "traded_deaths" in artifact.data_gaps


@pytest.mark.parametrize("case", _load_json("parser_evidence_rejected_cases.json"), ids=lambda case: case["id"])
def test_rejected_parser_evidence_fixtures_fail_closed(case):
    with pytest.raises(ParserEvidenceError) as exc_info:
        validate_parser_evidence(case["evidence"])

    assert case["expected_issue"] in exc_info.value.issues
