import subprocess

from scripts import local_quality_gate


def test_local_quality_gate_runs_required_commands_in_order(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((tuple(command), kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(local_quality_gate.subprocess, "run", fake_run)

    assert local_quality_gate.main() == 0

    assert [command for command, _kwargs in calls] == [
        (".venv/bin/python", "scripts/project_gate.py", "preflight"),
        (".venv/bin/python", "scripts/project_gate.py", "changed"),
        (".venv/bin/python", "scripts/project_gate.py", "required-checks"),
        (".venv/bin/pytest", "tests/test_semantic_ai_eval.py", "-q", "-p", "no:cacheprovider"),
        (".venv/bin/pytest", "tests/test_metrics_c2_fixtures.py", "-q", "-p", "no:cacheprovider"),
        (".venv/bin/pytest", "tests", "-q", "-p", "no:cacheprovider"),
        (".venv/bin/ruff", "check", ".", "--no-cache"),
        ("git", "diff", "--check"),
        (".venv/bin/python", "scripts/project_gate.py", "postflight"),
    ]
    assert all(kwargs["cwd"] == local_quality_gate.ROOT for _command, kwargs in calls)
    assert all(kwargs["check"] is False for _command, kwargs in calls)


def test_local_quality_gate_sets_safe_pytest_environment(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((tuple(command), kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(local_quality_gate.subprocess, "run", fake_run)
    monkeypatch.setenv("APP_ENV", "local")

    assert local_quality_gate.main() == 0

    pytest_calls = [
        kwargs
        for command, kwargs in calls
        if command[0] == ".venv/bin/pytest"
    ]
    assert len(pytest_calls) == 3
    assert all(call["env"]["APP_ENV"] == "test" for call in pytest_calls)
    assert all(call["env"]["PYTHONDONTWRITEBYTECODE"] == "1" for call in pytest_calls)


def test_local_quality_gate_returns_nonzero_when_any_command_fails(monkeypatch, capsys):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(tuple(command))
        returncode = 2 if tuple(command) == (".venv/bin/ruff", "check", ".", "--no-cache") else 0
        return subprocess.CompletedProcess(command, returncode)

    monkeypatch.setattr(local_quality_gate.subprocess, "run", fake_run)

    assert local_quality_gate.main() == 2

    output = capsys.readouterr().out
    assert "## ruff" in output
    assert "RESULT: FAIL exit=2" in output
    assert "LOCAL_QUALITY_GATE=FAIL first_failure=2" in output
    assert calls[-1] == (".venv/bin/python", "scripts/project_gate.py", "postflight")
