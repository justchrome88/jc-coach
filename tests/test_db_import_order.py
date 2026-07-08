import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

IMPORT_ORDER_SMOKE = textwrap.dedent(
    """
    import importlib
    import json
    import os

    from sqlalchemy import inspect

    from app.config import PRODUCTION_DB_PATH, assert_test_database_not_production

    database_url = os.environ["DATABASE_URL"]
    assert_test_database_not_production(database_url, context="DB import-order smoke")
    assert str(PRODUCTION_DB_PATH) not in database_url

    for module_name in json.loads(os.environ["DB_IMPORT_ORDER_MODULES"]):
        importlib.import_module(module_name)

    from app.db import models  # noqa: F401
    from app.db.session import Base, engine, init_db, settings

    assert settings.database_url == database_url
    init_db()

    expected_tables = set(Base.metadata.tables)
    actual_tables = set(inspect(engine).get_table_names())
    assert expected_tables
    assert expected_tables <= actual_tables
    """
)


@pytest.mark.parametrize(
    "module_order",
    (
        ("app.config", "app.db.session", "app.db.models"),
        ("app.config", "app.db.models", "app.db.session"),
        ("app.db.models", "app.db.session", "app.config"),
    ),
)
def test_db_session_and_models_import_order_is_stable_in_test_env(tmp_path, module_order):
    db_path = tmp_path / "import-order-smoke.db"
    runtime_root = tmp_path / "runtime"
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": f"sqlite:///{db_path}",
            "UPLOAD_DIR": str(runtime_root / "uploads"),
            "DEMO_INBOX_DIR": str(runtime_root / "incoming_demos"),
            "REPORTS_DIR": str(runtime_root / "reports"),
            "AI_HANDOFF_DIR": str(runtime_root / "ai_handoffs"),
            "SESSION_SECRET_KEY": "pytest-only-session-secret",
            "DB_IMPORT_ORDER_MODULES": json.dumps(module_order),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )

    result = subprocess.run(
        [sys.executable, "-c", IMPORT_ORDER_SMOKE],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
