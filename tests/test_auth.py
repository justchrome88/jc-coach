from app.services.auth import authenticate_user, register_user, verify_password


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
        assert "уже есть" in str(exc)
    else:
        raise AssertionError("duplicate email should be rejected")
