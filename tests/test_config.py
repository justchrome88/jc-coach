import pytest

from app.config import PRODUCTION_DB_PATH, Settings, _assert_safe_test_settings


def test_test_environment_rejects_production_database_url():
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{PRODUCTION_DB_PATH}",
    )

    with pytest.raises(RuntimeError):
        _assert_safe_test_settings(settings)
