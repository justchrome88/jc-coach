from app.db.models import ImportJob, Match, SteamAccount
from app.services.steam_demo_downloader import download_pending_steam_demos, steam_demo_downloader_configured
from app.services.steam_integration import (
    clear_steam_demo_download_errors,
    create_steam_import_job,
    current_steam_import_all_job,
    decode_match_share_code,
    extract_steam_id,
    import_all_available_steam_matches,
    link_steam_account,
    mark_steam_history_demo_download_status,
    parse_share_code_input,
    queue_match_history_sync,
    queue_steam_import_all,
    run_steam_import_all_job,
    steam_import_overview,
    steam_login_url,
    sync_match_history_job,
    update_match_auth_code,
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


def test_queue_steam_import_all_is_idempotent_while_active(db):
    first = queue_steam_import_all(db)
    second = queue_steam_import_all(db)

    assert first.id == second.id
    assert first.status == "queued"
    assert current_steam_import_all_job(db).id == first.id
    assert db.query(ImportJob).count() == 1


def test_run_steam_import_all_job_marks_job_succeeded(db, monkeypatch):
    monkeypatch.setenv("STEAM_BOT_USERNAME", "")
    monkeypatch.setenv("STEAM_BOT_PASSWORD", "")
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "")
    from app.config import get_settings

    get_settings.cache_clear()
    job = queue_steam_import_all(db)

    try:
        result = run_steam_import_all_job(db, job.id)
    finally:
        get_settings.cache_clear()

    db.refresh(job)
    assert result["status"] == "succeeded"
    assert job.status == "succeeded"
    assert current_steam_import_all_job(db) is None


def test_steam_import_overview_reports_current_job_and_demo_counts(db):
    queue_steam_import_all(db)
    match = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"status":"demo_download_error","error":"Valve replay CDN returned HTTP 502"}',
    )
    db.add(match)
    db.commit()

    overview = steam_import_overview(db)

    assert overview["current_job"].status == "queued"
    assert overview["steam_history_matches"] == 1
    assert overview["demo_download_errors"] == 1
    assert "HTTP 502" in overview["latest_error"]


def test_clear_steam_demo_download_errors_resets_rows_to_pending(db):
    match = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"status":"demo_download_error","error":"Valve replay CDN returned HTTP 502"}',
    )
    db.add(match)
    db.commit()

    result = clear_steam_demo_download_errors(db)

    db.refresh(match)
    assert result == {"cleared": 1}
    assert "demo_download_pending" in match.raw_json
    assert "HTTP 502" not in match.raw_json


def test_update_match_auth_code_enables_sync_and_queues_job(db):
    account = link_steam_account(db, "76561198056634139", persona_name="JC")

    updated = update_match_auth_code(db, account.id, " AUTH-CODE ", " CSGO-abcde-abcde-abcde-abcde-abcde ")

    assert updated.match_auth_code == "AUTH-CODE"
    assert updated.last_share_code == "CSGO-abcde-abcde-abcde-abcde-abcde"
    assert updated.sync_enabled == 1
    job = db.query(ImportJob).one()
    assert job.steam_account_id == account.id
    assert job.job_type == "match_history_sync"


def test_update_match_auth_code_rejects_share_code(db):
    account = link_steam_account(db, "76561198056634139", persona_name="JC")

    try:
        update_match_auth_code(db, account.id, "CSGO-abcde-abcde-abcde-abcde-abcde")
    except ValueError as exc:
        assert "share code" in str(exc)
    else:
        raise AssertionError("share code should not be accepted as match auth code")


def test_queue_match_history_sync_requires_auth_code(db):
    account = link_steam_account(db, "76561198056634139", persona_name="JC")

    try:
        queue_match_history_sync(db, account.id)
    except ValueError as exc:
        assert "Game Authentication Code" in str(exc)
    else:
        raise AssertionError("queue_match_history_sync should require match_auth_code")


def test_sync_match_history_job_requires_steam_web_api_key(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE")
    job = db.query(ImportJob).filter(ImportJob.job_type == "match_history_sync").one()

    try:
        result = sync_match_history_job(db, job.id)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "failed"
    assert "STEAM_WEB_API_KEY" in result["error"]


def test_sync_match_history_job_stores_share_codes(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    responses = [
        b'{"result":{"nextcode":"CSGO-abcde-abcde-abcde-abcde-abcde"}}',
        b'{"result":{"nextcode":"n/a"}}',
    ]

    class FakeResponse:
        def __init__(self, body: bytes):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.body

    def fake_urlopen(_request, timeout):
        assert timeout == 30
        return FakeResponse(responses.pop(0))

    monkeypatch.setattr("app.services.steam_integration.urlopen", fake_urlopen)
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE")
    job = db.query(ImportJob).filter(ImportJob.job_type == "match_history_sync").one()

    try:
        result = sync_match_history_job(db, job.id)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "succeeded"
    assert result["result"]["inserted"] == 1
    assert account.last_share_code == "CSGO-abcde-abcde-abcde-abcde-abcde"


def test_parse_share_code_input_accepts_plain_and_url():
    assert parse_share_code_input("CSGO-abc") == {"share_code": "CSGO-abc"}
    assert parse_share_code_input("https://example.test/?code=CSGO-def") == {"share_code": "CSGO-def"}


def test_decode_match_share_code():
    decoded = decode_match_share_code("CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")

    assert decoded == {
        "matchid": 3822708819734036647,
        "outcomeid": 3822713222075515607,
        "token": 40370,
    }


def test_mark_steam_history_demo_download_status(db):
    create_steam_import_job(db, None, "noop")
    from app.db.models import Match

    match = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"share_code":"CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"}',
    )
    db.add(match)
    db.commit()

    result = mark_steam_history_demo_download_status(db)

    db.refresh(match)
    assert result["pending_demo_download"] == 1
    assert "demo_download_pending" in match.raw_json
    assert "3822708819734036647" in match.raw_json


def test_import_all_available_steam_matches(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    monkeypatch.setenv("STEAM_BOT_USERNAME", "")
    monkeypatch.setenv("STEAM_BOT_PASSWORD", "")
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "")
    from app.config import get_settings

    get_settings.cache_clear()
    responses = [
        b'{"result":{"nextcode":"CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"}}',
        b'{"result":{"nextcode":"n/a"}}',
    ]

    class FakeResponse:
        def __init__(self, body: bytes):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.body

    def fake_urlopen(_request, timeout):
        assert timeout == 30
        return FakeResponse(responses.pop(0))

    monkeypatch.setattr("app.services.steam_integration.urlopen", fake_urlopen)
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-pnZBU-A5xA8-cJr4B-r5B6D-r6M3A")

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "succeeded"
    assert result["result"]["demo_status"]["pending_demo_download"] == 1
    assert result["result"]["demo_download"]["configured"] is False
    assert "service bot" in result["result"]["demo_download"]["message"]


def test_import_all_available_steam_matches_skips_recent_sync(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    monkeypatch.setenv("STEAM_BOT_USERNAME", "")
    monkeypatch.setenv("STEAM_BOT_PASSWORD", "")
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    account.last_sync_at = account.updated_at
    db.commit()

    def fail_urlopen(_request, _timeout):
        raise AssertionError("recent sync should not call Steam API")

    monkeypatch.setattr("app.services.steam_integration.urlopen", fail_urlopen)
    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "succeeded"
    assert result["result"]["sync_jobs"][0]["status"] == "skipped"
    assert result["result"]["demo_status"]["pending_demo_download"] == 0


def test_steam_demo_downloader_is_disabled_without_bot_credentials(db, monkeypatch):
    monkeypatch.setenv("STEAM_BOT_USERNAME", "")
    monkeypatch.setenv("STEAM_BOT_PASSWORD", "")
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "")
    from app.config import get_settings
    from app.db.models import Match

    get_settings.cache_clear()
    match = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"share_code":"CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"}',
    )
    db.add(match)
    db.commit()

    try:
        result = download_pending_steam_demos(db)
    finally:
        get_settings.cache_clear()

    assert steam_demo_downloader_configured() is False
    assert result["configured"] is False
    assert result["pending"] == 1
