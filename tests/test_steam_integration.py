from app.db.models import ImportJob, SteamAccount
from app.services.steam_integration import (
    create_steam_import_job,
    extract_steam_id,
    link_steam_account,
    parse_share_code_input,
    steam_login_url,
)


def test_steam_login_url_contains_openid_fields(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://example.test")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        url = steam_login_url()
    finally:
        get_settings.cache_clear()

    assert "steamcommunity.com/openid/login" in url
    assert "openid.mode=checkid_setup" in url
    assert "openid.return_to=" in url


def test_extract_steam_id_from_claimed_id():
    assert extract_steam_id("https://steamcommunity.com/openid/id/76561198056634139") == "76561198056634139"
    assert extract_steam_id("https://example.com/not-steam/1") is None


def test_link_steam_account_is_idempotent(db):
    first = link_steam_account(db, "76561198056634139", persona_name="JC")
    second = link_steam_account(db, "76561198056634139", persona_name="JC2")

    assert first.id == second.id
    assert db.query(SteamAccount).count() == 1
    assert second.persona_name == "JC2"


def test_create_steam_import_job(db):
    job = create_steam_import_job(db, None, "share_code_import", {"share_code": "CSGO-abc"})

    assert job.id is not None
    assert job.provider == "steam"
    assert job.status == "queued"
    assert db.query(ImportJob).count() == 1


def test_parse_share_code_input_accepts_plain_and_url():
    assert parse_share_code_input("CSGO-abc") == {"share_code": "CSGO-abc"}
    assert parse_share_code_input("https://example.test/?code=CSGO-def") == {"share_code": "CSGO-def"}
