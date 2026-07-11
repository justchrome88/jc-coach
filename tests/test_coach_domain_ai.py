from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.db.models import (
    AIDomainAnalysis,
    CoachDomainSlot,
    CoachEvidenceBaseline,
    CoachMissionProposal,
    SteamAccount,
    User,
)
from app.services.coach.domain_analysis import (
    OUTPUT_SCHEMA_VERSION,
    activate_domain_proposal,
    coach_domain_slots_payload,
    temporal_survival_metrics,
    validate_domain_output,
)
from app.services.missions.payloads import mission_domain_key
from app.services.missions.repository import list_active_coach_missions


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
    schema = json.loads(
        (Path(__file__).parents[1] / "app/contracts/coach/schemas/ai-domain-hypothesis.schema.json").read_text()
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["mission_proposal"]["anyOf"][1]["additionalProperties"] is False
    evidence_schema = json.loads(
        (Path(__file__).parents[1] / "app/contracts/coach/schemas/coach-domain-evidence.schema.json").read_text()
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


def test_current_ai_domain_proposals_activate_explicit_domains_and_reuse(db) -> None:
    owner = User(display_name="owner")
    db.add(owner)
    db.flush()
    account = SteamAccount(user_id=owner.id, steam_id="76561198000000017")
    db.add(account)
    db.flush()
    baseline = CoachEvidenceBaseline(
        owner_user_id=owner.id,
        owner_steam_id=account.steam_id,
        analysis_cutoff=datetime.now(UTC),
        status="eligible",
        baseline_hash="b" * 64,
        evidence_version="coach-domain-baseline-v1",
        match_ids_json=json.dumps(list(range(1, 31))),
        lineage_json="[]",
        exclusions_json="[]",
    )
    db.add(baseline)
    db.flush()

    created = []
    for index, domain in enumerate(("impact_leak", "bad_fight_selection"), start=1):
        output = {
            "analysis_status": "supported_hypothesis",
            "domain_key": domain,
            "headline": domain,
            "hypothesis": f"Supported {domain}",
            "recommended_focus": "Use supported trade evidence.",
            "confidence": "medium",
            "caveats": ["No spatial claim."],
            "metric_refs": [
                {
                    "metric_key": "untraded_death_rate",
                    "value": 0.8,
                    "evidence_ref": "aggregate:untraded_death_rate",
                }
            ],
        }
        analysis = AIDomainAnalysis(
            owner_user_id=owner.id,
            owner_steam_id=account.steam_id,
            domain_key=domain,
            baseline_id=baseline.id,
            baseline_hash=baseline.baseline_hash,
            idempotency_key=str(index) * 64,
            attempt_number=1,
            prompt_version="two-domain-hypothesis-v1",
            prompt_hash="p" * 64,
            evidence_schema_version="coach-domain-evidence-v1",
            evidence_hash=str(index + 2) * 64,
            provider="fixture",
            model="fixture",
            routing_json="{}",
            settings_json="{}",
            raw_response_hash=str(index + 4) * 64,
            structured_output_json=json.dumps(output),
            validation_status="accepted",
            validation_errors_json="[]",
        )
        db.add(analysis)
        db.flush()
        payload = {
            "title": domain,
            "goal": "Improve supported metric.",
            "behavioral_focus": "Use supported trade evidence.",
            "primary_metric": "untraded_death_rate",
            "secondary_metrics": [],
            "guardrail_metrics": [],
            "baseline_value": 0.8,
            "target_direction": "lower_is_better",
            "target_value": 0.7,
            "target_delta": -0.1,
            "minimum_future_matches": 3,
            "maximum_future_matches": 5,
            "success_definition": "Lower supported rate.",
            "failure_or_regression_definition": "Rate does not improve.",
            "per_match_feedback_template": "Report supported rate.",
        }
        proposal = CoachMissionProposal(
            owner_user_id=owner.id,
            owner_steam_id=account.steam_id,
            domain_key=domain,
            analysis_id=analysis.id,
            baseline_id=baseline.id,
            proposal_hash=str(index + 6) * 64,
            payload_json=json.dumps(payload),
            provenance_json="{}",
            is_current=True,
        )
        db.add(proposal)
        db.flush()
        slot = CoachDomainSlot(
            owner_user_id=owner.id,
            owner_steam_id=account.steam_id,
            domain_key=domain,
            status="proposal_ready",
            baseline_id=baseline.id,
            current_analysis_id=analysis.id,
            current_proposal_id=proposal.id,
            state_json="{}",
        )
        db.add(slot)
        db.flush()
        created.append(proposal)

    first = activate_domain_proposal(db, owner_user_id=owner.id, proposal_id=created[0].id)
    second = activate_domain_proposal(db, owner_user_id=owner.id, proposal_id=created[1].id)
    repeated = activate_domain_proposal(db, owner_user_id=owner.id, proposal_id=created[0].id)

    assert first["reused"] is False and second["reused"] is False
    assert repeated["reused"] is True and repeated["mission"].id == first["mission"].id
    missions = list_active_coach_missions(db, user_id=owner.id, owner_steam_id=account.steam_id)
    assert len(missions) == 2
    assert {mission_domain_key(mission) for mission in missions} == {
        "impact_leak",
        "bad_fight_selection",
    }
    slots = db.scalars(select(CoachDomainSlot).where(CoachDomainSlot.owner_user_id == owner.id)).all()
    assert {slot.status for slot in slots} == {"active"}
    payload = coach_domain_slots_payload(db, owner_user_id=owner.id, include_provenance=True)
    assert [card["domain"]["key"] for card in payload["cards"]] == [
        "impact_leak",
        "bad_fight_selection",
    ]
    assert all(card["state"] == "active" for card in payload["cards"])
    assert all(card["analysis_summary"] and card["evidence"] for card in payload["cards"])
    assert all(card["proposal"] and card["mission_lifecycle"] for card in payload["cards"])
    assert all(card["progress_history_summary"]["evaluation_count"] == 0 for card in payload["cards"])
    json.dumps(payload)
