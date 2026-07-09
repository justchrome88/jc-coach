import ast
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import PRODUCTION_DB_PATH, Settings, _assert_safe_test_settings
from scripts import schema_baseline_gate

ROOT = Path(__file__).resolve().parents[1]

LEGACY_STARTUP_SCHEMA_SQL = {
    "ALTER TABLE matches ADD COLUMN early_deaths INTEGER",
    "ALTER TABLE matches ADD COLUMN swing_score FLOAT",
    "ALTER TABLE matches ADD COLUMN user_id INTEGER",
    "ALTER TABLE matches ADD COLUMN steam_account_id INTEGER",
    "ALTER TABLE matches ADD COLUMN import_job_id INTEGER",
    "ALTER TABLE coach_reports ADD COLUMN report_type VARCHAR(50) DEFAULT 'rule_based' NOT NULL",
    "ALTER TABLE coach_reports ADD COLUMN source_ref VARCHAR(500)",
    "ALTER TABLE coach_reports ADD COLUMN user_id INTEGER",
    "ALTER TABLE coach_reports ADD COLUMN source_metric_snapshot_id INTEGER",
    "ALTER TABLE users ADD COLUMN email VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN password_hash VARCHAR(500)",
    "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1 NOT NULL",
    "ALTER TABLE users ADD COLUMN last_login_at DATETIME",
    "ALTER TABLE coach_recommendations ADD COLUMN start_after_match_id INTEGER",
    "ALTER TABLE import_jobs ADD COLUMN user_id INTEGER",
    "ALTER TABLE import_jobs ADD COLUMN logical_target_key VARCHAR(500)",
    "ALTER TABLE import_jobs ADD COLUMN updated_at DATETIME",
    "ALTER TABLE demo_parse_artifacts ADD COLUMN import_job_id INTEGER",
}


def _startup_schema_mutation_sql() -> set[str]:
    source_path = ROOT / "app" / "db" / "session.py"
    module = ast.parse(source_path.read_text(encoding="utf-8"))
    upgrade_function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "_upgrade_sqlite_schema"
    )
    sql = set()
    for node in ast.walk(upgrade_function):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            statement = " ".join(node.value.split())
            statement_upper = statement.upper()
            if "ALTER TABLE" in statement_upper or "CREATE TABLE" in statement_upper:
                sql.add(statement)
    return sql


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


def _write_post_copy_schema_baseline(source_db: Path, tmp_path: Path) -> Path:
    target_db = tmp_path / f"{source_db.stem}-baseline-target.db"
    baseline_path = tmp_path / f"{source_db.stem}-baseline.json"
    shutil.copy2(source_db, target_db)
    env = os.environ.copy()
    env.update({"APP_ENV": "test", "DATABASE_URL": f"sqlite:///{target_db}"})
    result = subprocess.run(
        [sys.executable, "-c", "from app.db.session import init_db; init_db()"],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    baseline = schema_baseline_gate.build_baseline(target_db)
    baseline_path.write_text(schema_baseline_gate.canonical_json(baseline), encoding="utf-8")
    return baseline_path


def test_test_environment_rejects_production_database_url_for_migrations():
    settings = Settings(app_env="test", database_url=f"sqlite:///{PRODUCTION_DB_PATH}")

    with pytest.raises(RuntimeError):
        _assert_safe_test_settings(settings)


def test_startup_schema_helper_only_contains_accepted_legacy_sql():
    assert _startup_schema_mutation_sql() == LEGACY_STARTUP_SCHEMA_SQL, (
        "Do not add startup schema mutations to app/db/session.py::_upgrade_sqlite_schema() "
        "without an explicit schema-changing WP approval."
    )


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
    baseline_path = _write_post_copy_schema_baseline(source_db, tmp_path)
    before = source_db.read_bytes()

    result = _run_script(
        "migration_check_on_copy.sh",
        {"SOURCE_DB": str(source_db), "TARGET_DB": str(target_db), "SCHEMA_BASELINE": str(baseline_path)},
    )

    assert result.returncode == 0, result.stderr
    assert "MIGRATION_COPY_CHECK_RESULT=ok" in result.stdout
    assert "SCHEMA_GATE_RESULT=match" in result.stdout
    assert source_db.read_bytes() == before
    assert target_db.exists()


def test_migration_check_refuses_to_use_source_as_target(tmp_path):
    source_db = tmp_path / "source.db"
    _create_minimal_sqlite(source_db)

    result = _run_script("migration_check_on_copy.sh", {"SOURCE_DB": str(source_db), "TARGET_DB": str(source_db)})

    assert result.returncode == 3
    assert "target_must_not_equal_source" in result.stderr


def test_migration_check_refuses_production_db_as_target(tmp_path):
    source_db = tmp_path / "source.db"
    _create_minimal_sqlite(source_db)
    before = source_db.read_bytes()

    result = _run_script(
        "migration_check_on_copy.sh",
        {"SOURCE_DB": str(source_db), "TARGET_DB": str(PRODUCTION_DB_PATH)},
    )

    assert result.returncode == 6
    assert "target_must_not_be_production_db" in result.stderr
    assert source_db.read_bytes() == before


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
    baseline_path = _write_post_copy_schema_baseline(source_db, tmp_path)

    result = _run_script(
        "migration_check_on_copy.sh",
        {"SOURCE_DB": str(source_db), "TARGET_DB": str(target_db), "SCHEMA_BASELINE": str(baseline_path)},
    )

    assert result.returncode == 0, result.stderr
    assert f"MIGRATION_COPY_CHECK_SOURCE={source_db}" in result.stdout


def test_migration_check_reports_schema_mismatch_from_copy(tmp_path):
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    _create_minimal_sqlite(source_db)
    baseline_path = _write_post_copy_schema_baseline(source_db, tmp_path)

    connection = sqlite3.connect(source_db)
    try:
        connection.execute("CREATE TABLE drift_table (id INTEGER PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()
    before = source_db.read_bytes()

    result = _run_script(
        "migration_check_on_copy.sh",
        {"SOURCE_DB": str(source_db), "TARGET_DB": str(target_db), "SCHEMA_BASELINE": str(baseline_path)},
    )

    assert result.returncode == 1
    assert "MIGRATION_COPY_CHECK_SOURCE_UNCHANGED=true" in result.stdout
    assert "SCHEMA_GATE_RESULT=mismatch" in result.stdout
    assert "SCHEMA_GATE_DIFF_BEGIN" in result.stdout
    assert '"name": "drift_table"' in result.stdout
    assert source_db.read_bytes() == before


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
