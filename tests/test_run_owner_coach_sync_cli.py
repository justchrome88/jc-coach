from __future__ import annotations

import json

from scripts import run_owner_coach_sync as cli


class _DummySession:
    def close(self) -> None:
        return None


def test_cli_writes_valid_json_and_passes_only_explicit_service_inputs(monkeypatch, tmp_path, capsys):
    output = tmp_path / "owner-sync.json"
    calls = []
    result = _result("success_no_changes")
    monkeypatch.setattr(cli, "SessionLocal", _DummySession)

    def run(db, **kwargs):
        calls.append(kwargs)
        return result

    monkeypatch.setattr(cli, "run_owner_coach_sync", run)

    exit_code = cli.main(
        [
            "--owner-user-id",
            "7",
            "--max-new-matches",
            "3",
            "--dry-run",
            "--strict",
            "--specific-sharecode",
            "CSGO-fixture",
            "--output-json",
            str(output),
        ]
    )

    assert exit_code == 0
    assert calls == [
        {
            "owner_user_id": 7,
            "max_new_matches": 3,
            "dry_run": True,
            "continue_on_match_error": False,
            "specific_sharecode": "CSGO-fixture",
        }
    ]
    assert json.loads(output.read_text(encoding="utf-8")) == result
    assert "status=success_no_changes" in capsys.readouterr().out


def test_cli_returns_nonzero_for_failed_blocked_and_already_running(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "SessionLocal", _DummySession)
    statuses = {
        "failed": cli.FAILED_EXIT,
        "blocked": cli.FAILED_EXIT,
        "already_running": cli.ALREADY_RUNNING_EXIT,
    }
    for status, expected_exit in statuses.items():
        monkeypatch.setattr(cli, "run_owner_coach_sync", lambda db, _status=status, **kwargs: _result(_status))
        output = tmp_path / f"{status}.json"
        assert (
            cli.main(
                [
                    "--owner-user-id",
                    "7",
                    "--continue-on-match-error",
                    "--output-json",
                    str(output),
                ]
            )
            == expected_exit
        )
        assert json.loads(output.read_text(encoding="utf-8"))["run"]["status"] == status


def _result(status: str) -> dict:
    return {
        "schema_version": "owner-coach-sync-result-v1",
        "run": {"status": status, "owner_user_id": 7},
        "discovery": {},
        "matches": [],
        "totals": {"discovered": 0, "new": 0, "reused": 0, "skipped": 0, "failed": 0},
        "coach": {"active_missions": [], "latest_progress": [], "recommendation_suppression": {}},
        "mutations": {},
        "warnings": [],
        "errors": [],
    }
