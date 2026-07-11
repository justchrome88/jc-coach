import json

import pytest
from sqlalchemy import select

from app.db.models import (
    DemoParseArtifact,
    Match,
    MetricSnapshot,
    MissionProgressEvaluation,
    SteamAccount,
    User,
)
from app.services.mission_domain import activate_coach_mission, create_analysis_run, create_coach_hypothesis
from app.services.owner.match_processing import process_owner_match_after_parser_artifact

OWNER_STEAM_ID = "76561198000000076"
OTHER_STEAM_ID = "76561198000009999"


def test_process_owner_match_after_parser_artifact_persists_metrics_and_runs_owner_loop(db):
    owner = _owner(db)
    match = _match(db, "m05-happy")
    artifact = _artifact(db, match=match, owner_utility_damage=130, other_utility_damage=5, status="parsed")

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
    assert result["analysis_run"]["id"] is None
    assert result["coach_hypothesis_ids"]["all"] == []
    assert result["active_mission_ids"] == []
    assert result["mission_progress_evaluation_ids"] == []
    assert result["mission_evaluation_summary"] == [
        {
            "mission_id": None,
            "evaluation_id": None,
            "status": "skipped",
            "action": "skipped",
            "skip_reason": "no_active_missions",
            "mission_status": None,
            "owner_steam_id": OWNER_STEAM_ID,
            "source_metric_snapshot_ids": [],
            "evaluated_window": {},
            "confidence": None,
            "caveats": [],
            "reason_codes": ["no_active_missions"],
            "counted": False,
            "reused": False,
            "progress_explanation": "No active owner missions were available for this processed match.",
        }
    ]

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
    assert first["mission_progress_evaluation_ids"] == []
    assert repeated["metric_snapshot_ids"]["created"] == []
    assert set(repeated["metric_snapshot_ids"]["reused"]) == set(first["metric_snapshot_ids"]["all"])
    assert repeated["mission_progress_evaluation_ids"] == []
    assert first["mission_evaluation_summary"][0]["action"] == "skipped"
    assert first["mission_evaluation_summary"][0]["skip_reason"] == "insufficient_metric_data"
    assert first["mission_evaluation_summary"][0]["counted"] is False
    assert repeated["mission_evaluation_summary"][0]["reused"] is False
    assert db.query(MetricSnapshot).count() == len(first["metric_snapshot_ids"]["all"])
    assert db.query(MissionProgressEvaluation).count() == 0
    assert first["mission_status_summaries"] == []


def test_owner_global_active_mission_policy_rejects_multiple_active_missions(db):
    owner = _owner(db)
    _active_utility_mission(db, owner=owner, baseline=0.3)
    with pytest.raises(ValueError, match="Duplicate active mission for owner"):
        _active_survival_mission(db, owner=owner, baseline=0.25)


def test_process_owner_match_after_parser_artifact_skips_inactive_and_cross_owner_missions(db):
    owner = _owner(db)
    inactive_mission = _active_utility_mission(db, owner=owner, baseline=50, status="draft")
    cross_owner_mission = _active_utility_mission(
        db,
        owner=owner,
        baseline=50,
        owner_steam_id=OTHER_STEAM_ID,
    )
    match = _match(db, "m05-skip-inactive-cross-owner")
    artifact = _artifact(db, match=match, owner_utility_damage=20, other_utility_damage=300)

    result = process_owner_match_after_parser_artifact(
        db,
        user_id=owner.id,
        match_id=match.id,
        parser_artifact_id=artifact.id,
    )

    assert result["active_mission_ids"] == []
    assert result["mission_progress_evaluation_ids"] == []
    assert db.query(MissionProgressEvaluation).count() == 0
    summary_by_reason = {item["skip_reason"]: item for item in result["mission_evaluation_summary"]}
    assert summary_by_reason["inactive_status"]["mission_id"] == inactive_mission.id
    assert summary_by_reason["cross_owner_denied"]["mission_id"] == cross_owner_mission.id
    assert summary_by_reason["no_active_missions"]["mission_id"] is None


def test_noncanonical_unsupported_metric_mission_is_rejected(db):
    owner = _owner(db)
    with pytest.raises(ValueError, match="Noncanonical coach domain"):
        _active_custom_metric_mission(db, owner=owner, metric_name="unsupported_metric", baseline=1)


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
    owner = db.query(User).filter(User.email == "m05-owner@example.test").one_or_none()
    match = Match(user_id=owner.id if owner else None, source="demo", external_match_id=external_match_id)
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
    status: str = "completed",
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
        status=status,
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


def _active_utility_mission(
    db,
    *,
    owner: User,
    baseline: int,
    status: str = "active",
    owner_steam_id: str = OWNER_STEAM_ID,
):
    return _active_custom_metric_mission(
        db,
        owner=owner,
        metric_name="opening_death_rate",
        baseline=float(baseline) if float(baseline) <= 1 else 0.3,
        status=status,
        owner_steam_id=owner_steam_id,
        title="Improve duel discipline",
        recommended_focus="Review bounded opening-death evidence.",
    )


def _active_survival_mission(db, *, owner: User, baseline: float):
    return _active_custom_metric_mission(
        db,
        owner=owner,
        metric_name="survival_rate",
        baseline=baseline,
        title="Improve survival",
        recommended_focus="Stay alive longer in rounds.",
    )


def _active_custom_metric_mission(
    db,
    *,
    owner: User,
    metric_name: str,
    baseline: float,
    status: str = "active",
    owner_steam_id: str = OWNER_STEAM_ID,
    title: str = "Improve metric",
    recommended_focus: str = "Review the assigned metric.",
):
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id=owner_steam_id)
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card={
            "id": f"m05-{metric_name}-baseline",
            "problem": f"{metric_name} can become a measurable mission.",
            "evidence": [{"metric_id": metric_name, "value": baseline, "metric_confidence": "medium"}],
            "confidence": "medium",
            "caveats": [],
            "recommended_focus": recommended_focus,
            "mission_readiness": {
                "can_become_mission": True,
                "target_metric_candidate": metric_name,
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
    mission = activate_coach_mission(
        db,
        user_id=owner.id,
        hypothesis_id=hypothesis.id,
        title=title,
        status=status,
    )
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
