import json
from datetime import datetime, timedelta
from pathlib import Path

from app.db.models import AnalysisRun, CoachHypothesis, CoachMission, Match, MetricSnapshot, User
from app.services.coach_domain_model import (
    CANONICAL_COACH_DOMAINS,
    METRIC_GROUPS,
    canonical_domain_for_family,
    canonicalize_domain_key,
)
from app.services.mission_domain import (
    generate_rolling_mission_candidates,
    persist_rolling_mission_candidates,
    reconcile_noncanonical_active_missions,
    serialize_coach_mission,
)


def test_machine_model_matches_runtime_canonical_domains():
    model = json.loads(Path("docs/coach/coach-domain-model.json").read_text(encoding="utf-8"))
    assert tuple(item["key"] for item in model["coach_domains"]) == CANONICAL_COACH_DOMAINS
    assert tuple(model["metric_groups"]) == METRIC_GROUPS
    assert model["active_mission_model"] == "at_most_one_globally_per_owner"


def test_family_mapping_is_explicit_and_utility_fails_closed():
    assert canonical_domain_for_family("impact_leak") == "impact_leak"
    assert canonical_domain_for_family("survival_opening") == "bad_fight_selection"
    assert canonical_domain_for_family("bad_fight_trade") == "bad_fight_selection"
    assert canonical_domain_for_family("utility_value") is None
    assert canonicalize_domain_key("performance") is None
    assert canonicalize_domain_key("utility") is None
    assert canonicalize_domain_key("aim") is None


def test_impact_leak_has_positive_negative_and_insufficient_fixtures(db):
    owner = User(display_name="canonical-impact-owner")
    db.add(owner)
    db.flush()
    steam_id = "76561198000000401"

    positive_ids = _impact_fixture(
        db,
        owner_id=owner.id,
        steam_id=steam_id,
        prefix="positive",
        results=["loss", "draw", "loss", "win", "win"],
        adrs=[100, 95, 88, 92, 90],
    )
    positive = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=steam_id,
        window_type="custom_match_set",
        match_ids=positive_ids,
    )
    assert positive["diagnostics"]["impact_leak"]["claim_supported"] is True
    assert any(candidate["family"] == "impact_leak" for candidate in positive["candidates"])

    negative_ids = _impact_fixture(
        db,
        owner_id=owner.id,
        steam_id=steam_id,
        prefix="negative",
        results=["win"] * 5,
        adrs=[100, 95, 88, 92, 90],
        day_offset=10,
    )
    negative = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=steam_id,
        window_type="custom_match_set",
        match_ids=negative_ids,
    )
    assert negative["diagnostics"]["impact_leak"]["claim_supported"] is False
    assert "outcome_conversion_leak_not_detected" in negative["diagnostics"]["impact_leak"]["reason_codes"]

    insufficient = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=steam_id,
        window_type="custom_match_set",
        match_ids=positive_ids[:4],
    )
    assert insufficient["diagnostics"]["impact_leak"]["claim_supported"] is False
    assert "insufficient_supported_matches" in insufficient["diagnostics"]["impact_leak"]["reason_codes"]


def test_utility_value_trend_is_context_only_and_never_a_candidate(db):
    owner = User(display_name="canonical-utility-owner")
    db.add(owner)
    db.flush()
    steam_id = "76561198000000402"
    match_ids = []
    for index, value in enumerate([*[50] * 5, *[40] * 5], start=1):
        match = Match(
            user_id=owner.id,
            source="test",
            external_match_id=f"utility-context-{index}",
            played_at=datetime(2026, 1, 1) + timedelta(days=index),
            result="loss",
            rounds_for=8,
            rounds_against=13,
        )
        db.add(match)
        db.flush()
        match_ids.append(match.id)
        _snapshot(
            db,
            owner_id=owner.id,
            match_id=match.id,
            steam_id=steam_id,
            source="coach_metric_utility",
            metrics={"effective_enemy_utility_damage": value},
        )
    result = generate_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=steam_id,
        window_type="custom_match_set",
        match_ids=match_ids,
    )
    diagnostic = result["diagnostics"]["effective_enemy_utility_damage"]
    assert diagnostic["deficiency_detected"] is True
    assert diagnostic["classification"] == "context-only"
    assert diagnostic["mission_eligible"] is False
    assert all(candidate["family"] != "utility_value" for candidate in result["candidates"])


def test_canonical_hypothesis_persistence_reuses_stable_window_identity(db):
    owner = User(display_name="canonical-idempotency-owner")
    db.add(owner)
    db.flush()
    steam_id = "76561198000000404"
    match_ids = _impact_fixture(
        db,
        owner_id=owner.id,
        steam_id=steam_id,
        prefix="idempotent",
        results=["loss", "draw", "loss", "win", "win"],
        adrs=[100, 95, 88, 92, 90],
    )
    first = persist_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=steam_id,
        window_type="custom_match_set",
        match_ids=match_ids,
    )
    second = persist_rolling_mission_candidates(
        db,
        user_id=owner.id,
        owner_steam_id=steam_id,
        window_type="custom_match_set",
        match_ids=match_ids,
    )
    assert first["analysis_run_id"] == second["analysis_run_id"]
    assert first["coach_hypothesis_ids"] == second["coach_hypothesis_ids"]
    assert second["idempotency"] == {"reused_analysis_run": True, "created_hypothesis_ids": []}
    assert db.query(AnalysisRun).count() == 1
    assert db.query(CoachHypothesis).count() == len(first["coach_hypothesis_ids"])


def test_noncanonical_mission_is_cancelled_without_rewriting_historical_payload(db):
    owner = User(display_name="canonical-mission-owner")
    db.add(owner)
    db.flush()
    steam_id = "76561198000000403"
    historical_payload = {
        "mission_domain_key": "utility_value",
        "problem_key": "utility_value",
        "mission_payload": {"historical": True, "success_metric": {"metric_name": "utility_damage"}},
    }
    mission = CoachMission(
        user_id=owner.id,
        owner_steam_id=steam_id,
        status="active",
        title="Historical utility mission",
        focus="Recover utility damage",
        source_payload_json=json.dumps(historical_payload),
    )
    db.add(mission)
    db.flush()

    result = reconcile_noncanonical_active_missions(
        db,
        user_id=owner.id,
        owner_steam_id=steam_id,
        apply=True,
    )
    db.flush()

    payload = json.loads(mission.source_payload_json)
    serialized = serialize_coach_mission(mission)
    assert result["decisions"][0]["reason"] == "noncanonical_domain_reconciliation"
    assert mission.status == "cancelled"
    assert payload["mission_payload"] == historical_payload["mission_payload"]
    assert payload["canonical_domain_reconciliation"]["canonical_domain_key"] is None
    assert serialized["domain_key"] is None
    assert serialized["legacy_domain_key"] == "utility_value"


def _impact_fixture(
    db,
    *,
    owner_id: int,
    steam_id: str,
    prefix: str,
    results: list[str],
    adrs: list[int],
    day_offset: int = 0,
) -> list[int]:
    match_ids = []
    for index, (result, adr) in enumerate(zip(results, adrs, strict=True), start=1):
        match = Match(
            user_id=owner_id,
            source="test",
            external_match_id=f"{prefix}-{index}",
            played_at=datetime(2026, 2, 1) + timedelta(days=day_offset + index),
            result=result,
            rounds_for=13 if result == "win" else 8,
            rounds_against=8 if result == "win" else 13,
        )
        db.add(match)
        db.flush()
        match_ids.append(match.id)
        _snapshot(
            db,
            owner_id=owner_id,
            match_id=match.id,
            steam_id=steam_id,
            source="coach_metric_performance",
            metrics={
                "rounds_played": 20,
                "adr": adr,
                "kast": 70,
                "deaths": 14,
                "survival_rate": 0.4,
                "kills_per_round": 0.8,
                "opening_death_rate": 0.1,
                "untraded_death_rate": 0.4,
            },
        )
    return match_ids


def _snapshot(
    db,
    *,
    owner_id: int,
    match_id: int,
    steam_id: str,
    source: str,
    metrics: dict,
) -> None:
    confidence = {
        "metrics": {
            metric: {
                "level": "high",
                "usable_for_insights": True,
                "usable_for_missions": True,
                "hard_recommendation_eligible": True,
            }
            for metric in metrics
        }
    }
    db.add(
        MetricSnapshot(
            owner_user_id=owner_id,
            match_id=match_id,
            player_key=f"steam:{steam_id}",
            player_steamid=steam_id,
            source=source,
            metric_domain="coach_utility" if source == "coach_metric_utility" else "coach_performance",
            semantic_version="3.0.0",
            validation_status="validated",
            source_event_set_id=f"canonical-fixture:{match_id}:{source}",
            metrics_json=json.dumps(metrics),
            confidence_baseline_json=json.dumps(confidence),
            caveats_json="[]",
            metadata_json="{}",
        )
    )
    db.flush()
