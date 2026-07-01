import sys
import types

from sqlalchemy import select

from app.db.models import Match
from app.services.demo_parser import import_demo_file, parse_demo


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
    assert match is not None
    assert match.demo_file.endswith(".dem")
    assert match.kills == 1
    assert match.utility_damage == 50


def _install_fake_demoparser(monkeypatch):
    module = types.ModuleType("demoparser2")

    class FakeDemoParser:
        def __init__(self, path):
            self.path = path

        def parse_header(self):
            return {"map_name": "de_mirage"}

        def parse_player_info(self):
            return [
                {"name": "me", "steamid": "123"},
                {"name": "JC", "steamid": "789"},
                {"name": "enemy", "steamid": "456"},
            ]

        def parse_event(self, event_name, **kwargs):
            if event_name == "player_death":
                return [
                    {
                        "total_rounds_played": 0,
                        "tick": 100,
                        "attacker_name": "me",
                        "user_name": "enemy",
                        "headshot": True,
                    },
                    {
                        "total_rounds_played": 1,
                        "tick": 200,
                        "attacker_name": "enemy",
                        "user_name": "me",
                        "headshot": False,
                    },
                    {
                        "total_rounds_played": 2,
                        "tick": 300,
                        "attacker_name": "JC",
                        "user_name": "enemy",
                        "headshot": False,
                    },
                ]
            if event_name == "player_hurt":
                return [
                    {
                        "total_rounds_played": 0,
                        "attacker_name": "me",
                        "user_name": "enemy",
                        "dmg_health": 50,
                        "weapon": "hegrenade",
                    },
                    {
                        "total_rounds_played": 1,
                        "attacker_name": "me",
                        "user_name": "enemy",
                        "dmg_health": 50,
                        "weapon": "ak47",
                    },
                ]
            return []

    module.DemoParser = FakeDemoParser
    monkeypatch.setitem(sys.modules, "demoparser2", module)
