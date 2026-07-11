import pytest

from app.config import Settings
from app.db.models import User
from app.services.owner.auth import authenticate_user, register_user, verify_password


def _settings(app_env: str, database_url: str = "sqlite:///:memory:") -> Settings:
    return Settings(app_env=app_env, database_url=database_url)


def test_register_and_authenticate_user(db):
    user = register_user(db, "USER@example.test", "strong-password", display_name="JC")

    assert user.email == "user@example.test"
    assert user.password_hash != "strong-password"
    assert verify_password("strong-password", user.password_hash)
    assert authenticate_user(db, "user@example.test", "strong-password").id == user.id
    assert authenticate_user(db, "user@example.test", "wrong-password") is None


def test_register_user_rejects_duplicate_email(db):
    register_user(db, "user@example.test", "strong-password")

    try:
        register_user(db, "USER@example.test", "strong-password")
    except ValueError as exc:
        assert "Регистрация закрыта" in str(exc)
    else:
        raise AssertionError("second registration should be rejected")


@pytest.mark.parametrize("email", ("test-abc@example.test", "smoke-abc@example.test"))
def test_register_user_rejects_test_smoke_email_outside_test_env(db, monkeypatch, email):
    monkeypatch.setattr("app.services.owner.auth.get_settings", lambda: _settings("local"))

    with pytest.raises(ValueError, match="Refusing to register test/smoke email outside APP_ENV=test"):
        register_user(db, email, "strong-password")

    assert db.query(User).count() == 0


def test_register_user_allows_normal_owner_email_outside_test_env(db, monkeypatch):
    monkeypatch.setattr("app.services.owner.auth.get_settings", lambda: _settings("local"))

    user = register_user(db, "owner@example.com", "strong-password", display_name="Owner")

    assert user.email == "owner@example.com"


@pytest.mark.parametrize("email", ("test-abc@example.test", "smoke-abc@example.test"))
def test_register_user_allows_test_smoke_email_only_in_test_env(db, monkeypatch, tmp_path, email):
    test_db_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setattr("app.services.owner.auth.get_settings", lambda: _settings("test", test_db_url))

    user = register_user(db, email, "strong-password")

    assert user.email == email
