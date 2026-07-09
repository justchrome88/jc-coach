import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api import routes as api_routes
from app.db.models import AnalysisRun, CoachHypothesis, CoachReport, Match, SteamAccount, User
from app.services.ai_coach import (
    AI_COACH_DOMAIN_CONTRACT_VERSION,
    AI_COACH_PAYLOAD_SCHEMA_VERSION,
    AI_COACH_PROMPT_VERSION,
    AI_COACH_SNAPSHOT_CONTRACT_VERSION,
    AI_COACH_SNAPSHOT_GENERATED_BY,
    CodexCliHandoffProvider,
    LocalLLMProvider,
    ai_provider_health,
    build_ai_coach_payload,
    build_ai_coach_prompt,
    latest_ai_coach_report,
    list_ai_coach_reports,
    persist_owner_scoped_coach_hypotheses,
    process_owner_match_metric_snapshots_for_coach_loop,
    save_ai_coach_result,
    serialize_ai_coach_report,
)
from app.services.coach_insights import validate_insight_cards
from app.services.demo_retention import ARTIFACT_CATEGORY_COACH_OUTPUT, RETENTION_CLASS_FINAL_OUTPUT
from app.services.importer import import_rows
from app.services.metric_snapshots import (
    MetricSnapshotAnalysisScope,
    admin_debug_all_metric_snapshots_scope,
    create_metric_snapshot,
)
from app.services.metric_truth import METRIC_REGISTRY_VERSION
from app.services.mission_domain import (
    activate_draft_coach_mission,
    create_draft_coach_mission,
    list_mission_progress_evaluations,
)


def test_build_ai_coach_payload_uses_structured_match_data(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    payload = build_ai_coach_payload(db, analysis_scope=admin_debug_all_metric_snapshots_scope())

    assert payload["product"] == "CS2 Personal Coach"
    assert payload["summary"]["matches_count"] == 2
    assert payload["rules"]["do_not_invent_facts"] is True
    assert len(payload["recent_matches"]) == 2
    assert payload["metric_confidence"]["metrics"]["grenade_rating"]["level"] == "unavailable"
    assert payload["metric_confidence"]["metrics"]["traded_deaths"]["level"] == "unavailable"


def test_ai_coach_payload_includes_deterministic_contract_snapshot(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    first = build_ai_coach_payload(db)
    second = build_ai_coach_payload(db)

    expected = {
        "ai_coach_prompt_version": AI_COACH_PROMPT_VERSION,
        "ai_coach_payload_schema_version": AI_COACH_PAYLOAD_SCHEMA_VERSION,
        "metric_registry_version": METRIC_REGISTRY_VERSION,
        "snapshot_generated_by": AI_COACH_SNAPSHOT_GENERATED_BY,
        "snapshot_contract_version": AI_COACH_SNAPSHOT_CONTRACT_VERSION,
    }
    assert first["contract_snapshot"] == expected
    assert second["contract_snapshot"] == expected
    assert first["contract_snapshot"] == second["contract_snapshot"]
    assert first["metric_truth"]["metric_registry_version"] == METRIC_REGISTRY_VERSION


def test_ai_coach_payload_includes_deterministic_domain_constraints(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    first = build_ai_coach_payload(db)
    second = build_ai_coach_payload(db)

    assert first["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert first["domain_contract_version"] == second["domain_contract_version"]
    assert first["domain_constraints"] == second["domain_constraints"]
    assert first["claim_guardrails"] == second["claim_guardrails"]
    assert first["metric_confidence_policy"] == second["metric_confidence_policy"]
    assert first["playlist_mode_policy"] == second["playlist_mode_policy"]
    assert first["recommendation_policy"] == second["recommendation_policy"]
    assert first["public_readiness_policy"] == second["public_readiness_policy"]

    assert first["domain_constraints"]["accepted_active_hard_recommendation_id"] == 5
    assert first["recommendation_policy"]["current_accepted_active_hard_recommendation_id"] == 5
    assert first["recommendation_policy"]["legacy_recommendations_not_for_new_hard_evaluations"] == [1, 3, 4]
    assert first["domain_constraints"]["steam_import_max_demos_per_run"] == 1
    assert first["domain_constraints"]["v1_0_claim_allowed"] is False
    assert first["public_readiness_policy"]["public_readiness"] == "blocked"
    assert first["public_readiness_policy"]["friends_readiness"] == "blocked"
    assert first["public_readiness_policy"]["public_or_friends_claim_allowed"] is False


def test_ai_coach_prompt_carries_contract_snapshot_without_removing_caveats(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    payload = build_ai_coach_payload(db, analysis_scope=admin_debug_all_metric_snapshots_scope())
    prompt = build_ai_coach_prompt(payload)
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)

    assert AI_COACH_PROMPT_VERSION in prompt
    assert METRIC_REGISTRY_VERSION in prompt
    assert AI_COACH_DOMAIN_CONTRACT_VERSION in prompt
    assert "domain_constraints" in prompt
    assert "claim_guardrails" in prompt
    assert payload["metric_confidence_policy"]["weak_metrics_must_remain_caveated"] is True
    assert payload["metric_confidence_policy"]["missing_metric_confidence_blocks_hard_advice"] is True
    assert "crosshair_placement" in payload["metric_truth"]["suppressed_for_diagnosis"]
    assert "crosshair_placement" in payload["metric_truth"]["suppressed_for_recommendation"]
    assert payload["metric_confidence"]["metrics"]["crosshair_placement"]["level"] == "unavailable"
    assert "trade_kills" in payload["metric_truth"]["suppressed_for_recommendation"]
    assert payload["playlist_mode_policy"]["mode_status"] == "unknown_or_provenance_only"
    assert payload["playlist_mode_policy"]["source_labels_are_provenance_not_playlist"] is True
    for unsupported_mode in ("Premier", "Competitive", "Wingman", "Casual", "Deathmatch", "FACEIT"):
        assert unsupported_mode in payload["playlist_mode_policy"]["unsupported_exact_playlist_claims"]
        assert f'"accepted_playlist": "{unsupported_mode}"' not in payload_json
    assert '"v1_0_claim_allowed": true' not in payload_json
    assert '"public_or_friends_claim_allowed": true' not in payload_json


def test_ai_coach_payload_includes_deterministic_bad_fight_trade_insight_cards(db):
    match = Match(source="demo", external_match_id="trade-insight-ai")
    db.add(match)
    db.commit()
    db.refresh(match)
    create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:76561198000000001",
        player_name="Alpha",
        player_steamid="76561198000000001",
        source="core_combat_metrics",
        source_event_set_id="fixture:e03",
        metrics={
            "rounds": 10,
            "opening_deaths": 3,
            "opening_death_rate": 0.3,
            "untraded_deaths": 3,
            "trade_status_known_deaths": 4,
            "untraded_death_rate": 0.75,
        },
        confidence_baseline={
            "source": "core-combat-metrics-v1",
            "metrics": {
                "opening_death_rate": {"level": "high"},
                "untraded_death_rate": {"level": "high"},
            },
        },
        caveats=[],
        metadata={"schema_version": "core-combat-metrics-v1"},
    )

    payload = build_ai_coach_payload(db, analysis_scope=admin_debug_all_metric_snapshots_scope())

    assert payload["coach_insight_cards"][0]["problem"] == (
        "Untraded deaths show bad fight selection or poor trade spacing in this match snapshot."
    )
    assert payload["coach_insight_cards"][0]["evidence"][0]["metric_id"] == "untraded_death_rate"
    assert payload["coach_insight_cards"][0]["evidence"][0]["sample_count"] == 4
    assert payload["coach_insight_cards"][0]["confidence"] == "high"


def test_ai_coach_payload_includes_deterministic_utility_value_insight_cards(db):
    match = Match(source="demo", external_match_id="utility-insight-ai")
    db.add(match)
    db.commit()
    db.refresh(match)
    create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:76561198000000001",
        player_name="Alpha",
        player_steamid="76561198000000001",
        source="utility_metrics",
        source_event_set_id="fixture:c05:utility",
        metrics={"utility_damage": 49, "he_damage": 42, "molotov_damage": 7, "enemies_flashed": 1},
        confidence_baseline={
            "source": "utility-metrics-v1",
            "metrics": {
                "utility_damage": {"level": "medium", "usable_for_insights": True},
                "enemies_flashed": {"level": "low", "usable_for_insights": False},
                "grenade_rating": {"level": "unavailable", "usable_for_insights": False},
            },
            "event_coverage": {"utility_damage_events": 2},
        },
        caveats=["Utility damage is inferred from parser weapon name on player_hurt."],
        metadata={"schema_version": "utility-metrics-v1"},
    )

    payload = build_ai_coach_payload(db, analysis_scope=admin_debug_all_metric_snapshots_scope())

    card = payload["coach_insight_cards"][0]
    assert card["problem"] == "Utility damage is the only supported utility value signal in this match snapshot."
    assert card["evidence"][0]["metric_id"] == "utility_damage"
    assert card["evidence"][0]["value"] == 49
    assert card["confidence"] == "medium"
    assert "grenade_rating" not in card["evidence"][0]


def test_ai_coach_payload_defaults_to_owner_player_metric_snapshot_scope(db):
    owner = User(email="owner@example.test", display_name="Owner", password_hash="hash")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    db.add(
        SteamAccount(
            user_id=owner.id,
            steam_id="owner-steam",
            persona_name="JC",
        )
    )
    match = Match(source="demo", external_match_id="owner-scope-ai")
    db.add(match)
    db.commit()
    db.refresh(match)
    owner_snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:owner-steam",
        player_name="JC",
        player_steamid="owner-steam",
        source="utility_metrics",
        source_event_set_id="fixture:owner:utility",
        metrics={"utility_damage": 94, "molotov_damage": 93},
        confidence_baseline={
            "source": "utility-metrics-v1",
            "metrics": {
                "utility_damage": {
                    "level": "medium",
                    "usable_for_insights": True,
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                }
            },
        },
        metadata={"schema_version": "utility-metrics-v1"},
    )
    other_snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:other",
        player_name="Other",
        player_steamid="other",
        source="core_combat_metrics",
        source_event_set_id="fixture:other:core",
        metrics={
            "rounds": 14,
            "opening_deaths": 5,
            "opening_death_rate": 0.357,
            "survived_rounds": 0,
            "survival_rate": 0.0,
        },
        confidence_baseline={
            "source": "core-combat-metrics-v1",
            "metrics": {
                "opening_death_rate": {"level": "high"},
                "survival_rate": {"level": "high"},
            },
        },
        metadata={"schema_version": "core-combat-metrics-v1"},
    )

    payload = build_ai_coach_payload(db)

    assert payload["analysis_scope"]["mode"] == "personal"
    assert payload["analysis_scope"]["owner_steam_id"] == "owner-steam"
    assert payload["analysis_scope"]["resolved_metric_snapshot_ids"] == [owner_snapshot.id]
    assert other_snapshot.id not in payload["analysis_scope"]["resolved_metric_snapshot_ids"]
    assert [card["evidence"][0]["metric_id"] for card in payload["coach_insight_cards"]] == ["utility_damage"]
    assert validate_insight_cards(payload["coach_insight_cards"]) == ()
    assert payload["coach_insight_cards"][0]["mission_readiness"]["can_become_mission"] is True


def test_api_personal_payload_and_saved_report_exclude_non_owner_metric_snapshots(db):
    owner = User(email="api-owner@example.test", display_name="Owner", password_hash="hash")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    db.add(SteamAccount(user_id=owner.id, steam_id="api-owner-steam", persona_name="JC"))
    match = Match(source="demo", external_match_id="api-owner-scope")
    db.add(match)
    db.commit()
    db.refresh(match)
    owner_snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:api-owner-steam",
        player_name="JC",
        player_steamid="api-owner-steam",
        source="utility_metrics",
        source_event_set_id="fixture:api-owner:utility",
        metrics={"utility_damage": 88, "he_damage": 88},
        confidence_baseline={
            "source": "utility-metrics-v1",
            "metrics": {
                "utility_damage": {
                    "level": "medium",
                    "usable_for_insights": True,
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                }
            },
        },
        metadata={"schema_version": "utility-metrics-v1"},
    )
    other_snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:other-player",
        player_name="Other",
        player_steamid="other-player",
        source="core_combat_metrics",
        source_event_set_id="fixture:api-other:core",
        metrics={
            "rounds": 12,
            "opening_deaths": 5,
            "opening_death_rate": 0.417,
            "survived_rounds": 1,
            "survival_rate": 0.083,
        },
        confidence_baseline={
            "source": "core-combat-metrics-v1",
            "metrics": {
                "opening_death_rate": {"level": "high"},
                "survival_rate": {"level": "high"},
            },
        },
        metadata={"schema_version": "core-combat-metrics-v1"},
    )

    payload = api_routes.ai_coach_payload_endpoint(db)
    created = api_routes.save_ai_coach_result_endpoint(
        db,
        report_markdown="# API personal report\n\nUse only scoped owner snapshots.",
        source_ref="api-personal",
    )
    latest = api_routes.latest_ai_coach_result_endpoint(db)

    assert payload["analysis_scope"]["mode"] == "personal"
    assert payload["analysis_scope"]["owner_steam_id"] == "api-owner-steam"
    assert payload["analysis_scope"]["resolved_metric_snapshot_ids"] == [owner_snapshot.id]
    assert other_snapshot.id not in payload["analysis_scope"]["resolved_metric_snapshot_ids"]
    assert [card["evidence"][0]["metric_id"] for card in payload["coach_insight_cards"]] == ["utility_damage"]
    assert validate_insight_cards(payload["coach_insight_cards"]) == ()
    assert created["ok"] is True
    assert latest["metadata"]["analysis_scope"]["mode"] == "personal"
    assert latest["metadata"]["analysis_scope"]["owner_identity"] == {
        "owner_user_id": owner.id,
        "owner_steam_id": "api-owner-steam",
    }
    assert latest["metadata"]["analysis_scope"]["player_identity"]["player_steamid"] == "api-owner-steam"
    assert latest["metadata"]["analysis_scope"]["selected_metric_snapshot_ids"] == [owner_snapshot.id]
    assert other_snapshot.id not in latest["metadata"]["analysis_scope"]["selected_metric_snapshot_ids"]


def test_owner_scoped_scope_prioritizes_jc_snapshot_rows_after_filtering(db):
    match = Match(source="demo", external_match_id="match-76-fixture")
    db.add(match)
    db.commit()
    db.refresh(match)
    jc_core = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:jc",
        player_name="JC",
        player_steamid="jc",
        source="core_combat_metrics",
        source_event_set_id="fixture:jc:core",
        metrics={
            "rounds": 14,
            "opening_deaths": 3,
            "opening_death_rate": 0.214,
            "survived_rounds": 5,
            "survival_rate": 0.357,
        },
        confidence_baseline={
            "source": "core-combat-metrics-v1",
            "metrics": {
                "opening_death_rate": {
                    "level": "medium",
                    "usable_for_insights": False,
                    "usable_for_missions": False,
                    "hard_recommendation_eligible": False,
                    "reason_codes": ["suppressed_metric_blocks_hard_recommendation"],
                },
                "survival_rate": {
                    "level": "medium",
                    "usable_for_insights": True,
                    "usable_for_missions": False,
                    "hard_recommendation_eligible": False,
                    "reason_codes": ["suppressed_metric_blocks_hard_recommendation"],
                },
            },
        },
        metadata={"schema_version": "core-combat-metrics-v1"},
    )
    jc_utility = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:jc",
        player_name="JC",
        player_steamid="jc",
        source="utility_metrics",
        source_event_set_id="fixture:jc:utility",
        metrics={"utility_damage": 94, "molotov_damage": 93},
        confidence_baseline={
            "source": "utility-metrics-v1",
            "metrics": {
                "utility_damage": {
                    "level": "medium",
                    "usable_for_insights": True,
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                }
            },
        },
        metadata={"schema_version": "utility-metrics-v1"},
    )
    other = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:other",
        player_name="Other",
        player_steamid="other",
        source="core_combat_metrics",
        metrics={
            "rounds": 14,
            "opening_deaths": 5,
            "opening_death_rate": 0.357,
            "survived_rounds": 0,
            "survival_rate": 0.0,
        },
        confidence_baseline={
            "source": "core-combat-metrics-v1",
            "metrics": {
                "opening_death_rate": {"level": "high"},
                "survival_rate": {"level": "high"},
            },
        },
    )
    scope = MetricSnapshotAnalysisScope(
        match_ids=(match.id,),
        source="steam",
        owner_steam_id="jc",
        player_key="steam:jc",
        player_steamid="jc",
        selected_metric_snapshot_ids=(jc_core.id, jc_utility.id, other.id),
    )

    payload = build_ai_coach_payload(db, analysis_scope=scope)

    assert payload["analysis_scope"]["resolved_metric_snapshot_ids"] == [jc_utility.id, jc_core.id]
    assert [card["evidence"][0]["metric_id"] for card in payload["coach_insight_cards"]] == [
        "survival_rate",
        "utility_damage",
    ]
    assert payload["coach_insight_cards"][0]["mission_readiness"]["can_become_mission"] is False
    assert "confidence_not_mission_eligible" in payload["coach_insight_cards"][0]["mission_readiness"][
        "blocking_reason_codes"
    ]
    assert payload["coach_insight_cards"][1]["mission_readiness"]["can_become_mission"] is True


def test_persist_owner_scoped_coach_hypotheses_keeps_filtered_snapshot_scope(db):
    owner = User(email="persist-owner@example.test", display_name="Owner", password_hash="hash")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    match = Match(id=76, source="demo", external_match_id="match-76-fixture-persist-owner-scope")
    db.add(match)
    db.commit()
    db.refresh(match)
    owner_snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:persist-owner",
        player_name="JC",
        player_steamid="persist-owner",
        source="utility_metrics",
        source_event_set_id="fixture:persist-owner:utility",
        metrics={"utility_damage": 95, "he_damage": 95},
        confidence_baseline={
            "source": "utility-metrics-v1",
            "metrics": {
                "utility_damage": {
                    "level": "medium",
                    "usable_for_insights": True,
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                }
            },
        },
        metadata={"schema_version": "utility-metrics-v1"},
    )
    other_snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:other",
        player_name="Other",
        player_steamid="other",
        source="core_combat_metrics",
        metrics={
            "rounds": 12,
            "opening_deaths": 5,
            "opening_death_rate": 0.417,
            "survived_rounds": 1,
            "survival_rate": 0.083,
        },
        confidence_baseline={
            "source": "core-combat-metrics-v1",
            "metrics": {
                "opening_death_rate": {"level": "high"},
                "survival_rate": {"level": "high"},
            },
        },
    )
    scope = MetricSnapshotAnalysisScope(
        match_ids=(match.id,),
        source="steam",
        owner_user_id=owner.id,
        owner_steam_id="persist-owner",
        player_key="steam:persist-owner",
        player_steamid="persist-owner",
        selected_metric_snapshot_ids=(owner_snapshot.id, other_snapshot.id),
    )
    payload = build_ai_coach_payload(db, analysis_scope=scope)

    run, hypotheses = persist_owner_scoped_coach_hypotheses(
        db,
        analysis_scope=scope,
        insight_cards=payload["coach_insight_cards"],
        source_payload={"payload_hash": "fixture"},
    )

    assert run.user_id == owner.id
    assert run.owner_steam_id == "persist-owner"
    assert run.source == "ai_coach_owner_scoped_insights"
    assert json.loads(run.selected_metric_snapshot_ids_json) == [owner_snapshot.id]
    persisted_scope = json.loads(run.analysis_scope_json)
    assert persisted_scope["mode"] == "personal"
    assert persisted_scope["source_placeholder"] == "steam"
    assert persisted_scope["window_placeholder"] == "match_set"
    assert persisted_scope["requested_metric_snapshot_ids"] == [owner_snapshot.id, other_snapshot.id]
    assert persisted_scope["selected_metric_snapshot_ids"] == [owner_snapshot.id]
    assert persisted_scope["resolved_metric_snapshot_ids"] == [owner_snapshot.id]
    assert len(hypotheses) == 1
    hypothesis = hypotheses[0]
    assert hypothesis.analysis_run_id == run.id
    assert hypothesis.user_id == owner.id
    assert hypothesis.owner_steam_id == "persist-owner"
    assert hypothesis.confidence == 0.6
    assert json.loads(hypothesis.evidence_json)[0]["metric_id"] == "utility_damage"
    assert json.loads(hypothesis.source_card_json)["confidence"] == "medium"
    assert json.loads(hypothesis.mission_readiness_json)["can_become_mission"] is True
    assert db.query(AnalysisRun).count() == 1
    assert db.query(CoachHypothesis).count() == 1


def test_persist_owner_scoped_coach_hypotheses_rejects_non_owner_card(db):
    owner = User(email="persist-reject@example.test", display_name="Owner", password_hash="hash")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    match = Match(source="demo", external_match_id="persist-non-owner-card")
    db.add(match)
    db.commit()
    db.refresh(match)
    create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:owner",
        player_name="Owner",
        player_steamid="owner",
        source="utility_metrics",
        metrics={"utility_damage": 80},
        confidence_baseline={
            "source": "utility-metrics-v1",
            "metrics": {"utility_damage": {"level": "medium", "usable_for_insights": True}},
        },
    )
    other_snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:other",
        player_name="Other",
        player_steamid="other",
        source="core_combat_metrics",
        metrics={
            "rounds": 12,
            "opening_deaths": 5,
            "opening_death_rate": 0.417,
        },
        confidence_baseline={
            "source": "core-combat-metrics-v1",
            "metrics": {"opening_death_rate": {"level": "high"}},
        },
    )
    scope = MetricSnapshotAnalysisScope(
        match_ids=(match.id,),
        source="steam",
        owner_user_id=owner.id,
        owner_steam_id="owner",
        player_key="steam:owner",
        player_steamid="owner",
        selected_metric_snapshot_ids=(other_snapshot.id,),
    )
    non_owner_card = {
        "problem": "Other player's opening deaths should not persist.",
        "evidence": [
            {
                "metric_id": "opening_death_rate",
                "value": 0.417,
                "match_ids": [match.id],
                "source": "core_combat_metrics",
            }
        ],
        "confidence": "high",
        "caveats": [],
        "recommended_focus": "Do not persist.",
    }

    with pytest.raises(PermissionError, match="owner-scoped metric snapshots"):
        persist_owner_scoped_coach_hypotheses(
            db,
            analysis_scope=scope,
            insight_cards=[non_owner_card],
        )

    assert db.query(AnalysisRun).count() == 0
    assert db.query(CoachHypothesis).count() == 0


def test_persist_owner_scoped_coach_hypotheses_rejects_admin_debug_scope(db):
    debug_card = {
        "problem": "Debug all snapshots.",
        "evidence": [{"metric_id": "survival_rate", "value": 0.1, "match_ids": [76]}],
        "confidence": "high",
        "caveats": [],
        "recommended_focus": "Do not persist.",
    }

    with pytest.raises(ValueError, match="personal analysis scope"):
        persist_owner_scoped_coach_hypotheses(
            db,
            analysis_scope=admin_debug_all_metric_snapshots_scope(match_ids=[76]),
            insight_cards=[debug_card],
        )

    assert db.query(AnalysisRun).count() == 0
    assert db.query(CoachHypothesis).count() == 0


def test_post_metrics_owner_match_coach_loop_persists_analysis_and_evaluates_active_mission(db):
    owner = User(email="m02-owner@example.test", display_name="M02 Owner", password_hash="hash")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    db.add(SteamAccount(user_id=owner.id, steam_id="76561198000000076", persona_name="JC"))
    baseline_match = Match(id=76, source="demo", external_match_id="m02-baseline-match")
    evaluation_match = Match(id=77, source="demo", external_match_id="m02-evaluation-match")
    db.add_all([baseline_match, evaluation_match])
    db.commit()
    baseline_snapshot = create_metric_snapshot(
        db,
        match_id=baseline_match.id,
        player_key="steam:76561198000000076",
        player_name="JC",
        player_steamid="76561198000000076",
        source="utility_metrics",
        source_event_set_id="fixture:m02:baseline-utility",
        metrics={"utility_damage": 95, "he_damage": 30},
        confidence_baseline={
            "source": "utility-metrics-v1",
            "confidence": "medium",
            "metrics": {
                "utility_damage": {
                    "level": "medium",
                    "usable_for_insights": True,
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                }
            },
        },
        metadata={"schema_version": "utility-metrics-v1", "sample_matches": 1, "sample_rounds": 24},
    )
    baseline_scope = MetricSnapshotAnalysisScope(
        match_ids=(baseline_match.id,),
        source="steam",
        owner_user_id=owner.id,
        owner_steam_id="76561198000000076",
        player_key="steam:76561198000000076",
        player_steamid="76561198000000076",
        selected_metric_snapshot_ids=(baseline_snapshot.id,),
    )
    baseline_payload = build_ai_coach_payload(db, analysis_scope=baseline_scope)
    baseline_run, baseline_hypotheses = persist_owner_scoped_coach_hypotheses(
        db,
        analysis_scope=baseline_scope,
        insight_cards=baseline_payload["coach_insight_cards"],
        source_payload={"acceptance": "m02-baseline"},
    )
    draft = create_draft_coach_mission(
        db,
        user_id=owner.id,
        hypothesis_id=baseline_hypotheses[0].id,
        title="Improve utility damage",
    )
    mission = activate_draft_coach_mission(db, user_id=owner.id, mission_id=draft.id)
    owner_evaluation_snapshot = create_metric_snapshot(
        db,
        match_id=evaluation_match.id,
        player_key="steam:76561198000000076",
        player_name="JC",
        player_steamid="76561198000000076",
        source="utility_metrics",
        source_event_set_id="fixture:m02:evaluation-utility-owner",
        metrics={"utility_damage": 122, "he_damage": 42},
        confidence_baseline={
            "source": "utility-metrics-v1",
            "confidence": "medium",
            "metrics": {
                "utility_damage": {
                    "level": "medium",
                    "usable_for_insights": True,
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                }
            },
        },
        metadata={"schema_version": "utility-metrics-v1", "sample_matches": 1, "sample_rounds": 24},
    )
    other_evaluation_snapshot = create_metric_snapshot(
        db,
        match_id=evaluation_match.id,
        player_key="steam:other",
        player_name="Other",
        player_steamid="76561198000009999",
        source="utility_metrics",
        source_event_set_id="fixture:m02:evaluation-utility-other",
        metrics={"utility_damage": 1, "he_damage": 1},
        confidence_baseline={
            "source": "utility-metrics-v1",
            "confidence": "medium",
            "metrics": {
                "utility_damage": {
                    "level": "medium",
                    "usable_for_insights": True,
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                }
            },
        },
        metadata={"schema_version": "utility-metrics-v1", "sample_matches": 1, "sample_rounds": 24},
    )

    result = process_owner_match_metric_snapshots_for_coach_loop(
        db,
        user_id=owner.id,
        match_id=evaluation_match.id,
        metric_snapshot_ids=(owner_evaluation_snapshot.id, other_evaluation_snapshot.id),
        evaluation_window_start=datetime(2026, 7, 10),
        evaluation_window_end=datetime(2026, 7, 10),
    )

    assert baseline_run.user_id == owner.id
    assert baseline_hypotheses[0].owner_steam_id == "76561198000000076"
    assert result["selected_metric_snapshot_ids"] == [owner_evaluation_snapshot.id]
    assert result["analysis_run_id"] is not None
    assert result["coach_hypothesis_ids"]
    evaluations = list_mission_progress_evaluations(db, user_id=owner.id, mission_id=mission.id)
    assert [item.id for item in evaluations] == result["mission_progress_evaluation_ids"]
    summary = result["mission_status_summaries"][0]
    assert summary["mission_id"] == mission.id
    assert summary["evaluated_window"]["match_ids"] == [evaluation_match.id]
    assert summary["source_metric_snapshot_ids"] == [owner_evaluation_snapshot.id]
    assert summary["primary_metric_result"]["metric_name"] == "utility_damage"
    assert summary["primary_metric_result"]["baseline_value"] == 95
    assert summary["primary_metric_result"]["evaluation_value"] == 122
    assert summary["primary_metric_result"]["delta"] == 27
    assert summary["status"] == "improving"
    assert summary["confidence"] == 0.6
    assert summary["caveats"] == []
    assert summary["target_met"] is True
    assert "reached without failing guardrails" in summary["why_counted_or_not"]

    repeated = process_owner_match_metric_snapshots_for_coach_loop(
        db,
        user_id=owner.id,
        match_id=evaluation_match.id,
        metric_snapshot_ids=(owner_evaluation_snapshot.id, other_evaluation_snapshot.id),
        evaluation_window_start=datetime(2026, 7, 10),
        evaluation_window_end=datetime(2026, 7, 10),
    )

    assert repeated["analysis_run_id"] == result["analysis_run_id"]
    assert repeated["coach_hypothesis_ids"] == result["coach_hypothesis_ids"]
    assert repeated["mission_progress_evaluation_ids"] == result["mission_progress_evaluation_ids"]
    assert repeated["idempotency"]["reused_analysis_run"] is True
    assert repeated["idempotency"]["reused_mission_progress_evaluation_ids"] == result[
        "mission_progress_evaluation_ids"
    ]
    assert db.query(AnalysisRun).count() == 2
    assert db.query(CoachHypothesis).count() == 2
    assert len(list_mission_progress_evaluations(db, user_id=owner.id, mission_id=mission.id)) == 1


def test_ai_payload_uses_exact_recent_matches_and_reports_exclusions(db):
    db.add_all(
        [
            Match(
                source="demo",
                external_match_id="exact-ai",
                played_at=datetime(2026, 6, 1),
                result="win",
                raw_json=_date_truth_raw("exact_match_date_available", "steam_gc_match_time"),
            ),
            Match(
                source="demo",
                external_match_id="approx-ai",
                played_at=datetime(2026, 7, 1),
                result="loss",
                raw_json=_date_truth_raw("approximate_match_date", "file_modified_fallback"),
            ),
        ]
    )
    db.commit()

    payload = build_ai_coach_payload(db)

    assert [match["id"] for match in payload["recent_matches"]] == [1]
    assert payload["metric_confidence"]["date_window"]["approximate_date_matches"] == 1
    assert payload["rules"]["use_exact_date_windows_for_trends"] is True


def test_codex_handoff_provider_writes_prompt_and_payload(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        ai_handoff_dir=tmp_path,
        ai_codex_command="codex exec",
    )
    monkeypatch.setattr("app.services.ai_coach.get_settings", lambda: settings)

    result = CodexCliHandoffProvider().prepare(
        {
            "summary": {"matches_count": 1},
            "detected_weaknesses": [],
            "map_stats": [],
            "period_comparison": {},
            "coach_focus": {"title": "test"},
        }
    )

    assert result["status"] == "handoff_ready"
    assert result["provider"] == "codex_cli_handoff"
    assert result["ai_coach_prompt_version"] == AI_COACH_PROMPT_VERSION
    assert result["ai_coach_payload_schema_version"] == AI_COACH_PAYLOAD_SCHEMA_VERSION
    assert result["metric_registry_version"] == METRIC_REGISTRY_VERSION
    assert result["snapshot_generated_by"] == AI_COACH_SNAPSHOT_GENERATED_BY
    assert result["snapshot_contract_version"] == AI_COACH_SNAPSHOT_CONTRACT_VERSION
    assert result["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert result["domain_constraints"]["accepted_active_hard_recommendation_id"] == 5
    assert result["metric_confidence_policy"]["weak_metrics_must_remain_caveated"] is True
    assert result["playlist_mode_policy"]["mode_status"] == "unknown_or_provenance_only"
    assert result["public_readiness_policy"]["public_readiness"] == "blocked"
    assert "codex exec" in result["command"]
    assert list(tmp_path.glob("*/codex_prompt.md"))
    assert list(tmp_path.glob("*/coach_payload.json"))


def test_save_ai_coach_result_persists_ai_report(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    report = save_ai_coach_result(db, "# AI report\n\nFocus on survival.", source_ref="manual")
    latest = latest_ai_coach_report(db)
    serialized = serialize_ai_coach_report(report)

    assert report.report_type == "ai_coach"
    assert report.source_ref == "manual"
    assert latest is not None
    assert latest.id == report.id
    assert serialized["status"] == "saved"
    assert serialized["payload_hash"]
    assert serialized["payload_matches_count"] == 2
    assert serialized["metadata"]["ai_coach_prompt_version"] == AI_COACH_PROMPT_VERSION
    assert serialized["metadata"]["ai_coach_payload_schema_version"] == AI_COACH_PAYLOAD_SCHEMA_VERSION
    assert serialized["metadata"]["metric_registry_version"] == METRIC_REGISTRY_VERSION
    assert serialized["metadata"]["snapshot_generated_by"] == AI_COACH_SNAPSHOT_GENERATED_BY
    assert serialized["metadata"]["snapshot_contract_version"] == AI_COACH_SNAPSHOT_CONTRACT_VERSION
    assert serialized["metadata"]["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert serialized["metadata"]["domain_contract"]["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert serialized["metadata"]["domain_constraints"]["accepted_active_hard_recommendation_id"] == 5
    assert serialized["metadata"]["claim_guardrails"]["do_not_invent_parser_data"] is True
    assert serialized["metadata"]["metric_confidence_policy"]["weak_metrics_must_remain_caveated"] is True
    assert serialized["metadata"]["playlist_mode_policy"]["mode_status"] == "unknown_or_provenance_only"
    assert serialized["metadata"]["public_readiness_policy"]["v1_0_claim_allowed"] is False
    assert serialized["metadata"]["public_readiness_policy"]["friends_readiness"] == "blocked"
    assert serialized["metadata"]["artifact_retention"]["category"] == ARTIFACT_CATEGORY_COACH_OUTPUT
    assert serialized["metadata"]["artifact_retention"]["retention_class"] == RETENTION_CLASS_FINAL_OUTPUT
    assert serialized["metadata"]["analysis_scope"] == {
        "mode": "personal",
        "match_ids": [],
        "match_ids_placeholder": "all_personal_playable_matches",
        "source": "unknown",
        "source_placeholder": "unknown",
        "owner_identity": {"owner_user_id": None, "owner_steam_id": None},
        "player_identity": {"player_key": None, "player_name": None, "player_steamid": None},
        "selected_metric_snapshot_ids": [],
        "requested_metric_snapshot_ids": [],
    }
    assert serialized["insight_cards"][0]["confidence"] == "low"
    assert serialized["insight_cards"][0]["evidence"] == []
    assert serialized["insight_cards"][0]["caveats"]
    assert (
        serialized["metadata"]["contract_snapshot"]
        == serialized["metadata"]["payload_snapshot"]["contract_snapshot"]
    )
    assert (
        serialized["metadata"]["domain_contract"]
        == {
            "domain_contract_version": serialized["metadata"]["payload_snapshot"]["domain_contract_version"],
            "domain_constraints": serialized["metadata"]["payload_snapshot"]["domain_constraints"],
            "claim_guardrails": serialized["metadata"]["payload_snapshot"]["claim_guardrails"],
            "metric_confidence_policy": serialized["metadata"]["payload_snapshot"]["metric_confidence_policy"],
            "playlist_mode_policy": serialized["metadata"]["payload_snapshot"]["playlist_mode_policy"],
            "recommendation_policy": serialized["metadata"]["payload_snapshot"]["recommendation_policy"],
            "public_readiness_policy": serialized["metadata"]["payload_snapshot"]["public_readiness_policy"],
        }
    )


def test_save_ai_coach_result_rejects_admin_debug_all_snapshots_payload(db):
    match = Match(source="demo", external_match_id="debug-scope-save")
    db.add(match)
    db.commit()
    db.refresh(match)
    create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:any-player",
        player_name="Any",
        player_steamid="any-player",
        source="core_combat_metrics",
        metrics={
            "rounds": 12,
            "opening_deaths": 5,
            "opening_death_rate": 0.417,
            "survived_rounds": 1,
            "survival_rate": 0.083,
        },
        confidence_baseline={
            "source": "core-combat-metrics-v1",
            "metrics": {
                "opening_death_rate": {"level": "high"},
                "survival_rate": {"level": "high"},
            },
        },
    )
    debug_payload = build_ai_coach_payload(db, analysis_scope=admin_debug_all_metric_snapshots_scope())

    with pytest.raises(ValueError, match="personal analysis scope"):
        save_ai_coach_result(db, "# Debug report\n\nShould not save as personal.", payload_snapshot=debug_payload)

    assert latest_ai_coach_report(db) is None


def test_admin_debug_scope_report_is_not_presented_as_personal_latest_or_history(db):
    personal_report = CoachReport(
        report_type="ai_coach",
        source_ref="personal",
        report_markdown="Personal report",
        report_json=json.dumps({"analysis_scope": {"mode": "personal"}}),
    )
    debug_report = CoachReport(
        report_type="ai_coach",
        source_ref="admin-debug",
        report_markdown="Debug report",
        report_json=json.dumps({"payload_snapshot": {"analysis_scope": {"mode": "admin_debug_all_snapshots"}}}),
    )
    db.add_all([personal_report, debug_report])
    db.commit()
    db.refresh(personal_report)
    db.refresh(debug_report)

    latest = latest_ai_coach_report(db)
    history = list_ai_coach_reports(db)

    assert latest is not None
    assert latest.id == personal_report.id
    assert debug_report.id not in [report.id for report in history]


def test_ai_coach_report_history_is_newest_first(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    first = save_ai_coach_result(db, "First report", source_ref="manual-1")
    second = save_ai_coach_result(db, "Second report", source_ref="manual-2")

    reports = list_ai_coach_reports(db)

    assert [report.id for report in reports[:2]] == [second.id, first.id]


def test_save_ai_coach_result_rejects_empty_text(db):
    with pytest.raises(ValueError):
        save_ai_coach_result(db, "   ")


def test_local_llm_provider_calls_ollama(monkeypatch):
    settings = SimpleNamespace(
        local_llm_base_url="http://127.0.0.1:11434",
        local_llm_model="test-model",
        local_llm_timeout_seconds=5,
    )
    monkeypatch.setattr("app.services.ai_coach.get_settings", lambda: settings)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps({"response": "AI report"}).encode()

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:11434/api/generate"
        assert timeout == 5
        return FakeResponse()

    monkeypatch.setattr("app.services.ai_coach.urllib.request.urlopen", fake_urlopen)

    result = LocalLLMProvider().generate(
        {
            "summary": {"matches_count": 1},
            "detected_weaknesses": [],
            "map_stats": [],
            "period_comparison": {},
            "coach_focus": {"title": "test"},
        }
    )

    assert result == "AI report"


def test_ai_provider_health_for_handoff(monkeypatch):
    settings = SimpleNamespace(ai_provider="codex_cli_handoff")
    monkeypatch.setattr("app.services.ai_coach.get_settings", lambda: settings)

    health = ai_provider_health()

    assert health["provider"] == "codex_cli_handoff"
    assert health["status"] == "handoff"


def _date_truth_raw(status: str, source: str) -> str:
    return json.dumps(
        {
            "match_date_status": status,
            "match_date_source": source,
            "played_at_source": source,
        }
    )
