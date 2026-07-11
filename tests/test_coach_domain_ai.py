from __future__ import annotations

import json
from pathlib import Path

from app.services.coach_domain_ai import (
    OUTPUT_SCHEMA_VERSION,
    temporal_survival_metrics,
    validate_domain_output,
)


def _evidence() -> dict:
    return {
        "identity": {"owner_steamid": "765"},
        "phase": {
            "rounds": [
                {"round_number": 1, "start_tick": 0, "end_tick": 6400, "phase": "regulation"},
                {"round_number": 2, "start_tick": 6400, "end_tick": 12800, "phase": "regulation"},
                {"round_number": 24, "start_tick": 12800, "end_tick": 19200, "phase": "overtime"},
                {"round_number": 25, "start_tick": 19200, "end_tick": 25600, "phase": "overtime"},
            ]
        },
        "participation": {
            "roster_steamids": ["765"],
            "owner_spawns": [],
            "owner_connects": [{"round_number": 24, "tick": 15000, "team": 3}],
            "owner_disconnects": [{"round_number": 24, "tick": 14000, "team": 3}],
            "owner_team_events": [
                {"round_number": 1, "tick": 0, "team": 2},
                {"round_number": 2, "tick": 6400, "team": 3},
                {"round_number": 24, "tick": 12800, "team": 3},
                {"round_number": 25, "tick": 19200, "team": 2},
            ],
        },
        "events": {
            "deaths": [
                {"round_number": 1, "tick": 2560, "victim_steamid": "765"},
                {"round_number": 25, "tick": 26000, "victim_steamid": "765"},
            ]
        },
    }


def test_temporal_survival_distinguishes_death_survival_disconnect_overtime_and_post_round() -> None:
    metrics, ledger = temporal_survival_metrics(_evidence())

    assert [row["outcome"] for row in ledger] == ["died", "survived", "incomplete_round", "survived"]
    assert ledger[2]["phase"] == "overtime"
    assert ledger[2]["disconnect"] is True and ledger[2]["reconnect"] is True
    assert ledger[3]["post_round_death_excluded"] is True
    assert metrics["survival_time_seconds_per_participated_round"] == [40.0, 100.0, 100.0]
    assert metrics["early_death_rate_before_45_seconds"] == 0.333
    assert metrics["average_death_time_t_side_seconds"] == 40.0
    assert metrics["average_death_time_ct_side_seconds"] is None


def test_structured_schema_is_strict_and_json_valid() -> None:
    schema = json.loads((Path(__file__).parents[1] / "docs/coach/schemas/ai-domain-hypothesis.schema.json").read_text())
    assert schema["additionalProperties"] is False
    assert schema["properties"]["mission_proposal"]["anyOf"][1]["additionalProperties"] is False
    evidence_schema = json.loads(
        (Path(__file__).parents[1] / "docs/coach/evidence-schemas/coach-domain-evidence.schema.json").read_text()
    )
    assert evidence_schema["$id"] == "coach-domain-evidence-v1"
    assert evidence_schema["properties"]["per_match_observations"]["minItems"] == 30


def test_validator_accepts_grounded_no_problem_and_rejects_claim_injection() -> None:
    bundle = {
        "domain_key": "impact_leak",
        "baseline": {"match_ids": list(range(1, 31))},
        "metric_versions": {"adr": "3.0.0"},
        "aggregates": {"adr": 75.0},
        "evidence_refs": {"aggregate:adr": {"metric_key": "adr", "value": 75.0}},
    }
    output = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "domain_key": "impact_leak",
        "analysis_status": "no_material_problem",
        "headline": "No material pattern",
        "hypothesis": "The supplied evidence does not support a material problem.",
        "reasoning_summary": "ADR is adequate, while the bundle does not establish repeated costly deaths.",
        "primary_pattern": "No supported pattern",
        "evidence_refs": ["aggregate:adr"],
        "counterevidence_refs": ["aggregate:adr"],
        "metric_refs": [{"metric_key": "adr", "value": 75.0, "evidence_ref": "aggregate:adr"}],
        "match_refs": [1],
        "confidence": "medium",
        "confidence_rationale": "Thirty validated matches.",
        "caveats": ["No tactical location evidence."],
        "recommended_focus": "Maintain current discipline.",
        "mission_proposal": None,
    }
    assert validate_domain_output(output, bundle) == ()

    output["hypothesis"] = "The exact angle and API key caused the issue."
    errors = validate_domain_output(output, bundle)
    assert "unsupported_tactical_claim" in errors
    assert "secret_or_raw_payload_leakage" in errors
