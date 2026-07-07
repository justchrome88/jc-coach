#!/usr/bin/env python3
"""Run the standard local quality gate from the repository root."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CommandSpec:
    name: str
    command: tuple[str, ...]
    env: dict[str, str] | None = None


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
        name="full safe pytest",
        command=(
            ".venv/bin/pytest",
            "tests",
            "-q",
            "-p",
            "no:cacheprovider",
        ),
        env={
            "APP_ENV": "test",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
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


def run_command(spec: CommandSpec) -> int:
    print(f"## {spec.name}", flush=True)
    print(f"$ {display_command(spec)}", flush=True)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if spec.env is not None:
        env.update(spec.env)
    try:
        result = subprocess.run(
            list(spec.command),
            cwd=ROOT,
            env=env,
            text=True,
            check=False,
        )
    except OSError as exc:
        print(f"FAILED_TO_START: {exc}", flush=True)
        print("RESULT: FAIL exit=127", flush=True)
        print(flush=True)
        return 127

    if result.returncode == 0:
        print("RESULT: PASS", flush=True)
    else:
        print(f"RESULT: FAIL exit={result.returncode}", flush=True)
    print(flush=True)
    return result.returncode


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
