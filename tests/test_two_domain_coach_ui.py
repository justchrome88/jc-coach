from __future__ import annotations

import json
import re
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.models import (
    AIDomainAnalysis,
    CoachDomainSlot,
    CoachEvidenceBaseline,
    CoachMission,
    CoachMissionProposal,
    Match,
    SteamAccount,
    User,
)
from app.db.session import SessionLocal
from app.main import app
from app.services.missions.payloads import mission_domain_key
from app.services.owner.auth import hash_password, owner_user
from app.services.owner.coach_ui import (
    compose_coach_workspace_from_payload,
    compose_match_feedback,
)

DOMAINS = ("impact_leak", "bad_fight_selection")


def _csrf_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def _register_owner(client: TestClient) -> int:
    page = client.get("/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": _csrf_from(page),
            "display_name": "Owner",
            "email": "owner@example.test",
            "password": "strong-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    with SessionLocal() as db:
        owner = owner_user(db)
        assert owner is not None
        return owner.id


def _seed_two_proposals(owner_id: int) -> dict[str, int]:
    with SessionLocal() as db:
        owner = db.get(User, owner_id)
        assert owner is not None
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
        ids = {}
        for index, domain in enumerate(DOMAINS, start=1):
            output = {
                "analysis_status": "supported_hypothesis",
                "domain_key": domain,
                "headline": f"Distinct headline {domain}",
                "hypothesis": f"Distinct diagnosis {domain}",
                "reasoning_summary": "Persisted evidence only.",
                "primary_pattern": f"Distinct pattern {domain}",
                "recommended_focus": f"Distinct focus {domain}",
                "confidence": "medium",
                "confidence_rationale": "Thirty eligible matches.",
                "caveats": ["No spatial claim."],
                "evidence_refs": ["aggregate:untraded_death_rate"],
                "counterevidence_refs": [],
                "metric_refs": [
                    {
                        "metric_key": "untraded_death_rate",
                        "value": 0.8,
                        "evidence_ref": "aggregate:untraded_death_rate",
                    }
                ],
                "match_refs": [1, 2],
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
            proposal = CoachMissionProposal(
                owner_user_id=owner.id,
                owner_steam_id=account.steam_id,
                domain_key=domain,
                analysis_id=analysis.id,
                baseline_id=baseline.id,
                proposal_hash=str(index + 6) * 64,
                payload_json=json.dumps(_proposal_payload(domain)),
                provenance_json="{}",
                is_current=True,
            )
            db.add(proposal)
            db.flush()
            db.add(
                CoachDomainSlot(
                    owner_user_id=owner.id,
                    owner_steam_id=account.steam_id,
                    domain_key=domain,
                    status="proposal_ready",
                    baseline_id=baseline.id,
                    current_analysis_id=analysis.id,
                    current_proposal_id=proposal.id,
                    state_json="{}",
                )
            )
            ids[domain] = proposal.id
        db.commit()
        return ids


def _proposal_payload(domain: str) -> dict:
    return {
        "title": f"Mission {domain}",
        "goal": "Improve the supported rate.",
        "behavioral_focus": f"Distinct focus {domain}",
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


def _mission_domains(owner_id: int) -> list[str]:
    with SessionLocal() as db:
        missions = db.query(CoachMission).filter_by(user_id=owner_id, status="active").all()
        return [mission_domain_key(mission) for mission in missions]


def test_coach_activation_supports_neither_one_both_and_double_submit() -> None:
    with TestClient(app) as client:
        owner_id = _register_owner(client)
        proposal_ids = _seed_two_proposals(owner_id)

        first_page = client.get("/coach")
        second_page = client.get("/coach")
        assert first_page.status_code == second_page.status_code == 200
        assert first_page.text.count('class="panel coach-domain-card') == 2
        assert first_page.text.count("Активировать миссию") == 2
        assert _mission_domains(owner_id) == []

        csrf = _csrf_from(first_page)
        impact = client.post(
            "/coach/domains/impact_leak/activate",
            data={"csrf_token": csrf, "proposal_id": proposal_ids["impact_leak"]},
            follow_redirects=False,
        )
        assert impact.status_code == 303
        assert _mission_domains(owner_id) == ["impact_leak"]

        repeated = client.post(
            "/coach/domains/impact_leak/activate",
            data={"csrf_token": csrf, "proposal_id": proposal_ids["impact_leak"]},
            follow_redirects=False,
        )
        assert repeated.status_code == 303
        assert "activation_reused" in repeated.headers["location"]
        assert _mission_domains(owner_id) == ["impact_leak"]

        second = client.post(
            "/coach/domains/bad_fight_selection/activate",
            data={"csrf_token": csrf, "proposal_id": proposal_ids["bad_fight_selection"]},
            follow_redirects=False,
        )
        assert second.status_code == 303
        assert set(_mission_domains(owner_id)) == set(DOMAINS)


def test_can_activate_only_bad_fight_selection_in_fresh_fixture() -> None:
    with TestClient(app) as client:
        owner_id = _register_owner(client)
        proposal_ids = _seed_two_proposals(owner_id)
        page = client.get("/coach")

        response = client.post(
            "/coach/domains/bad_fight_selection/activate",
            data={
                "csrf_token": _csrf_from(page),
                "proposal_id": proposal_ids["bad_fight_selection"],
            },
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert _mission_domains(owner_id) == ["bad_fight_selection"]


def test_dashboard_has_concise_two_domain_summary() -> None:
    with TestClient(app) as client:
        owner_id = _register_owner(client)
        _seed_two_proposals(owner_id)
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert response.text.count('class="dashboard-domain-list"') == 1
    assert "Impact Leak" in response.text
    assert "Bad Fight Selection" in response.text
    assert "Доказательства и контрдоказательства" not in response.text


def test_unauthenticated_activation_is_denied_without_mutation() -> None:
    with TestClient(app, follow_redirects=False) as client:
        login_page = client.get("/login")
        response = client.post(
            "/coach/domains/impact_leak/activate",
            data={"csrf_token": _csrf_from(login_page), "proposal_id": 1},
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    with SessionLocal() as db:
        assert db.query(CoachMission).count() == 0


def test_activation_fails_closed_for_csrf_domain_stale_and_cross_owner() -> None:
    with TestClient(app) as client:
        owner_id = _register_owner(client)
        proposal_ids = _seed_two_proposals(owner_id)
        page = client.get("/coach")
        csrf = _csrf_from(page)

        missing_csrf = client.post(
            "/coach/domains/impact_leak/activate",
            data={"proposal_id": proposal_ids["impact_leak"]},
            follow_redirects=False,
        )
        assert missing_csrf.status_code == 403

        mismatch = client.post(
            "/coach/domains/bad_fight_selection/activate",
            data={"csrf_token": csrf, "proposal_id": proposal_ids["impact_leak"]},
            follow_redirects=False,
        )
        assert mismatch.status_code == 303
        assert "activation_unavailable" in mismatch.headers["location"]
        assert _mission_domains(owner_id) == []

        with SessionLocal() as db:
            impact = db.get(CoachMissionProposal, proposal_ids["impact_leak"])
            assert impact is not None
            impact.is_current = False
            other = User(
                email="other@example.test",
                password_hash=hash_password("strong-password"),
                display_name="Other",
                is_active=1,
            )
            db.add(other)
            db.flush()
            foreign_analysis = AIDomainAnalysis(
                owner_user_id=other.id,
                owner_steam_id="76561198000000999",
                domain_key="impact_leak",
                baseline_id=impact.baseline_id,
                baseline_hash="c" * 64,
                idempotency_key="a" * 64,
                attempt_number=1,
                prompt_version="two-domain-hypothesis-v1",
                prompt_hash="q" * 64,
                evidence_schema_version="coach-domain-evidence-v1",
                evidence_hash="d" * 64,
                provider="fixture",
                model="fixture",
                routing_json="{}",
                settings_json="{}",
                structured_output_json="{}",
                validation_status="accepted",
                validation_errors_json="[]",
            )
            db.add(foreign_analysis)
            db.flush()
            foreign = CoachMissionProposal(
                owner_user_id=other.id,
                owner_steam_id="76561198000000999",
                domain_key="impact_leak",
                analysis_id=foreign_analysis.id,
                baseline_id=impact.baseline_id,
                proposal_hash="f" * 64,
                payload_json=impact.payload_json,
                provenance_json="{}",
                is_current=True,
            )
            db.add(foreign)
            db.commit()
            foreign_id = foreign.id

        stale = client.post(
            "/coach/domains/impact_leak/activate",
            data={"csrf_token": csrf, "proposal_id": proposal_ids["impact_leak"]},
            follow_redirects=False,
        )
        foreign = client.post(
            "/coach/domains/impact_leak/activate",
            data={"csrf_token": csrf, "proposal_id": foreign_id},
            follow_redirects=False,
        )
        assert "activation_unavailable" in stale.headers["location"]
        assert "activation_denied" in foreign.headers["location"]
        assert _mission_domains(owner_id) == []


@pytest.mark.parametrize(
    ("backend_state", "analysis_status", "expected_state", "activation"),
    [
        ("insufficient_baseline", None, "insufficient_baseline", False),
        ("analyzing", None, "analyzing", False),
        ("proposal_ready", "supported_hypothesis", "proposal_ready", True),
        ("no_material_problem", "no_material_problem", "no_material_problem", False),
        ("analysis_failed", "insufficient_evidence", "not_enough_data", False),
        ("analysis_failed", None, "analysis_failed", False),
        ("proposal_superseded", "supported_hypothesis", "stale_or_superseded", False),
        ("paused", "supported_hypothesis", "paused", False),
        ("completed", "supported_hypothesis", "completed", False),
        ("unknown_state", None, "unavailable", False),
    ],
)
def test_all_reachable_card_states_have_explicit_safe_presentations(
    backend_state: str,
    analysis_status: str | None,
    expected_state: str,
    activation: bool,
) -> None:
    payload = _two_card_payload(
        backend_state=backend_state,
        analysis_status=analysis_status,
        activation=activation,
    )
    workspace = compose_coach_workspace_from_payload(payload, locale="ru")

    assert workspace["card_count"] == 2
    assert workspace["domain_order"] == list(DOMAINS)
    assert all(card["presentation_state"] == expected_state for card in workspace["cards"])
    assert all(bool(card["state_label"]) and "." not in card["state_label"] for card in workspace["cards"])
    assert all(card["activation"]["allowed"] is activation for card in workspace["cards"])


def test_active_and_insufficient_progress_are_distinct_and_match_feedback_is_post_activation_only() -> None:
    payload = _two_card_payload(backend_state="active", analysis_status="supported_hypothesis", activation=False)
    first = payload["cards"][0]
    first["mission_lifecycle"] = {
        "mission_id": 11,
        "status": "active",
        "title": "Impact mission",
        "focus": "Tradeable deaths",
        "activated_at": "2026-07-11T10:00:00",
        "source_payload": {"activation_baseline": {"match_ids": [1]}},
    }
    first["progress_history"] = [
        {
            "evaluation_id": 21,
            "status": "insufficient_data",
            "confidence": 0.25,
            "caveats": ["low_sample_caveat"],
            "evaluated_window": {"match_ids": [2], "sample_matches": 1},
            "primary_metric_result": {
                "metric_name": "untraded_death_rate",
                "baseline_value": 0.8,
                "evaluation_value": 0.75,
                "target_value": 0.7,
                "sample_matches": 1,
                "reason_codes": ["insufficient_sample_matches"],
            },
            "counted": False,
            "progress_explanation": "Insufficient accepted sample.",
        }
    ]
    workspace = compose_coach_workspace_from_payload(payload, locale="ru")

    assert workspace["cards"][0]["presentation_state"] == "active"
    assert workspace["cards"][0]["progress"]["status"] == "insufficient_data"
    assert workspace["cards"][0]["progress"]["sample_matches"] == 1
    assert "percentage" not in json.dumps(workspace)

    baseline_feedback = compose_match_feedback(workspace, match_id=1)["cards"][0]
    future_feedback = compose_match_feedback(workspace, match_id=2)["cards"][0]
    assert baseline_feedback["status"] == "pre_activation"
    assert baseline_feedback["included_in_progress_window"] is False
    assert future_feedback["status"] == "insufficient_data"
    assert future_feedback["included_in_progress_window"] is True
    assert future_feedback["sample_matches"] == 1
    assert future_feedback["minimum_matches"] == 3


def test_counted_progress_shows_direction_without_fake_percentage() -> None:
    payload = _two_card_payload(backend_state="active", analysis_status="supported_hypothesis", activation=False)
    first = payload["cards"][0]
    first["mission_lifecycle"] = {
        "mission_id": 12,
        "status": "active",
        "title": "Impact mission",
        "focus": "Tradeable deaths",
        "activated_at": "2026-07-11T10:00:00",
        "source_payload": {"activation_baseline": {"match_ids": [1]}},
    }
    first["progress_history"] = [
        {
            "evaluation_id": 22,
            "status": "improving",
            "confidence": 0.8,
            "caveats": [],
            "evaluated_window": {"match_ids": [2, 3, 4], "sample_matches": 3},
            "primary_metric_result": {
                "metric_name": "untraded_death_rate",
                "baseline_value": 0.8,
                "evaluation_value": 0.68,
                "target_value": 0.7,
                "sample_matches": 3,
                "reason_codes": [],
            },
            "counted": True,
            "progress_explanation": "Improving on the assigned focus.",
        }
    ]

    workspace = compose_coach_workspace_from_payload(payload, locale="ru")
    card = workspace["cards"][0]
    feedback = compose_match_feedback(workspace, match_id=4)["cards"][0]

    assert card["progress"]["status"] == "improving"
    assert card["metrics"] == {
        "name": "untraded_death_rate",
        "baseline": 0.8,
        "current": 0.68,
        "target": 0.7,
        "target_delta": -0.1,
        "direction": "lower_is_better",
    }
    assert feedback["included_in_progress_window"] is True
    assert feedback["target_result_counted"] is True
    assert "percentage" not in json.dumps(card)


def test_match_detail_denies_cross_owner_and_escapes_coach_text() -> None:
    with TestClient(app) as client:
        owner_id = _register_owner(client)
        _seed_two_proposals(owner_id)
        with SessionLocal() as db:
            analysis = db.query(AIDomainAnalysis).filter_by(owner_user_id=owner_id).first()
            assert analysis is not None
            output = json.loads(analysis.structured_output_json)
            output["headline"] = "<script>alert('unsafe')</script>"
            analysis.structured_output_json = json.dumps(output)
            own = Match(user_id=owner_id, source="test", external_match_id="own")
            other_user = User(display_name="Other")
            db.add(other_user)
            db.flush()
            foreign = Match(user_id=other_user.id, source="test", external_match_id="foreign")
            db.add_all([own, foreign])
            db.commit()
            own_id, foreign_id = own.id, foreign.id

        coach_page = client.get("/coach")
        own_page = client.get(f"/matches/{own_id}")
        foreign_page = client.get(f"/matches/{foreign_id}", follow_redirects=False)

    assert "&lt;script&gt;" in coach_page.text
    assert "<script>alert" not in coach_page.text
    assert "/opt/" not in coach_page.text
    assert "SESSION_SECRET" not in coach_page.text
    assert own_page.status_code == 200
    assert own_page.text.count('class="feedback-card"') == 2
    assert foreign_page.status_code == 303
    assert foreign_page.headers["location"] == "/matches"


def _two_card_payload(*, backend_state: str, analysis_status: str | None, activation: bool) -> dict:
    cards = []
    for index, domain in enumerate(DOMAINS, start=1):
        proposal = (
            _proposal_payload(domain)
            if activation or backend_state in {"active", "proposal_superseded"}
            else None
        )
        proposal_ref = (
            {
                "id": index,
                "domain_key": domain,
                "is_current": backend_state != "proposal_superseded",
            }
            if proposal
            else None
        )
        cards.append(
            {
                "domain": {"key": domain},
                "state": backend_state,
                "slot_status": backend_state,
                "analysis_summary": {"status": analysis_status} if analysis_status else None,
                "proposal": proposal,
                "proposal_ref": proposal_ref,
                "activation_eligibility": activation,
                "confidence": "medium" if analysis_status else None,
                "caveats": [],
                "progress_history": [],
            }
        )
    return {"schema_version": "coach-domain-slots-v1", "cards": cards}
