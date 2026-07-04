#!/usr/bin/env python3
"""Read-only project gate helper for governance passes."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "cs2_coach.db"


GUARDIAN_RULES = [
    ("DB_GUARDIAN", ("app/db/*", "data/*.db"), ()),
    ("DB_GUARDIAN", ("app/services/auth.py",), ()),
    ("RUNTIME_GUARDIAN", ("app/web/*", "app/templates/*", "app/static/*"), ()),
    ("TEST_GUARDIAN", ("tests/*",), ()),
    (
        "IMPORT_GUARDIAN",
        (
            "app/services/steam_integration.py",
            "app/services/demo_parser.py",
            "app/web/*import*",
            "app/web/*upload*",
            "app/templates/*import*",
            "app/templates/*upload*",
        ),
        (),
    ),
    (
        "METRICS_GUARDIAN",
        (
            "app/services/metric_truth.py",
            "app/services/ai_coach.py",
            "docs/METRICS",
            "docs/RECOMMENDATIONS",
            "tests/test_metric",
            "tests/test_ai",
            "tests/test_recommendation",
        ),
        (),
    ),
]


CHECKS = {
    "PM_ORCHESTRATOR": [
        "python scripts/project_gate.py preflight",
        "python scripts/project_gate.py changed",
        "python scripts/project_gate.py required-checks",
        "python scripts/project_gate.py postflight",
        "git diff --check",
    ],
    "DB_GUARDIAN": [
        "sha256sum data/cs2_coach.db before/after",
        "APP_ENV=test .venv/bin/pytest tests -q",
        "confirm production DB touched yes/no",
    ],
    "RUNTIME_GUARDIAN": [
        "systemctl status jc-coach --no-pager when available",
        "targeted web/template tests for touched runtime paths",
        "runtime smoke only when authorized",
    ],
    "TEST_GUARDIAN": [
        "APP_ENV=test .venv/bin/pytest tests -q",
        ".venv/bin/ruff check .",
        "git diff --check",
    ],
    "IMPORT_GUARDIAN": [
        "mocked import/Steam/parser tests only unless live work is authorized",
        "confirm live AI/Steam/import/parser jobs run yes/no",
        "confirm Steam cursor/production DB mutation yes/no",
    ],
    "METRICS_GUARDIAN": [
        "metric truth / AI validator / recommendation evidence tests as applicable",
        "confirm no unsupported metric claims",
        "confirm live AI calls yes/no",
    ],
    "UI_COACH_GUARDIAN": [
        "coach UI targeted tests when /coach changes",
        "recommendation read/write no-mutation tests when route behavior changes",
        "runtime freshness smoke after authorized restart/deploy",
    ],
}


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def print_command(title: str, command: list[str]) -> None:
    print(f"## {title}")
    result = run(command)
    output = result.stdout.strip()
    if output:
        print(output)
    else:
        print("(no output)")
    if result.returncode != 0:
        print(f"EXIT_CODE={result.returncode}")
    print()


def db_sha() -> str:
    if not DB_PATH.exists():
        return "MISSING"
    digest = hashlib.sha256()
    with DB_PATH.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"{digest.hexdigest()}  data/cs2_coach.db"


def changed_files() -> list[str]:
    result = run(["git", "status", "--short", "-uall"])
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def activates(path: str, prefixes: tuple[str, ...], excludes: tuple[str, ...]) -> bool:
    if any(fnmatch.fnmatch(path, exclude) for exclude in excludes):
        return False
    return any(fnmatch.fnmatch(path, pattern) for pattern in prefixes)


def infer_guardians(paths: list[str]) -> list[str]:
    guardians = {"PM_ORCHESTRATOR"}
    for path in paths:
        normalized = path.lstrip("/")
        for guardian, prefixes, excludes in GUARDIAN_RULES:
            if activates(normalized, prefixes, excludes):
                guardians.add(guardian)
        if "coach" in normalized.lower() and (
            normalized.startswith("app/web/")
            or normalized.startswith("app/templates/")
            or normalized.startswith("app/static/")
            or normalized.startswith("tests/")
            or normalized.startswith("docs/")
        ):
            guardians.add("UI_COACH_GUARDIAN")
        if "metric" in normalized.lower() or "recommendation" in normalized.lower():
            guardians.add("METRICS_GUARDIAN")
        if "import" in normalized.lower() or "upload" in normalized.lower():
            guardians.add("IMPORT_GUARDIAN")
    return sorted(guardians)


def preflight(_: argparse.Namespace) -> int:
    print_command("git status --short", ["git", "status", "--short"])
    print_command("git log --oneline -12", ["git", "log", "--oneline", "-12"])
    print("## DB SHA")
    print(db_sha())
    print()
    print("## service status")
    if shutil.which("systemctl"):
        print_command("systemctl status jc-coach --no-pager", ["systemctl", "status", "jc-coach", "--no-pager"])
    else:
        print("systemctl not available")
        print()
    return 0


def changed(_: argparse.Namespace) -> int:
    paths = changed_files()
    print("## changed/untracked files")
    if paths:
        for path in paths:
            print(path)
    else:
        print("(none)")
    print()
    print("## activated guardians")
    for guardian in infer_guardians(paths):
        print(guardian)
    return 0


def required_checks(_: argparse.Namespace) -> int:
    guardians = infer_guardians(changed_files())
    print("## required checks by activated guardian")
    for guardian in guardians:
        print(f"{guardian}:")
        for check in CHECKS.get(guardian, []):
            print(f"- {check}")
    return 0


def postflight(_: argparse.Namespace) -> int:
    print_command("git diff --stat", ["git", "diff", "--stat"])
    print("## DB SHA")
    print(db_sha())
    print()
    print("## reminder")
    print("- Run safe tests with APP_ENV=test before claiming completion.")
    print("- Run runtime smoke only when authorized and report service restart yes/no.")
    print("- Report production DB touched yes/no and live jobs run yes/no.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only project governance gate.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    commands = {
        "preflight": preflight,
        "changed": changed,
        "required-checks": required_checks,
        "postflight": postflight,
    }
    for name in commands:
        subparsers.add_parser(name)
    args = parser.parse_args()
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
