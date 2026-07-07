import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import PRODUCTION_DB_PATH, Settings, _assert_safe_test_settings
from scripts import schema_baseline_gate

ROOT = Path(__file__).resolve().parents[1]


def _run_script(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    merged_env["PYTHON"] = sys.executable
    return subprocess.run(
        ["bash", str(ROOT / "scripts" / script)],
        cwd=ROOT,
        env=merged_env,
        check=False,
        text=True,
        capture_output=True,
    )


def _create_minimal_sqlite(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE existing_table (id INTEGER PRIMARY KEY, value TEXT)")
        connection.commit()
    finally:
        connection.close()


def test_test_environment_rejects_production_database_url_for_migrations():
    settings = Settings(app_env="test", database_url=f"sqlite:///{PRODUCTION_DB_PATH}")

    with pytest.raises(RuntimeError):
        _assert_safe_test_settings(settings)


def test_migration_status_reads_temp_db_without_mutating(tmp_path):
    db_path = tmp_path / "status.db"
    _create_minimal_sqlite(db_path)
    before = db_path.read_bytes()

    result = _run_script("migration_status.sh", {"DB_PATH": str(db_path)})

    assert result.returncode == 0, result.stderr
    assert "MIGRATION_STATUS_INTEGRITY=ok" in result.stdout
    assert "existing_table" in result.stdout
    assert db_path.read_bytes() == before


def test_migration_check_on_copy_runs_against_copy_and_keeps_source_unchanged(tmp_path):
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    _create_minimal_sqlite(source_db)
    before = source_db.read_bytes()

    result = _run_script("migration_check_on_copy.sh", {"SOURCE_DB": str(source_db), "TARGET_DB": str(target_db)})

    assert result.returncode == 0, result.stderr
    assert "MIGRATION_COPY_CHECK_RESULT=ok" in result.stdout
    assert source_db.read_bytes() == before
    assert target_db.exists()


def test_migration_check_refuses_to_use_source_as_target(tmp_path):
    source_db = tmp_path / "source.db"
    _create_minimal_sqlite(source_db)

    result = _run_script("migration_check_on_copy.sh", {"SOURCE_DB": str(source_db), "TARGET_DB": str(source_db)})

    assert result.returncode == 3
    assert "target_must_not_equal_source" in result.stderr


def test_migration_scripts_are_shell_parseable():
    for script in ("migration_status.sh", "migration_check_on_copy.sh"):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / "scripts" / script)],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr


def test_migration_check_uses_explicit_temp_source_not_production_db(tmp_path):
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    _create_minimal_sqlite(source_db)

    result = _run_script("migration_check_on_copy.sh", {"SOURCE_DB": str(source_db), "TARGET_DB": str(target_db)})

    assert result.returncode == 0, result.stderr
    assert f"MIGRATION_COPY_CHECK_SOURCE={source_db}" in result.stdout


def _run_schema_gate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "schema_baseline_gate.py"), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def test_schema_baseline_is_deterministic_and_excludes_row_data(tmp_path):
    db_path = tmp_path / "schema.db"
    _create_minimal_sqlite(db_path)
    first = schema_baseline_gate.build_baseline(db_path)

    connection = sqlite3.connect(db_path)
    try:
        connection.execute("INSERT INTO existing_table (value) VALUES ('row data excluded')")
        connection.commit()
    finally:
        connection.close()

    second = schema_baseline_gate.build_baseline(db_path)

    assert first == second
    assert "row data excluded" not in schema_baseline_gate.canonical_json(second)


def test_schema_gate_matches_written_baseline(tmp_path):
    db_path = tmp_path / "schema.db"
    baseline_path = tmp_path / "baseline.json"
    _create_minimal_sqlite(db_path)

    write_result = _run_schema_gate("write-baseline", "--db-path", str(db_path), "--output", str(baseline_path))
    check_result = _run_schema_gate("check", "--db-path", str(db_path), "--baseline", str(baseline_path))

    assert write_result.returncode == 0, write_result.stderr
    assert "SCHEMA_BASELINE_RESULT=written" in write_result.stdout
    assert check_result.returncode == 0, check_result.stderr
    assert "SCHEMA_GATE_RESULT=match" in check_result.stdout


def test_schema_gate_exits_nonzero_on_schema_mismatch(tmp_path):
    db_path = tmp_path / "schema.db"
    baseline_path = tmp_path / "baseline.json"
    _create_minimal_sqlite(db_path)

    write_result = _run_schema_gate("write-baseline", "--db-path", str(db_path), "--output", str(baseline_path))
    assert write_result.returncode == 0, write_result.stderr

    connection = sqlite3.connect(db_path)
    try:
        connection.execute("ALTER TABLE existing_table ADD COLUMN drift TEXT")
        connection.commit()
    finally:
        connection.close()

    check_result = _run_schema_gate("check", "--db-path", str(db_path), "--baseline", str(baseline_path))

    assert check_result.returncode == 1
    assert "SCHEMA_GATE_RESULT=mismatch" in check_result.stdout
    assert "SCHEMA_GATE_DIFF_BEGIN" in check_result.stdout
    assert '"name": "drift"' in check_result.stdout
