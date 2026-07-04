import os

import pytest

from app.config import (
    PRODUCTION_DB_PATH,
    Settings,
    _assert_safe_test_settings,
    _sqlite_database_path,
    assert_test_database_not_production,
    database_url_points_to_production,
)


def test_test_environment_rejects_production_database_url():
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{PRODUCTION_DB_PATH}",
    )

    with pytest.raises(RuntimeError):
        _assert_safe_test_settings(settings)


def test_database_url_points_to_production_detects_resolved_path():
    assert database_url_points_to_production(f"sqlite:///{PRODUCTION_DB_PATH}")


def test_assert_test_database_not_production_rejects_production_url():
    with pytest.raises(RuntimeError, match="test helpers cannot use the production database"):
        assert_test_database_not_production(f"sqlite:///{PRODUCTION_DB_PATH}", context="pytest configuration")


def test_conftest_isolation_uses_test_env_and_non_production_db():
    assert os.environ["APP_ENV"] == "test"
    assert _sqlite_database_path(os.environ["DATABASE_URL"]) != PRODUCTION_DB_PATH
