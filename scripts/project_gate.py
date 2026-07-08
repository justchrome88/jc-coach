#!/usr/bin/env python3
"""Read-only project gate helper for task preflight and postflight evidence."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "cs2_coach.db"
DB_DISPLAY_PATH = "data/cs2_coach.db"
GOVERNANCE_FILES = (
    "AGENTS.md",
    "docs/CURRENT_STATUS.md",
    "docs/HANDOFF.md",
    "docs/project_management/WP_REGISTRY.md",
    "docs/project_management/AGENT_WORKFLOW.md",
    "docs/TESTING.md",
)


@dataclass(frozen=True)
class Change:
    status: str
    path: str


GUARDIAN_RULES = [
    ("DB_GUARDIAN", ("app/db/*", "data/*.db", "migrations/*", "alembic*"), ()),
    ("DB_GUARDIAN", ("app/services/auth.py", "app/config.py"), ()),
    (
        "RUNTIME_GUARDIAN",
        ("app/main.py", "app/web/*", "app/templates/*", "app/static/*"),
        (),
    ),
    ("TEST_GUARDIAN", ("tests/*", "scripts/*", "pyproject.toml"), ()),
    (
        "DOCUMENTATION_STEWARD",
        (
            "AGENTS.md",
            "AGENT.md",
            "docs/*",
        ),
        (),
    ),
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
    "PM_ORCHESTRATOR": {
        "required": [
            ".venv/bin/python scripts/project_gate.py preflight",
            ".venv/bin/python scripts/project_gate.py changed",
            ".venv/bin/python scripts/project_gate.py required-checks",
            ".venv/bin/python scripts/project_gate.py postflight",
            "git diff --check",
            "confirm no unauthorized git add/commit/push",
        ],
        "recommended": [
            "include initial git status, changed files, guardians and final git status in report"
        ],
    },
    "DB_GUARDIAN": {
        "required": [
            "sha256sum data/cs2_coach.db before/after for DB-impacting work",
            "confirm production DB touched yes/no",
            "confirm schema changed yes/no",
        ],
        "recommended": [
            "APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest "
            "tests/test_config.py tests/test_migrations.py -q -p no:cacheprovider"
        ],
    },
    "RUNTIME_GUARDIAN": {
        "required": [
            "targeted web/template tests for touched runtime paths",
            "confirm service/nginx/systemd/deploy changed yes/no",
            "runtime smoke only when explicitly authorized",
        ],
        "recommended": [
            "APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/test_web_smoke.py -q -p no:cacheprovider"
        ],
    },
    "TEST_GUARDIAN": {
        "required": [
            "APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q -p no:cacheprovider",
            ".venv/bin/ruff check . --no-cache",
            "git diff --check",
        ],
        "recommended": [
            "run focused tests for the changed test/script surface before the full suite"
        ],
    },
    "DOCUMENTATION_STEWARD": {
        "required": [
            "complete the report docs update checklist",
            "confirm Hot/current status docs updated or not required",
            "confirm navigation docs updated or not required",
        ],
        "recommended": [
            "check changed docs do not weaken AGENTS.md or control-plane policy"
        ],
    },
    "IMPORT_GUARDIAN": {
        "required": [
            "mocked import/Steam/parser tests only unless live work is authorized",
            "confirm live Steam/import/parser jobs run yes/no",
            "confirm Steam cursor/production DB mutation yes/no",
        ],
        "recommended": [
            "APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest "
            "tests/test_importer.py tests/test_steam_integration.py tests/test_demo_parser.py "
            "-q -p no:cacheprovider"
        ],
    },
    "METRICS_GUARDIAN": {
        "required": [
            "metric truth / AI validator / recommendation evidence tests as applicable",
            "confirm no unsupported metric or coach claims",
            "confirm live AI calls yes/no",
        ],
        "recommended": [
            "APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest "
            "tests/test_metric_truth.py tests/test_ai_validator.py "
            "tests/test_recommendation_tracking.py -q -p no:cacheprovider"
        ],
    },
    "UI_COACH_GUARDIAN": {
        "required": [
            "coach UI targeted tests when /coach changes",
            "recommendation read/write no-mutation tests when route behavior changes",
            "runtime freshness smoke only when authorized",
        ],
        "recommended": [
            "APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest "
            "tests/test_coach_first_ui.py -q -p no:cacheprovider"
        ],
    },
}


CODE_TEST_SCRIPT_PATTERNS = (
    "app/*",
    "scripts/*",
    "tests/*",
    "pyproject.toml",
)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def command_output(command: list[str]) -> str:
    result = run(command)
    output = result.stdout.strip()
    if output:
        return output
    if result.returncode != 0:
        return f"(no output; exit {result.returncode})"
    return "(no output)"


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
        return f"MISSING  {DB_DISPLAY_PATH}"
    digest = hashlib.sha256()
    with DB_PATH.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"{digest.hexdigest()}  {DB_DISPLAY_PATH}"


def git_status_entries() -> list[Change]:
    result = run(["git", "status", "--short", "-uall"])
    changes: list[Change] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changes.append(Change(status=status, path=path))
    return changes


def changed_files() -> list[str]:
    return [change.path for change in git_status_entries()]


def activates(path: str, prefixes: tuple[str, ...], excludes: tuple[str, ...]) -> bool:
    if any(fnmatch.fnmatch(path, exclude) for exclude in excludes):
        return False
    return any(fnmatch.fnmatch(path, pattern) for pattern in prefixes)


def has_code_test_script_change(paths: list[str]) -> bool:
    return any(
        any(fnmatch.fnmatch(path, pattern) for pattern in CODE_TEST_SCRIPT_PATTERNS)
        for path in paths
    )


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


def print_task_context() -> None:
    print("## task context")
    print(f"working_directory: {ROOT}")
    print(f"branch: {command_output(['git', 'branch', '--show-current'])}")
    print()


def print_governance_files() -> None:
    print("## governance files")
    for relative_path in GOVERNANCE_FILES:
        status = "present" if (ROOT / relative_path).exists() else "MISSING"
        print(f"{relative_path}: {status}")
    print()


def print_db_sha() -> None:
    print("## production DB SHA")
    print(db_sha())
    print()


def print_changed_entries(changes: list[Change]) -> None:
    print("## changed/untracked files")
    if changes:
        for change in changes:
            print(f"{change.status} {change.path}")
    else:
        print("(none)")
    print()


def print_activated_guardians(paths: list[str]) -> None:
    print("## activated guardians")
    for guardian in infer_guardians(paths):
        print(guardian)
    print()


def print_required_check_summary(paths: list[str]) -> None:
    guardians = infer_guardians(paths)
    print("## required-check summary")
    print(f"code/test/script change: {'yes' if has_code_test_script_change(paths) else 'no'}")
    print(f"activated guardians: {', '.join(guardians)}")
    print()


def print_required_checks_for(paths: list[str]) -> None:
    guardians = infer_guardians(paths)
    print("## mandatory local gate expectations")
    print("- .venv/bin/python scripts/project_gate.py preflight")
    print("- .venv/bin/python scripts/project_gate.py changed")
    print("- .venv/bin/python scripts/project_gate.py required-checks")
    print("- .venv/bin/python scripts/project_gate.py postflight")
    print("- git diff --check")
    if has_code_test_script_change(paths):
        print(
            "- APP_ENV=test PYTHONDONTWRITEBYTECODE=1 "
            ".venv/bin/pytest tests -q -p no:cacheprovider"
        )
        print("- .venv/bin/ruff check . --no-cache")
    print()

    print("## required checks by activated guardian")
    for guardian in guardians:
        print(f"{guardian}:")
        for check in CHECKS.get(guardian, {}).get("required", []):
            print(f"- REQUIRED: {check}")
        for check in CHECKS.get(guardian, {}).get("recommended", []):
            print(f"- RECOMMENDED: {check}")
    print()


def preflight(_: argparse.Namespace) -> int:
    print_task_context()
    print_command("git status --short -uall", ["git", "status", "--short", "-uall"])
    print_command("git log --oneline -12 --decorate", ["git", "log", "--oneline", "-12", "--decorate"])
    print_governance_files()
    print_db_sha()
    return 0


def changed(_: argparse.Namespace) -> int:
    changes = git_status_entries()
    paths = [change.path for change in changes]
    print_changed_entries(changes)
    print_activated_guardians(paths)
    return 0


def required_checks(_: argparse.Namespace) -> int:
    print_required_checks_for(changed_files())
    return 0


def postflight(_: argparse.Namespace) -> int:
    print_command("git diff --stat", ["git", "diff", "--stat"])
    changes = git_status_entries()
    paths = [change.path for change in changes]
    print_changed_entries(changes)
    print_activated_guardians(paths)
    print_required_check_summary(paths)
    print_governance_files()
    print_db_sha()
    print("## reminder")
    print("- Run safe tests with APP_ENV=test before claiming completion.")
    print("- Run runtime smoke only when explicitly authorized and report service restart yes/no.")
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
