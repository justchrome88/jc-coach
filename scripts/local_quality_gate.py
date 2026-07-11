#!/usr/bin/env python3
"""Run the standard local quality gate from the repository root."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STEP_TIMEOUT_SECONDS = 300
HEARTBEAT_SECONDS = 30
POLL_SECONDS = 1
TERMINATE_GRACE_SECONDS = 5
SAFE_PYTEST_ENV = {
    "APP_ENV": "test",
    "PYTHONDONTWRITEBYTECODE": "1",
}


@dataclass(frozen=True)
class CommandSpec:
    name: str
    command: tuple[str, ...]
    env: dict[str, str] | None = None
    timeout_seconds: int = DEFAULT_STEP_TIMEOUT_SECONDS


COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec(
        name="project gate preflight",
        command=(".venv/bin/python", "scripts/project_gate.py", "preflight"),
    ),
    CommandSpec(
        name="project gate changed",
        command=(".venv/bin/python", "scripts/project_gate.py", "changed"),
    ),
    CommandSpec(
        name="project gate required checks",
        command=(".venv/bin/python", "scripts/project_gate.py", "required-checks"),
    ),
    CommandSpec(
        name="R02A2 repository guardrails",
        command=(".venv/bin/python", "scripts/r02a2_repository_guardrails.py"),
    ),
    CommandSpec(
        name="service architecture guardrails",
        command=(".venv/bin/python", "scripts/architecture_guardrails.py"),
    ),
    CommandSpec(
        name="semantic AI eval fixtures",
        command=(
            ".venv/bin/pytest",
            "tests/test_semantic_ai_eval.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ),
        env=SAFE_PYTEST_ENV,
    ),
    CommandSpec(
        name="golden metric readiness fixtures",
        command=(
            ".venv/bin/pytest",
            "tests/test_metrics_c2_fixtures.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ),
        env=SAFE_PYTEST_ENV,
    ),
    CommandSpec(
        name="full safe pytest",
        command=(
            ".venv/bin/pytest",
            "tests",
            "-q",
            "-p",
            "no:cacheprovider",
        ),
        env=SAFE_PYTEST_ENV,
    ),
    CommandSpec(
        name="ruff",
        command=(".venv/bin/ruff", "check", ".", "--no-cache"),
    ),
    CommandSpec(
        name="git diff check",
        command=("git", "diff", "--check"),
    ),
    CommandSpec(
        name="project gate postflight",
        command=(".venv/bin/python", "scripts/project_gate.py", "postflight"),
    ),
)


def display_command(spec: CommandSpec) -> str:
    env_prefix = ""
    if spec.env:
        env_prefix = " ".join(f"{key}={value}" for key, value in spec.env.items())
        env_prefix = f"{env_prefix} "
    return f"{env_prefix}{' '.join(spec.command)}"


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def format_elapsed(seconds: float) -> str:
    return f"{seconds:.1f}s"


def stop_timed_out_process(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def run_command(spec: CommandSpec) -> int:
    print(f"## {spec.name}", flush=True)
    print(f"$ {display_command(spec)}", flush=True)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if spec.env is not None:
        env.update(spec.env)
    started_at = time.monotonic()
    next_heartbeat_at = started_at + HEARTBEAT_SECONDS
    print(
        f"STEP_START name={spec.name!r} at={timestamp()} "
        f"timeout={spec.timeout_seconds}s",
        flush=True,
    )
    try:
        process = subprocess.Popen(
            list(spec.command),
            cwd=ROOT,
            env=env,
            text=True,
        )
    except OSError as exc:
        print(f"FAILED_TO_START: {exc}", flush=True)
        print("RESULT: FAIL exit=127", flush=True)
        print(flush=True)
        return 127

    while True:
        returncode = process.poll()
        now = time.monotonic()
        elapsed = now - started_at
        if returncode is not None:
            break
        if elapsed >= spec.timeout_seconds:
            print(
                f"STEP_TIMEOUT name={spec.name!r} elapsed={format_elapsed(elapsed)} "
                f"timeout={spec.timeout_seconds}s",
                flush=True,
            )
            stop_timed_out_process(process)
            print(
                f"STEP_END name={spec.name!r} at={timestamp()} "
                f"elapsed={format_elapsed(time.monotonic() - started_at)}",
                flush=True,
            )
            print("RESULT: FAIL timeout exit=124", flush=True)
            print(flush=True)
            return 124
        if now >= next_heartbeat_at:
            print(
                f"STEP_HEARTBEAT name={spec.name!r} "
                f"elapsed={format_elapsed(elapsed)}",
                flush=True,
            )
            next_heartbeat_at += HEARTBEAT_SECONDS
        time.sleep(POLL_SECONDS)

    print(
        f"STEP_END name={spec.name!r} at={timestamp()} "
        f"elapsed={format_elapsed(time.monotonic() - started_at)}",
        flush=True,
    )
    if returncode == 0:
        print("RESULT: PASS", flush=True)
    else:
        print(f"RESULT: FAIL exit={returncode}", flush=True)
    print(flush=True)
    return returncode


def main() -> int:
    first_failure = 0
    print(f"LOCAL_QUALITY_GATE_ROOT={ROOT}", flush=True)
    print(flush=True)
    for spec in COMMANDS:
        returncode = run_command(spec)
        if returncode != 0 and first_failure == 0:
            first_failure = returncode

    if first_failure == 0:
        print("LOCAL_QUALITY_GATE=PASS", flush=True)
        return 0

    print(f"LOCAL_QUALITY_GATE=FAIL first_failure={first_failure}", flush=True)
    return first_failure


if __name__ == "__main__":
    raise SystemExit(main())
