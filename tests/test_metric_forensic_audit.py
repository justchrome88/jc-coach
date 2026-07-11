import json
import sqlite3
from pathlib import Path

import pytest

from scripts.audit_match_metrics import build_ledger


def _artifact_payload() -> dict:
    if not Path("data/cs2_coach.db").exists():
        pytest.skip("retained H01A production artifact is not present")
    connection = sqlite3.connect("file:data/cs2_coach.db?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT payload_json FROM demo_parse_artifacts WHERE id = 91").fetchone()
    finally:
        connection.close()
    if row is None:
        pytest.skip("retained H01A parser artifact 91 is not present")
    return json.loads(row[0])


def test_match_124_ledger_is_deterministic_and_excludes_post_match_self_kill() -> None:
    first = build_ledger(_artifact_payload(), "76561198056634139")
    second = build_ledger(_artifact_payload(), "76561198056634139")

    assert first == second
    assert first["totals"]["kills"] == 16
    assert first["totals"]["deaths"] == 10
    assert first["totals"]["assists"] == 4
    assert first["totals"]["headshot_kills"] == 10
    assert first["totals"]["enemy_damage_raw"] == 2165
    assert first["totals"]["team_damage_raw"] == 5
    assert first["rows"][20]["round_classification"] == "post_match"
    assert first["rows"][20]["deaths"] == 1
