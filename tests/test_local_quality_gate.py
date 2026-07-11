from scripts import local_quality_gate


class FakeProcess:
    def __init__(self, returncode=0, polls_before_done=0):
        self.returncode = returncode
        self.polls_before_done = polls_before_done
        self.poll_count = 0
        self.terminated = False
        self.killed = False

    def poll(self):
        if self.poll_count < self.polls_before_done:
            self.poll_count += 1
            return None
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_local_quality_gate_runs_required_commands_in_order(monkeypatch):
    calls = []

    def fake_popen(command, **kwargs):
        calls.append((tuple(command), kwargs))
        return FakeProcess()

    monkeypatch.setattr(local_quality_gate.subprocess, "Popen", fake_popen)

    assert local_quality_gate.main() == 0

    assert [command for command, _kwargs in calls] == [
        (".venv/bin/python", "scripts/project_gate.py", "preflight"),
        (".venv/bin/python", "scripts/project_gate.py", "changed"),
        (".venv/bin/python", "scripts/project_gate.py", "required-checks"),
        (".venv/bin/python", "scripts/r02a2_repository_guardrails.py"),
        (".venv/bin/python", "scripts/architecture_guardrails.py"),
        (".venv/bin/pytest", "tests/test_semantic_ai_eval.py", "-q", "-p", "no:cacheprovider"),
        (".venv/bin/pytest", "tests/test_metrics_c2_fixtures.py", "-q", "-p", "no:cacheprovider"),
        (".venv/bin/pytest", "tests", "-q", "-p", "no:cacheprovider"),
        (".venv/bin/ruff", "check", ".", "--no-cache"),
        ("git", "diff", "--check"),
        (".venv/bin/python", "scripts/project_gate.py", "postflight"),
    ]
    assert all(kwargs["cwd"] == local_quality_gate.ROOT for _command, kwargs in calls)
    assert all(kwargs["text"] is True for _command, kwargs in calls)


def test_local_quality_gate_sets_safe_pytest_environment(monkeypatch):
    calls = []

    def fake_popen(command, **kwargs):
        calls.append((tuple(command), kwargs))
        return FakeProcess()

    monkeypatch.setattr(local_quality_gate.subprocess, "Popen", fake_popen)
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

    def fake_popen(command, **kwargs):
        calls.append(tuple(command))
        returncode = 2 if tuple(command) == (".venv/bin/ruff", "check", ".", "--no-cache") else 0
        return FakeProcess(returncode=returncode)

    monkeypatch.setattr(local_quality_gate.subprocess, "Popen", fake_popen)

    assert local_quality_gate.main() == 2

    output = capsys.readouterr().out
    assert "## ruff" in output
    assert "RESULT: FAIL exit=2" in output
    assert "LOCAL_QUALITY_GATE=FAIL first_failure=2" in output
    assert calls[-1] == (".venv/bin/python", "scripts/project_gate.py", "postflight")


def test_local_quality_gate_logs_step_start_end_and_heartbeat(monkeypatch, capsys):
    process = FakeProcess(polls_before_done=1)

    monkeypatch.setattr(
        local_quality_gate,
        "COMMANDS",
        (
            local_quality_gate.CommandSpec(
                name="slow visible command",
                command=("example",),
                timeout_seconds=300,
            ),
        ),
    )
    monkeypatch.setattr(local_quality_gate.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monotonic_values = iter([0, local_quality_gate.HEARTBEAT_SECONDS + 1, 32, 32])
    monkeypatch.setattr(local_quality_gate.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(local_quality_gate.time, "sleep", lambda _seconds: None)

    assert local_quality_gate.main() == 0

    output = capsys.readouterr().out
    assert "STEP_START name='slow visible command'" in output
    assert "STEP_HEARTBEAT name='slow visible command'" in output
    assert "STEP_END name='slow visible command'" in output


def test_local_quality_gate_times_out_running_command(monkeypatch, capsys):
    process = FakeProcess(polls_before_done=999)

    monkeypatch.setattr(
        local_quality_gate,
        "COMMANDS",
        (
            local_quality_gate.CommandSpec(
                name="stuck command",
                command=("example",),
                timeout_seconds=300,
            ),
        ),
    )
    monkeypatch.setattr(local_quality_gate.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monotonic_values = iter([0, 301, 301])
    monkeypatch.setattr(local_quality_gate.time, "monotonic", lambda: next(monotonic_values))

    assert local_quality_gate.main() == 124

    output = capsys.readouterr().out
    assert process.terminated is True
    assert "STEP_TIMEOUT name='stuck command'" in output
    assert "RESULT: FAIL timeout exit=124" in output
    assert "LOCAL_QUALITY_GATE=FAIL first_failure=124" in output
