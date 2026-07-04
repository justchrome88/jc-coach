import json
import sys
import types
from datetime import datetime

from sqlalchemy import select

from app.db.models import (
    DemoDamageEvent,
    DemoDuel,
    DemoParseArtifact,
    DemoPlayerRound,
    DemoRound,
    DemoWeaponStat,
    Match,
)
from app.services.demo_parser import DemoParseError, import_demo_file, parse_demo
from app.services.demo_retention import (
    DEMO_RETENTION_POLICY_RETAIN_RAW,
    DEMO_RETENTION_STATUS_RETAINED_AFTER_FAILURE,
    DEMO_RETENTION_STATUS_RETAINED_FOR_DEV,
    delete_raw_demo_after_success,
)


def test_parse_demo_with_fake_demoparser(monkeypatch, tmp_path):
    demo_path = tmp_path / "match.dem"
    demo_path.write_bytes(b"HL2DEMO")
    _install_fake_demoparser(monkeypatch)

    parsed = parse_demo(demo_path, player_identifier="me")

    assert parsed["status"] == "parsed"
    assert parsed["player"]["name"] == "me"
    assert parsed["match"]["kills"] == 1
    assert parsed["match"]["deaths"] == 1
    assert parsed["match"]["entry_kills"] == 1
    assert parsed["match"]["entry_deaths"] == 1
    assert parsed["match"]["adr"] == 33.33
    assert parsed["match"]["swing_score"] is not None
    assert parsed["swing_summary"]["formula"] == "jc_swing_v1"
    assert parsed["parser_confidence"] in {"low", "medium", "high"}
    assert parsed["event_counts"]["player_death"] == 3
    assert parsed["metric_confidence"]["adr"] == "high"
    assert parsed["warnings"]
    assert parsed["aim_summary"]["damage_per_death"] == 100
    assert parsed["aim_summary"]["multi_kill_rounds"] == 0
    assert parsed["weapon_breakdown"]["ak47"]["damage"] == 50


def test_parse_demo_prefers_jc_player_by_default(monkeypatch, tmp_path):
    demo_path = tmp_path / "match.dem"
    demo_path.write_bytes(b"HL2DEMO")
    _install_fake_demoparser(monkeypatch)

    parsed = parse_demo(demo_path)

    assert parsed["player"]["name"] == "JC"


def test_import_demo_file_persists_match(monkeypatch, tmp_path, db):
    demo_path = tmp_path / "match.dem"
    demo_path.write_bytes(b"HL2DEMO")
    _install_fake_demoparser(monkeypatch)

    result = import_demo_file(db, demo_path, original_filename="match.dem", player_identifier="me")
    match = db.scalar(select(Match).where(Match.source == "demo"))

    assert result["imported"] == 1
    assert result["parser_confidence"] in {"low", "medium", "high"}
    assert result["event_counts"]["player_hurt"] == 2
    assert match is not None
    assert match.demo_file.endswith(".dem")
    assert match.kills == 1
    assert match.utility_damage == 50
    assert result["demo_retention_policy"] == DEMO_RETENTION_POLICY_RETAIN_RAW
    assert result["demo_retention_status"] == DEMO_RETENTION_STATUS_RETAINED_FOR_DEV
    assert result["parser_success"] is True
    assert result["raw_demo_size_bytes"] is not None
    assert "retain_raw_for_parser_development" in match.raw_json


def test_import_demo_file_filters_date_source_metadata_from_match_kwargs(monkeypatch, tmp_path, db):
    demo_path = tmp_path / "steam-match.dem"
    demo_path.write_bytes(b"HL2DEMO")

    monkeypatch.setattr(
        "app.services.demo_parser.parse_demo",
        lambda *_args, **_kwargs: _parsed_demo_payload(
            external_match_id="steam-exact-date",
            played_at=datetime(2026, 7, 2, 20, 0, 0),
        ),
    )

    result = import_demo_file(
        db,
        demo_path,
        original_filename="steam-match.dem",
        steam_metadata={
            "source": "steam_gc",
            "match_time": "2026-07-02T20:00:00+00:00",
            "played_at_source": "steam_gc_match_time",
        },
    )
    match = db.get(Match, result["match_id"])
    raw = json.loads(match.raw_json)

    assert result["imported"] == 1
    assert match.played_at == datetime(2026, 7, 2, 20, 0, 0)
    assert "played_at_source" not in Match.__table__.columns
    assert raw["played_at_source"] == "steam_gc_match_time"
    assert raw["match"]["played_at_source"] == "steam_gc_match_time"


def test_import_demo_file_preserves_unavailable_date_truth_metadata(monkeypatch, tmp_path, db):
    demo_path = tmp_path / "steam-unknown-date.dem"
    demo_path.write_bytes(b"HL2DEMO")

    parsed = _parsed_demo_payload(external_match_id="steam-unknown-date", played_at=None)
    parsed["played_at_source"] = "unavailable"
    parsed["match_date_status"] = "exact_match_date_unavailable"
    parsed["match_date_source"] = "unavailable"
    parsed["match"]["played_at_source"] = "unavailable"
    parsed["match"]["match_date_status"] = "exact_match_date_unavailable"
    parsed["match"]["match_date_source"] = "unavailable"
    monkeypatch.setattr("app.services.demo_parser.parse_demo", lambda *_args, **_kwargs: parsed)

    result = import_demo_file(db, demo_path, original_filename="steam-unknown-date.dem")
    match = db.get(Match, result["match_id"])
    raw = json.loads(match.raw_json)

    assert result["imported"] == 1
    assert match.played_at is None
    assert raw["played_at_source"] == "unavailable"
    assert raw["match_date_status"] == "exact_match_date_unavailable"
    assert raw["match"]["played_at_source"] == "unavailable"


def test_import_demo_file_persists_deep_parse_artifacts(monkeypatch, tmp_path, db):
    demo_path = tmp_path / "match.dem"
    demo_path.write_bytes(b"HL2DEMO")
    _install_fake_demoparser(monkeypatch)

    result = import_demo_file(db, demo_path, original_filename="match.dem", player_identifier="me")

    assert result["imported"] == 1
    match = db.scalar(select(Match).where(Match.source == "demo"))
    assert match is not None
    artifact = db.scalar(select(DemoParseArtifact).where(DemoParseArtifact.match_id == match.id))
    assert artifact is not None
    assert artifact.payload_version
    assert db.scalar(select(DemoRound).where(DemoRound.match_id == match.id)) is not None
    assert db.scalar(select(DemoPlayerRound).where(DemoPlayerRound.match_id == match.id)) is not None
    assert db.scalar(select(DemoWeaponStat).where(DemoWeaponStat.match_id == match.id)) is not None
    assert db.scalar(select(DemoDamageEvent).where(DemoDamageEvent.match_id == match.id)) is not None
    assert db.scalar(select(DemoDuel).where(DemoDuel.match_id == match.id)) is not None


def test_duplicate_demo_import_removes_extra_copy(monkeypatch, tmp_path, db):
    demo_path = tmp_path / "match.dem"
    demo_path.write_bytes(b"HL2DEMO")
    _install_fake_demoparser(monkeypatch)

    first = import_demo_file(db, demo_path, original_filename="match.dem", player_identifier="me")
    second = import_demo_file(db, demo_path, original_filename="match.dem", player_identifier="me")

    assert first["imported"] == 1
    assert second["imported"] == 0
    assert second["skipped_duplicates"] == 1
    assert second["stored_path"] == first["stored_path"]
    assert second["demo_retention_status"] == DEMO_RETENTION_STATUS_RETAINED_FOR_DEV


def test_parse_failure_retains_raw_demo_metadata(monkeypatch, tmp_path, db):
    demo_path = tmp_path / "broken.dem"
    demo_path.write_bytes(b"HL2DEMO")

    class BrokenParser:
        def __init__(self, _path):
            pass

        def parse_header(self):
            raise RuntimeError("broken parser")

    module = types.ModuleType("demoparser2")
    module.DemoParser = BrokenParser
    monkeypatch.setitem(sys.modules, "demoparser2", module)

    try:
        import_demo_file(db, demo_path, original_filename="broken.dem", player_identifier="me")
    except DemoParseError as exc:
        retention = exc.retention
    else:
        raise AssertionError("broken parser should fail")

    assert retention["demo_retention_policy"] == DEMO_RETENTION_POLICY_RETAIN_RAW
    assert retention["demo_retention_status"] == DEMO_RETENTION_STATUS_RETAINED_AFTER_FAILURE
    assert retention["parser_success"] is False
    assert retention["raw_demo_path"].endswith("broken.dem")
    assert retention["raw_demo_size_bytes"] is not None


def test_delete_after_success_helper_is_disabled_by_default(tmp_path):
    demo_path = tmp_path / "retained.dem"
    demo_path.write_bytes(b"HL2DEMO")

    result = delete_raw_demo_after_success(demo_path)

    assert result["deleted"] is False
    assert demo_path.exists()
    assert result["demo_retention_status"] == DEMO_RETENTION_STATUS_RETAINED_FOR_DEV


def test_delete_after_success_helper_requires_explicit_enable(tmp_path):
    demo_path = tmp_path / "delete-me.dem"
    demo_path.write_bytes(b"HL2DEMO")

    result = delete_raw_demo_after_success(demo_path, enabled=True)

    assert result["deleted"] is True
    assert not demo_path.exists()


def _install_fake_demoparser(monkeypatch):
    module = types.ModuleType("demoparser2")

    class FakeDemoParser:
        def __init__(self, path):
            self.path = path

        def parse_header(self):
            return {"map_name": "de_mirage"}

        def parse_player_info(self):
            return [
                {"name": "me", "steamid": "123", "team_number": 2},
                {"name": "JC", "steamid": "789", "team_number": 2},
                {"name": "ally", "steamid": "124", "team_number": 2},
                {"name": "enemy", "steamid": "456", "team_number": 3},
                {"name": "enemy2", "steamid": "457", "team_number": 3},
            ]

        def parse_event(self, event_name, **kwargs):
            if event_name == "player_death":
                return [
                    {
                        "total_rounds_played": 0,
                        "tick": 100,
                        "attacker_name": "me",
                        "attacker_steamid": "123",
                        "user_name": "enemy",
                        "user_steamid": "456",
                        "headshot": True,
                        "weapon": "ak47",
                    },
                    {
                        "total_rounds_played": 1,
                        "tick": 200,
                        "attacker_name": "enemy",
                        "attacker_steamid": "456",
                        "user_name": "me",
                        "user_steamid": "123",
                        "headshot": False,
                        "weapon": "m4a1",
                    },
                    {
                        "total_rounds_played": 2,
                        "tick": 300,
                        "attacker_name": "JC",
                        "attacker_steamid": "789",
                        "user_name": "enemy",
                        "user_steamid": "456",
                        "headshot": False,
                        "weapon": "ak47",
                    },
                ]
            if event_name == "player_hurt":
                return [
                    {
                        "total_rounds_played": 0,
                        "attacker_name": "me",
                        "attacker_steamid": "123",
                        "user_name": "enemy",
                        "user_steamid": "456",
                        "dmg_health": 50,
                        "weapon": "hegrenade",
                    },
                    {
                        "total_rounds_played": 1,
                        "attacker_name": "me",
                        "attacker_steamid": "123",
                        "user_name": "enemy",
                        "user_steamid": "456",
                        "dmg_health": 50,
                        "weapon": "ak47",
                    },
                ]
            if event_name == "round_start":
                return [{"round": 1, "tick": 10, "total_rounds_played": 0}]
            if event_name == "round_freeze_end":
                return [{"tick": 20, "total_rounds_played": 0}]
            if event_name == "round_end":
                return [{"round": 1, "tick": 500, "total_rounds_played": 0, "winner": "T", "reason": "ct_killed"}]
            if event_name == "weapon_fire":
                return [
                    {"total_rounds_played": 0, "tick": 90, "user_name": "me", "user_steamid": "123", "weapon": "ak47"},
                    {"total_rounds_played": 0, "tick": 91, "user_name": "me", "user_steamid": "123", "weapon": "ak47"},
                ]
            if event_name == "player_blind":
                return [
                    {
                        "total_rounds_played": 0,
                        "tick": 95,
                        "attacker_name": "me",
                        "attacker_steamid": "123",
                        "user_name": "enemy",
                        "user_steamid": "456",
                        "blind_duration": 1.5,
                        "entityid": 7,
                    }
                ]
            if event_name == "flashbang_detonate":
                return [
                    {
                        "total_rounds_played": 0,
                        "tick": 95,
                        "user_name": "me",
                        "user_steamid": "123",
                        "entityid": 7,
                        "x": 1,
                        "y": 2,
                        "z": 3,
                    }
                ]
            return []

        def parse_grenades(self):
            return [
                {
                    "grenade_type": "CFlashbangProjectile",
                    "grenade_entity_id": 7,
                    "tick": 90,
                    "name": "me",
                    "steamid": 123,
                },
                {
                    "grenade_type": "CFlashbangProjectile",
                    "grenade_entity_id": 7,
                    "tick": 95,
                    "name": "me",
                    "steamid": 123,
                },
            ]

    module.DemoParser = FakeDemoParser
    monkeypatch.setitem(sys.modules, "demoparser2", module)


def _parsed_demo_payload(external_match_id: str, played_at: datetime | None) -> dict:
    return {
        "status": "parsed",
        "parser": "demoparser2",
        "parser_version": "test",
        "payload_version": "test",
        "file": "test.dem",
        "demo_sha1": "abc123",
        "played_at": played_at.isoformat() if played_at else None,
        "played_at_source": "demo_header" if played_at else "unavailable",
        "player": {"name": "me", "steamid": "123"},
        "match": {
            "source": "demo",
            "external_match_id": external_match_id,
            "played_at": played_at,
            "map_name": "de_mirage",
            "mode": "demo",
            "result": "win",
            "rounds_for": 13,
            "rounds_against": 7,
            "kills": 20,
            "deaths": 10,
            "assists": 3,
            "kd": 2.0,
            "adr": 100.0,
            "kast": 80.0,
            "rating": None,
            "swing_score": 10.0,
            "headshot_percent": 50.0,
            "entry_kills": 2,
            "entry_deaths": 1,
            "early_deaths": None,
            "flash_assists": 0,
            "utility_damage": 12,
            "enemies_flashed": 1,
            "clutches_won": None,
            "clutches_lost": None,
            "side_t_rounds_won": None,
            "side_t_rounds_lost": None,
            "side_ct_rounds_won": None,
            "side_ct_rounds_lost": None,
        },
        "aim_summary": {},
        "weapon_breakdown": {},
        "swing_summary": {},
        "deep": {},
        "aim_data_gaps": [],
        "header": {},
        "event_counts": {},
        "metric_confidence": {},
        "parser_confidence": "medium",
        "warnings": [],
        "available_players": [{"name": "me", "steamid": "123"}],
        "message": "Demo imported with parser confidence metadata.",
    }
