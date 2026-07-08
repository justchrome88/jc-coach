import hashlib
import subprocess
from pathlib import Path

from scripts import project_gate


def run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, stdout=subprocess.PIPE)


def make_gate_fixture(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    run_git(root, "init")
    run_git(root, "config", "user.email", "test@example.test")
    run_git(root, "config", "user.name", "Test User")

    for relative_path in project_gate.GOVERNANCE_FILES:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{relative_path}\n", encoding="utf-8")

    db_path = root / "data" / "cs2_coach.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"fixture-db")

    run_git(root, "add", ".")
    run_git(root, "commit", "-m", "initial")

    monkeypatch.setattr(project_gate, "ROOT", root)
    monkeypatch.setattr(project_gate, "DB_PATH", db_path)
    return root


def test_db_sha_reads_configured_db_path(tmp_path, monkeypatch):
    make_gate_fixture(tmp_path, monkeypatch)

    expected = hashlib.sha256(b"fixture-db").hexdigest()

    assert project_gate.db_sha() == f"{expected}  data/cs2_coach.db"


def test_changed_lists_untracked_paths_and_activated_guardians(tmp_path, monkeypatch, capsys):
    root = make_gate_fixture(tmp_path, monkeypatch)
    (root / "scripts").mkdir()
    (root / "tests").mkdir()
    (root / "scripts" / "project_gate.py").write_text("print('changed')\n", encoding="utf-8")
    (root / "tests" / "test_project_gate.py").write_text("def test_new(): pass\n", encoding="utf-8")
    report = (
        root
        / "docs"
        / "foundation_hardening"
        / "2026-07-06-readiness-recovery-plan"
        / "task_reports"
        / "FH-020_report.md"
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("report\n", encoding="utf-8")

    assert project_gate.changed(project_gate.argparse.Namespace()) == 0

    output = capsys.readouterr().out
    assert "scripts/project_gate.py" in output
    assert "tests/test_project_gate.py" in output
    assert "FH-020_report.md" in output
    assert "DOCUMENTATION_STEWARD" in output
    assert "PM_ORCHESTRATOR" in output
    assert "TEST_GUARDIAN" in output


def test_required_checks_include_full_local_gate_for_script_changes(tmp_path, monkeypatch, capsys):
    root = make_gate_fixture(tmp_path, monkeypatch)
    (root / "scripts").mkdir()
    (root / "scripts" / "project_gate.py").write_text("print('changed')\n", encoding="utf-8")

    assert project_gate.required_checks(project_gate.argparse.Namespace()) == 0

    output = capsys.readouterr().out
    assert ".venv/bin/python scripts/project_gate.py preflight" in output
    assert "APP_ENV=test PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests -q" in output
    assert ".venv/bin/ruff check . --no-cache" in output
    assert "REQUIRED: git diff --check" in output


def test_preflight_includes_start_evidence_without_service_probe(tmp_path, monkeypatch, capsys):
    make_gate_fixture(tmp_path, monkeypatch)

    assert project_gate.preflight(project_gate.argparse.Namespace()) == 0

    output = capsys.readouterr().out
    assert "## task context" in output
    assert "working_directory:" in output
    assert "## git status --short -uall" in output
    assert "## git log --oneline -12 --decorate" in output
    assert "AGENTS.md: present" in output
    assert "## production DB SHA" in output
    assert "systemctl" not in output
    assert "service status" not in output.lower()


def test_postflight_includes_changed_files_guardians_checks_and_db_sha(tmp_path, monkeypatch, capsys):
    root = make_gate_fixture(tmp_path, monkeypatch)
    (root / "tests").mkdir()
    (root / "tests" / "test_project_gate.py").write_text("def test_new(): pass\n", encoding="utf-8")

    assert project_gate.postflight(project_gate.argparse.Namespace()) == 0

    output = capsys.readouterr().out
    assert "## git diff --stat" in output
    assert "tests/test_project_gate.py" in output
    assert "TEST_GUARDIAN" in output
    assert "## required-check summary" in output
    assert "code/test/script change: yes" in output
    assert "## production DB SHA" in output
