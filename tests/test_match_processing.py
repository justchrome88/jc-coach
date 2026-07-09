import json

from sqlalchemy import select

from app.db.models import (
    DemoParseArtifact,
    Match,
    MetricSnapshot,
    SteamAccount,
    User,
)
from app.services.match_processing import process_owner_match_after_parser_artifact
from app.services.mission_domain import activate_coach_mission, create_analysis_run, create_coach_hypothesis

OWNER_STEAM_ID = "76561198000000076"
OTHER_STEAM_ID = "76561198000009999"


def test_process_owner_match_after_parser_artifact_persists_metrics_and_runs_owner_loop(db):
    owner = _owner(db)
    match = _match(db, "m05-happy")
    artifact = _artifact(db, match=match, owner_utility_damage=130, other_utility_damage=5)

    result = process_owner_match_after_parser_artifact(
        db,
        user_id=owner.id,
        match_id=match.id,
        parser_artifact_id=artifact.id,
    )

    assert result["status"] == "processed"
    assert result["match_id"] == match.id
    assert result["parser_artifact"]["id"] == artifact.id
    assert result["source_event_set_id"].startswith(f"parser-artifact:{artifact.id}:events:")
    assert result["metric_snapshot_ids"]["by_source"]["core_combat_metrics"]["all"]
    assert result["metric_snapshot_ids"]["by_source"]["utility_metrics"]["all"]
    assert result["analysis_run"]["id"] is not None
    assert result["coach_hypothesis_ids"]["all"]
    assert result["active_mission_ids"] == []
    assert result["mission_progress_evaluation_ids"] == []

    selected_snapshots = [
        db.get(MetricSnapshot, snapshot_id) for snapshot_id in result["owner_selected_metric_snapshot_ids"]
    ]
    assert selected_snapshots
    assert all(snapshot.player_steamid == OWNER_STEAM_ID for snapshot in selected_snapshots)
    assert _other_snapshot_ids(db, match.id).isdisjoint(result["owner_selected_metric_snapshot_ids"])
    for snapshot in db.scalars(select(MetricSnapshot).where(MetricSnapshot.match_id == match.id)):
        assert snapshot.source_parser_artifact_id == artifact.id
        assert snapshot.source_event_set_id == result["source_event_set_id"]


def test_process_owner_match_after_parser_artifact_evaluates_active_mission_with_owner_only_data(db):
    owner = _owner(db)
    mission = _active_utility_mission(db, owner=owner, baseline=50)
    match = _match(db, "m05-active-mission")
    artifact = _artifact(db, match=match, owner_utility_damage=20, other_utility_damage=300)

    first = process_owner_match_after_parser_artifact(
        db,
        user_id=owner.id,
        match_id=match.id,
        parser_artifact_id=artifact.id,
    )
    repeated = process_owner_match_after_parser_artifact(
        db,
        user_id=owner.id,
        match_id=match.id,
        parser_artifact_id=artifact.id,
    )

    assert first["active_mission_ids"] == [mission.id]
    assert first["mission_progress_evaluation_ids"]
    assert repeated["metric_snapshot_ids"]["created"] == []
    assert set(repeated["metric_snapshot_ids"]["reused"]) == set(first["metric_snapshot_ids"]["all"])
    assert repeated["mission_progress_evaluation_ids"] == first["mission_progress_evaluation_ids"]
    assert repeated["idempotency"]["post_metrics_coach_loop"]["reused_mission_progress_evaluation_ids"] == first[
        "mission_progress_evaluation_ids"
    ]
    assert db.query(MetricSnapshot).count() == len(first["metric_snapshot_ids"]["all"])

    summary = first["mission_status_summaries"][0]
    owner_utility_snapshot_id = _snapshot_id(
        db,
        match_id=match.id,
        player_steamid=OWNER_STEAM_ID,
        source="utility_metrics",
    )
    other_utility_snapshot_id = _snapshot_id(
        db,
        match_id=match.id,
        player_steamid=OTHER_STEAM_ID,
        source="utility_metrics",
    )
    assert owner_utility_snapshot_id in summary["source_metric_snapshot_ids"]
    assert other_utility_snapshot_id not in summary["source_metric_snapshot_ids"]
    assert summary["primary_metric_result"]["metric_name"] == "utility_damage"
    assert summary["primary_metric_result"]["evaluation_value"] == 20
    assert summary["status"] == "insufficient_data"
    assert summary["primary_metric_result"]["reason_codes"] == ["insufficient_confidence"]


def test_process_owner_match_after_parser_artifact_blocks_missing_artifact(db):
    owner = _owner(db)
    match = _match(db, "m05-missing-artifact")

    result = process_owner_match_after_parser_artifact(db, user_id=owner.id, match_id=match.id)

    assert result["status"] == "blocked"
    assert result["issue"] == "parser_artifact_missing"
    assert result["metric_snapshot_ids"]["all"] == []
    assert db.query(MetricSnapshot).count() == 0


def _owner(db) -> User:
    owner = User(email="m05-owner@example.test", display_name="M05 Owner", password_hash="hash")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    db.add(SteamAccount(user_id=owner.id, steam_id=OWNER_STEAM_ID, persona_name="JC"))
    db.commit()
    return owner


def _match(db, external_match_id: str) -> Match:
    match = Match(source="demo", external_match_id=external_match_id)
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def _artifact(
    db,
    *,
    match: Match,
    owner_utility_damage: int,
    other_utility_damage: int,
) -> DemoParseArtifact:
    payload = {
        "parser": "fixture-parser",
        "parser_version": "m05",
        "payload_version": "parser-artifact-v0.10",
        "deep": {
            "round_boundaries": [
                {"round_number": 1, "event_type": "round_end", "tick": 6400},
                {"round_number": 2, "event_type": "round_end", "tick": 12800},
            ],
            "player_hurt_events": [
                {
                    "round_number": 1,
                    "tick": 1200,
                    "attacker_name": "JC",
                    "attacker_steamid": OWNER_STEAM_ID,
                    "victim_name": "Other",
                    "victim_steamid": OTHER_STEAM_ID,
                    "weapon": "hegrenade",
                    "damage_health": owner_utility_damage,
                },
                {
                    "round_number": 2,
                    "tick": 8400,
                    "attacker_name": "Other",
                    "attacker_steamid": OTHER_STEAM_ID,
                    "victim_name": "JC",
                    "victim_steamid": OWNER_STEAM_ID,
                    "weapon": "hegrenade",
                    "damage_health": other_utility_damage,
                },
            ],
            "player_death_events": [
                {
                    "round_number": 1,
                    "tick": 2200,
                    "attacker_name": "JC",
                    "attacker_steamid": OWNER_STEAM_ID,
                    "victim_name": "Other",
                    "victim_steamid": OTHER_STEAM_ID,
                    "weapon": "ak47",
                },
                {
                    "round_number": 2,
                    "tick": 9200,
                    "attacker_name": "Other",
                    "attacker_steamid": OTHER_STEAM_ID,
                    "victim_name": "JC",
                    "victim_steamid": OWNER_STEAM_ID,
                    "weapon": "m4a1",
                },
            ],
            "player_rounds": [
                {"round_number": 1, "player_name": "JC", "player_steamid": OWNER_STEAM_ID, "survived": True},
                {"round_number": 2, "player_name": "JC", "player_steamid": OWNER_STEAM_ID, "survived": False},
                {"round_number": 1, "player_name": "Other", "player_steamid": OTHER_STEAM_ID, "survived": False},
                {"round_number": 2, "player_name": "Other", "player_steamid": OTHER_STEAM_ID, "survived": True},
            ],
            "grenade_events": [
                {
                    "round_number": 1,
                    "tick": 1150,
                    "player_name": "JC",
                    "player_steamid": OWNER_STEAM_ID,
                    "grenade_type": "hegrenade",
                },
                {
                    "round_number": 2,
                    "tick": 8350,
                    "player_name": "Other",
                    "player_steamid": OTHER_STEAM_ID,
                    "grenade_type": "hegrenade",
                },
            ],
        },
    }
    artifact = DemoParseArtifact(
        match_id=match.id,
        parser_name="fixture-parser",
        parser_version="m05",
        payload_version="parser-artifact-v0.10",
        status="completed",
        source_demo_file="/tmp/m05.dem",
        demo_sha1="b" * 40,
        event_counts_json=json.dumps({"player_hurt": 2, "player_death": 2}),
        confidence_json=json.dumps(
            {
                "parser_confidence": "medium",
                "metric_confidence": {
                    "adr": "medium",
                    "entry_duels": "medium",
                    "grenades": "medium",
                    "kast": "medium",
                    "utility": "medium",
                },
            }
        ),
        data_gaps_json=json.dumps([]),
        payload_json=json.dumps(payload),
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def _active_utility_mission(db, *, owner: User, baseline: int):
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id=OWNER_STEAM_ID)
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card={
            "id": "m05-utility-baseline",
            "problem": "Utility damage can become a measurable mission.",
            "evidence": [{"metric_id": "utility_damage", "value": baseline, "metric_confidence": "medium"}],
            "confidence": "medium",
            "caveats": [],
            "recommended_focus": "Review damage-producing grenade rounds.",
            "mission_readiness": {
                "can_become_mission": True,
                "target_metric_candidate": "utility_damage",
                "baseline_value": baseline,
                "confidence_eligibility": {
                    "level": "medium",
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                },
                "blocking_reason_codes": [],
            },
        },
    )
    mission = activate_coach_mission(db, user_id=owner.id, hypothesis_id=hypothesis.id, title="Improve utility")
    db.commit()
    db.refresh(mission)
    return mission


def _other_snapshot_ids(db, match_id: int) -> set[int]:
    return {
        snapshot.id
        for snapshot in db.scalars(select(MetricSnapshot).where(MetricSnapshot.match_id == match_id)).all()
        if snapshot.player_steamid == OTHER_STEAM_ID
    }


def _snapshot_id(db, *, match_id: int, player_steamid: str, source: str) -> int:
    snapshot = db.scalar(
        select(MetricSnapshot)
        .where(MetricSnapshot.match_id == match_id)
        .where(MetricSnapshot.player_steamid == player_steamid)
        .where(MetricSnapshot.source == source)
    )
    assert snapshot is not None
    return snapshot.id
