import json

from app.db.models import Match
from app.services.aim_stats import get_aim_profile, match_aim_profile


def test_get_aim_profile_aggregates_match_and_weapon_data():
    matches = [
        Match(
            source="demo",
            external_match_id="m1",
            adr=90,
            kd=1.4,
            headshot_percent=50,
            entry_kills=2,
            entry_deaths=1,
            raw_json=json.dumps(
                {
                    "aim_summary": {"damage_per_death": 120, "multi_kill_rounds": 2},
                    "weapon_breakdown": {
                        "ak47": {"weapon": "ak47", "kills": 4, "headshots": 2, "deaths": 1, "damage": 350}
                    },
                }
            ),
        ),
        Match(
            source="demo",
            external_match_id="m2",
            adr=70,
            kd=0.9,
            headshot_percent=25,
            entry_kills=1,
            entry_deaths=2,
            raw_json=json.dumps(
                {
                    "aim_summary": {"damage_per_death": 80, "multi_kill_rounds": 1},
                    "weapon_breakdown": {
                        "ak47": {"weapon": "ak47", "kills": 2, "headshots": 1, "deaths": 2, "damage": 180}
                    },
                }
            ),
        ),
    ]

    profile = get_aim_profile(matches)

    assert profile["averages"]["adr"] == 80
    assert profile["averages"]["damage_per_death"] == 100
    assert profile["averages"]["opening_duel_success"] == 50
    assert profile["averages"]["multi_kill_rounds"] == 3
    assert profile["weapon_breakdown"]["ak47"]["kills"] == 6
    assert profile["weapon_breakdown"]["ak47"]["headshot_percent"] == 50
    assert profile["data_gaps"]


def test_match_aim_profile_reads_raw_payload():
    match = Match(
        source="demo",
        external_match_id="m1",
        adr=90,
        kd=1.4,
        headshot_percent=50,
        entry_kills=2,
        entry_deaths=1,
        raw_json=json.dumps(
            {
                "aim_summary": {"damage_per_death": 120, "multi_kill_rounds": 2},
                "weapon_breakdown": {
                    "ak47": {"weapon": "ak47", "kills": 4, "headshots": 2, "deaths": 1, "damage": 350}
                },
            }
        ),
    )

    profile = match_aim_profile(match)

    assert profile["damage_per_death"] == 120
    assert profile["opening_duel_success"] == 66.67
    assert profile["top_weapons"][0]["weapon"] == "ak47"
