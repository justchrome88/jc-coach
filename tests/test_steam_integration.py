import bz2
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.models import CoachRecommendation, ImportJob, Match, MatchRecommendationEvaluation, SteamAccount
from app.services.demo_retention import (
    DEMO_RETENTION_POLICY_RETAIN_RAW,
    DEMO_RETENTION_STATUS_RETAINED_AFTER_FAILURE,
    DEMO_RETENTION_STATUS_RETAINED_FOR_DEV,
)
from app.services.match_queries import playable_match_select
from app.services.recommendation_tracking import ensure_default_recommendation, evaluate_recommendations_for_match
from app.services.steam_demo_downloader import (
    _download_and_import_match,
    _download_demo_file,
    download_pending_steam_demos,
    steam_demo_downloader_configured,
)
from app.services.steam_integration import (
    STEAM_IMPORT_APPROXIMATE_MATCH_DATE,
    STEAM_IMPORT_BATCH_CAP_REACHED,
    STEAM_IMPORT_DEMO_TOO_LARGE,
    STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
    STEAM_IMPORT_DOWNLOAD_FAILED,
    STEAM_IMPORT_DUPLICATE_SKIPPED,
    STEAM_IMPORT_EXACT_MATCH_DATE_AVAILABLE,
    STEAM_IMPORT_EXACT_MATCH_DATE_UNAVAILABLE,
    STEAM_IMPORT_INTERRUPTED,
    STEAM_IMPORT_NEED_CODE,
    STEAM_IMPORT_NO_NEW,
    STEAM_IMPORT_PARSER_FAILED,
    STEAM_IMPORT_PARTIAL_SUCCESS,
    STEAM_IMPORT_STEAM_NOT_CONNECTED,
    STEAM_IMPORT_SUCCESS,
    checkpoint_steam_import_all_job,
    clear_steam_demo_download_errors,
    create_steam_import_job,
    current_steam_import_all_job,
    decode_match_share_code,
    extract_steam_id,
    import_all_available_steam_matches,
    import_steam_share_code_demo,
    is_stale_steam_import_all_job,
    link_steam_account,
    mark_steam_history_demo_download_status,
    mark_steam_import_all_job_interrupted,
    match_date_truth,
    parse_share_code_input,
    queue_match_history_sync,
    queue_steam_import_all,
    run_startup_stale_steam_import_repair,
    run_steam_import_all_job,
    steam_import_overview,
    steam_login_url,
    sync_match_history_job,
    update_match_auth_code,
    validate_openid_callback,
)
from app.services.steam_match_metadata import parse_steam_match_time, steam_gc_metadata_from_item
from app.services.steam_storage_guard import SteamImportStorageBudget


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


def test_validate_openid_callback_requires_positive_steam_assertion(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"ns:http://specs.openid.net/auth/2.0\nis_valid:true\n"

    def fake_urlopen(request, timeout):
        assert timeout == 10
        assert "openid.mode=check_authentication" in request.full_url
        return FakeResponse()

    monkeypatch.setattr("app.services.steam_integration.urlopen", fake_urlopen)

    steam_id, error = validate_openid_callback(
        {
            "openid.mode": "id_res",
            "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198056634139",
        }
    )

    assert steam_id == "76561198056634139"
    assert error is None


def test_validate_openid_callback_rejects_negative_steam_assertion(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"ns:http://specs.openid.net/auth/2.0\nis_valid:false\n"

    monkeypatch.setattr("app.services.steam_integration.urlopen", lambda *_args, **_kwargs: FakeResponse())

    steam_id, error = validate_openid_callback(
        {
            "openid.mode": "id_res",
            "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198056634139",
        }
    )

    assert steam_id is None
    assert error == "Steam OpenID verification failed."


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


def test_parent_checkpoint_persists_after_account_checked(db):
    link_steam_account(db, "76561198056634139", persona_name="JC")
    job = queue_steam_import_all(db)

    result = run_steam_import_all_job(db, job.id)

    db.refresh(job)
    progress = result["result"]["progress"]
    phases = [event["phase"] for event in progress["recent_events"]]
    assert "started" in phases
    assert "account_checked" in phases
    assert progress["phase"] == "demo_queued"
    assert job.result_json


def test_parent_checkpoint_persists_after_child_sync_success(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])
    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        lambda *_args, **_kwargs: {"configured": True, "processed": 0, "imported": 0, "failed": 0, "results": []},
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    progress = result["result"]["progress"]
    phases = [event["phase"] for event in progress["recent_events"]]
    assert "share_codes_fetch_started" in phases
    assert "share_codes_fetched" in phases
    assert progress["child_job_ids"]


def test_parent_checkpoint_persists_before_demo_download(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])

    def fake_download_pending_steam_demos(_db, **kwargs):
        kwargs["progress_callback"](
            "demo_downloading",
            {
                "share_code": "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
                "counters": {"processed": 0, "imported": 0, "failed": 0, "skipped": 0, "pending": 1},
            },
        )
        return {"configured": True, "processed": 0, "imported": 0, "failed": 0, "pending": 1, "results": []}

    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        fake_download_pending_steam_demos,
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    phases = [event["phase"] for event in result["result"]["progress"]["recent_events"]]
    assert "demo_queued" in phases
    assert "demo_downloading" in phases


def test_parent_checkpoint_persists_disk_budget_exceeded(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])

    def fake_download_pending_steam_demos(_db, **kwargs):
        kwargs["progress_callback"](
            STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
            {
                "share_code": "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
                "budget_status": STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
            },
        )
        return {
            "configured": True,
            "processed": 0,
            "imported": 0,
            "failed": 1,
            "pending": 1,
            "budget_status": STEAM_IMPORT_DISK_BUDGET_EXCEEDED,
            "results": [{"status": "failed", "budget_status": STEAM_IMPORT_DISK_BUDGET_EXCEEDED}],
        }

    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        fake_download_pending_steam_demos,
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "failed"
    progress = result["result"]["progress"]
    assert progress["phase"] == STEAM_IMPORT_DISK_BUDGET_EXCEEDED
    assert any(event["phase"] == STEAM_IMPORT_DISK_BUDGET_EXCEEDED for event in progress["recent_events"])


def test_stale_running_steam_import_all_is_not_reused(db):
    stale = queue_steam_import_all(db)
    stale.status = "in_progress"
    stale.started_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
    db.commit()

    queued = queue_steam_import_all(db)

    db.refresh(stale)
    assert queued.id != stale.id
    assert queued.status == "queued"
    assert stale.status == "failed"
    assert json.loads(stale.result_json)["overall_outcome"] == STEAM_IMPORT_INTERRUPTED


def test_stale_running_steam_import_all_can_be_marked_interrupted(db):
    job = queue_steam_import_all(db)
    job.status = "in_progress"
    job.started_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
    db.commit()

    assert is_stale_steam_import_all_job(job)
    mark_steam_import_all_job_interrupted(db, job, reason="test interruption")

    db.refresh(job)
    result = json.loads(job.result_json)
    assert job.status == "failed"
    assert result["overall_outcome"] == STEAM_IMPORT_INTERRUPTED
    assert result["statuses"] == [STEAM_IMPORT_INTERRUPTED]
    assert result["progress"]["phase"] == STEAM_IMPORT_INTERRUPTED


def test_non_stale_running_steam_import_all_blocks_new_queue(db):
    running = queue_steam_import_all(db)
    running.status = "in_progress"
    running.started_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()

    queued = queue_steam_import_all(db)

    db.refresh(running)
    assert queued.id == running.id
    assert running.status == "in_progress"
    assert db.query(ImportJob).count() == 1


def test_startup_stale_repair_is_opt_in(db, monkeypatch):
    from app.config import get_settings

    job = create_steam_import_job(db, None, "steam_import_all")
    job.status = "in_progress"
    job.started_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
    db.commit()

    monkeypatch.setenv("STEAM_IMPORT_REPAIR_STALE_ON_STARTUP", "false")
    get_settings.cache_clear()
    try:
        assert run_startup_stale_steam_import_repair(db) == []
        db.refresh(job)
        assert job.status == "in_progress"

        monkeypatch.setenv("STEAM_IMPORT_REPAIR_STALE_ON_STARTUP", "true")
        get_settings.cache_clear()
        repaired = run_startup_stale_steam_import_repair(db)
    finally:
        get_settings.cache_clear()

    db.refresh(job)
    assert [item.id for item in repaired] == [job.id]
    assert job.status == "failed"
    assert json.loads(job.result_json)["overall_outcome"] == STEAM_IMPORT_INTERRUPTED


def test_parent_checkpoint_recent_events_are_bounded(db):
    job = queue_steam_import_all(db)
    job.status = "in_progress"
    job.started_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()

    for index in range(40):
        checkpoint_steam_import_all_job(db, job, f"phase_{index}", event={"status": str(index)})

    db.refresh(job)
    progress = json.loads(job.result_json)["progress"]
    assert len(progress["recent_events"]) == 25
    assert progress["recent_events"][0]["phase"] == "phase_15"
    assert progress["recent_events"][-1]["phase"] == "phase_39"


def test_run_steam_import_all_job_reports_steam_not_connected(db, monkeypatch):
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
    assert result["status"] == "failed"
    assert job.status == "failed"
    assert result["result"]["overall_outcome"] == STEAM_IMPORT_STEAM_NOT_CONNECTED
    assert STEAM_IMPORT_STEAM_NOT_CONNECTED in result["result"]["statuses"]
    assert current_steam_import_all_job(db) is None


def test_run_steam_import_all_job_reports_need_code(db, monkeypatch):
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    job = queue_steam_import_all(db)

    result = run_steam_import_all_job(db, job.id)

    db.refresh(account)
    db.refresh(job)
    assert result["status"] == "failed"
    assert job.status == "failed"
    assert result["result"]["overall_outcome"] == STEAM_IMPORT_NEED_CODE
    assert result["result"]["account_states"][0]["has_match_auth_code"] is False
    assert result["result"]["account_states"][0]["has_last_share_code"] is False


def test_run_steam_import_all_job_reports_no_new_clean_success(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])
    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        lambda *_args, **_kwargs: {"configured": True, "processed": 0, "imported": 0, "failed": 0, "results": []},
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "completed"
    assert result["result"]["overall_outcome"] == STEAM_IMPORT_NO_NEW
    assert STEAM_IMPORT_EXACT_MATCH_DATE_UNAVAILABLE in result["result"]["statuses"]


def test_run_steam_import_all_job_reports_duplicate_skipped_clean_success(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    db.add(
        Match(
            source="steam_history",
            external_match_id="CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK",
            raw_json='{"share_code":"CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK"}',
        )
    )
    db.commit()
    monkeypatch.setattr(
        "app.services.steam_integration._collect_match_share_codes",
        lambda **_kwargs: ["CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK"],
    )
    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        lambda *_args, **_kwargs: {"configured": True, "processed": 0, "imported": 0, "failed": 0, "results": []},
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "completed"
    assert result["result"]["overall_outcome"] == STEAM_IMPORT_DUPLICATE_SKIPPED
    assert STEAM_IMPORT_DUPLICATE_SKIPPED in result["result"]["statuses"]


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

    assert result["status"] == "completed"
    assert result["result"]["inserted"] == 1
    assert result["result"]["collected_share_codes"] == ["CSGO-abcde-abcde-abcde-abcde-abcde"]
    assert account.last_share_code == "CSGO-abcde-abcde-abcde-abcde-abcde"


def test_steam_history_rows_are_not_playable_matches(db):
    steam_placeholder = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"share_code":"CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"}',
    )
    real_match = Match(source="demo", external_match_id="demo-1", map_name="Mirage", kills=10, deaths=8)
    db.add_all([steam_placeholder, real_match])
    db.commit()

    matches = db.scalars(playable_match_select()).all()

    assert matches == [real_match]


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


def test_steam_gc_metadata_normalizes_match_time():
    metadata = steam_gc_metadata_from_item(
        {
            "share_code": "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
            "match_id": "3822708819734036647",
            "match_time": 1783022400,
        }
    )

    assert metadata["played_at"] == "2026-07-02T20:00:00"
    assert metadata["played_at_source"] == "steam_gc_match_time"
    assert parse_steam_match_time("1783022400000") == datetime(2026, 7, 2, 20, 0)


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
    monkeypatch.setattr(
        "app.services.steam_integration._collect_match_share_codes",
        lambda **_kwargs: ["CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK"],
    )
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    stale_pending = Match(
        source="steam_history",
        external_match_id="CSGO-SYSZK-hOFfp-WtBsM-WtsNK-pcy6A",
        raw_json='{"share_code":"CSGO-SYSZK-hOFfp-WtBsM-WtsNK-pcy6A","status":"demo_download_pending"}',
    )
    db.add(stale_pending)
    db.commit()

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "failed"
    assert result["result"]["overall_outcome"] == STEAM_IMPORT_DOWNLOAD_FAILED
    assert result["result"]["demo_status"]["pending_demo_download"] == 2
    assert result["result"]["demo_status"]["steam_history_matches"] == 2
    assert result["result"]["sync_jobs"][0]["status"] == "completed"
    assert result["result"]["demo_download"]["configured"] is False
    assert result["result"]["demo_download"]["pending"] == 2
    assert "service bot" in result["result"]["demo_download"]["message"]


def test_import_all_available_steam_matches_uses_sync_even_after_recent_sync(db, monkeypatch):
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

    monkeypatch.setattr(
        "app.services.steam_integration._collect_match_share_codes",
        lambda **_kwargs: ["CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK"],
    )
    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "failed"
    assert result["result"]["overall_outcome"] == STEAM_IMPORT_DOWNLOAD_FAILED
    assert result["result"]["sync_jobs"][0]["status"] == "completed"
    assert result["result"]["demo_status"]["pending_demo_download"] == 2


def test_import_all_available_steam_matches_reports_download_failure(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])
    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        lambda *_args, **_kwargs: {
            "configured": True,
            "processed": 1,
            "imported": 0,
            "failed": 1,
            "results": [{"status": "failed", "error": "Valve replay CDN returned HTTP 502"}],
        },
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "failed"
    assert result["result"]["overall_outcome"] == STEAM_IMPORT_DOWNLOAD_FAILED
    assert STEAM_IMPORT_DOWNLOAD_FAILED in result["result"]["statuses"]


def test_import_all_available_steam_matches_reports_parser_failure(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])
    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        lambda *_args, **_kwargs: {
            "configured": True,
            "processed": 1,
            "imported": 0,
            "failed": 1,
            "results": [{"status": "failed", "error": "Downloaded demo but parser failed: broken demo"}],
        },
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "failed"
    assert result["result"]["overall_outcome"] == STEAM_IMPORT_PARSER_FAILED
    assert STEAM_IMPORT_PARSER_FAILED in result["result"]["statuses"]


def test_import_all_available_steam_matches_reports_partial_success(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])
    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        lambda *_args, **_kwargs: {
            "configured": True,
            "processed": 2,
            "imported": 1,
            "failed": 1,
            "results": [
                {
                    "status": "imported",
                    "played_at": "2026-07-02T20:00:00",
                    "played_at_source": "steam_gc_match_time",
                },
                {"status": "failed", "error": "Valve replay CDN returned HTTP 502"},
            ],
        },
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "failed"
    assert result["result"]["overall_outcome"] == STEAM_IMPORT_PARTIAL_SUCCESS
    assert STEAM_IMPORT_SUCCESS in result["result"]["statuses"]
    assert STEAM_IMPORT_DOWNLOAD_FAILED in result["result"]["statuses"]
    assert STEAM_IMPORT_EXACT_MATCH_DATE_AVAILABLE in result["result"]["statuses"]
    assert "partial_success is represented" in result["result"]["job_status_limitation"]


def test_import_all_available_steam_matches_reports_approximate_match_date(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])
    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        lambda *_args, **_kwargs: {
            "configured": True,
            "processed": 1,
            "imported": 1,
            "failed": 0,
            "results": [{"status": "imported", "played_at": "2026-07-02T20:00:00", "played_at_source": "demo_header"}],
        },
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["status"] == "completed"
    assert STEAM_IMPORT_APPROXIMATE_MATCH_DATE in result["result"]["statuses"]


def test_import_steam_share_code_demo_imports_exact_code(db, monkeypatch):
    monkeypatch.setenv("STEAM_BOT_USERNAME", "")
    monkeypatch.setenv("STEAM_BOT_PASSWORD", "")
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")

    try:
        result = import_steam_share_code_demo(db, account.id, " CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL ")
    finally:
        get_settings.cache_clear()

    db.refresh(account)
    assert account.last_share_code == "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"
    assert result["share_code"] == "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"
    assert result["demo_status"]["pending_demo_download"] == 1
    assert result["demo_download"]["pending"] == 1
    assert result["job_id"] is not None
    assert result["job_status"] == "failed"


def test_import_steam_share_code_demo_creates_tracking_job_before_downloader(db, monkeypatch):
    account = link_steam_account(db, "76561198056634139", persona_name="JC")

    def fake_download_pending_steam_demos(inner_db, *_args, **_kwargs):
        job = inner_db.query(ImportJob).filter(ImportJob.job_type == "share_code_import").one()
        assert job.status == "in_progress"
        return {
            "configured": True,
            "processed": 1,
            "imported": 1,
            "failed": 0,
            "results": [
                {
                    "status": "imported",
                    "played_at": "2026-07-02T20:00:00",
                    "played_at_source": "steam_gc_match_time",
                }
            ],
        }

    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        fake_download_pending_steam_demos,
    )

    result = import_steam_share_code_demo(db, account.id, "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")

    job = db.query(ImportJob).filter(ImportJob.job_type == "share_code_import").one()
    assert result["job_id"] == job.id
    assert result["job_status"] == "completed"
    assert result["overall_outcome"] == STEAM_IMPORT_SUCCESS
    assert STEAM_IMPORT_EXACT_MATCH_DATE_AVAILABLE in result["statuses"]


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


def test_steam_demo_batch_cap_leaves_remaining_pending(db, monkeypatch, tmp_path):
    monkeypatch.setenv("STEAM_IMPORT_MAX_DEMOS_PER_RUN", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    share_codes = [
        "CSGO-FpxoS-hCLi9-My3iH-JJsdP-xbjsF",
        "CSGO-uCGaY-r6Pcy-X3KpH-oQDBR-e75RG",
        "CSGO-KeYZ6-uqGoK-ZRMVA-8DJFQ-P8o3B",
    ]
    for code in share_codes:
        db.add(Match(source="steam_history", external_match_id=code, raw_json=json.dumps({"share_code": code})))
    db.commit()
    demo_path = tmp_path / "demo.dem"
    demo_path.write_bytes(b"demo")

    def fake_fetch_demo_urls(codes):
        return {
            "ok": True,
            "results": [
                {"ok": True, "share_code": code, "match_id": str(index), "demo_url": "https://example.test/demo.dem"}
                for index, code in enumerate(codes)
            ],
        }

    def fake_download_demo_file(_url, _share_code, storage_budget=None):
        return demo_path

    def fake_import_demo_file(_db, _demo_path, **kwargs):
        assert kwargs["evaluate_recommendations"] is False
        return {"match_id": None, "imported": 1, "skipped_duplicates": 0, "stored_path": str(demo_path)}

    monkeypatch.setattr("app.services.steam_demo_downloader.steam_demo_downloader_configured", lambda: True)
    monkeypatch.setattr("app.services.steam_demo_downloader._fetch_demo_urls", fake_fetch_demo_urls)
    monkeypatch.setattr("app.services.steam_demo_downloader._download_demo_file", fake_download_demo_file)
    monkeypatch.setattr("app.services.steam_demo_downloader.import_demo_file", fake_import_demo_file)

    try:
        result = download_pending_steam_demos(db, limit=20)
    finally:
        get_settings.cache_clear()

    assert result["processed"] == 1
    assert result["imported"] == 1
    assert result["failed"] == 0
    assert result["batch_cap_reached"] is True
    assert result["remaining_pending"] == 2
    assert result["results"][0]["recommendation_evaluation"]["status"] == "skipped"
    pending_rows = [json.loads(match.raw_json or "{}").get("status") for match in db.query(Match).all()]
    assert pending_rows.count("demo_imported") == 1
    assert "demo_download_error" not in pending_rows


def test_steam_import_result_reports_batch_cap(db, monkeypatch):
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])
    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        lambda *_args, **_kwargs: {
            "configured": True,
            "processed": 1,
            "imported": 1,
            "failed": 0,
            "remaining_pending": 19,
            "batch_cap_reached": True,
            "results": [{"status": "imported", "played_at_source": "steam_gc_match_time", "played_at": "2026-07-02"}],
        },
    )

    result = import_all_available_steam_matches(db)

    assert result["status"] == "completed"
    assert STEAM_IMPORT_BATCH_CAP_REACHED in result["result"]["statuses"]


def test_steam_download_content_length_blocks_too_large_demo(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("STEAM_IMPORT_MAX_SINGLE_DEMO_BYTES", "3")
    from app.config import get_settings

    get_settings.cache_clear()

    class FakeResponse:
        headers = {"Content-Length": "4"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            return b"data"

    monkeypatch.setattr("app.services.steam_demo_downloader.urlopen", lambda *_args, **_kwargs: FakeResponse())
    try:
        budget = SteamImportStorageBudget()
        try:
            _download_demo_file(
                "https://example.test/demo.dem",
                "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
                storage_budget=budget,
            )
        except Exception as exc:
            captured = exc
        else:
            raise AssertionError("too-large demo should be blocked")
    finally:
        get_settings.cache_clear()

    assert captured.status == STEAM_IMPORT_DEMO_TOO_LARGE


def test_steam_job_byte_budget_stops_before_next_demo(db, monkeypatch, tmp_path):
    monkeypatch.setenv("STEAM_IMPORT_MAX_DEMOS_PER_RUN", "2")
    monkeypatch.setenv("STEAM_IMPORT_MAX_BYTES_PER_JOB", "7")
    monkeypatch.setenv("STEAM_IMPORT_UNKNOWN_DEMO_RESERVE_BYTES", "4")
    from app.config import get_settings

    get_settings.cache_clear()
    share_codes = ["CSGO-FpxoS-hCLi9-My3iH-JJsdP-xbjsF", "CSGO-uCGaY-r6Pcy-X3KpH-oQDBR-e75RG"]
    for code in share_codes:
        db.add(Match(source="steam_history", external_match_id=code, raw_json=json.dumps({"share_code": code})))
    db.commit()
    demo_path = tmp_path / "demo.dem"
    demo_path.write_bytes(b"demo")

    def fake_fetch_demo_urls(codes):
        return {
            "ok": True,
            "results": [
                {"ok": True, "share_code": code, "match_id": code, "demo_url": "https://example.test/demo.dem"}
                for code in codes
            ],
        }

    def fake_download_demo_file(_url, _share_code, storage_budget=None):
        storage_budget.record_downloaded(4)
        return demo_path

    def fake_import_demo_file(_db, _demo_path, **_kwargs):
        return {"match_id": None, "imported": 1, "skipped_duplicates": 0, "stored_path": str(demo_path)}

    monkeypatch.setattr("app.services.steam_demo_downloader.steam_demo_downloader_configured", lambda: True)
    monkeypatch.setattr("app.services.steam_demo_downloader._fetch_demo_urls", fake_fetch_demo_urls)
    monkeypatch.setattr("app.services.steam_demo_downloader._download_demo_file", fake_download_demo_file)
    monkeypatch.setattr("app.services.steam_demo_downloader.import_demo_file", fake_import_demo_file)

    try:
        result = download_pending_steam_demos(db, limit=20)
    finally:
        get_settings.cache_clear()

    assert result["processed"] == 1
    assert result["failed"] == 0
    assert result["budget_status"] == STEAM_IMPORT_DISK_BUDGET_EXCEEDED
    assert result["remaining_pending"] == 1
    assert result["results"][-1]["status"] == "not_attempted"


def test_streamed_download_writes_chunks_and_counts_bytes(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    from app.config import get_settings

    get_settings.cache_clear()

    class FakeResponse:
        headers = {"Content-Length": "4"}

        def __init__(self):
            self.chunks = [b"ab", b"cd", b""]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            return self.chunks.pop(0)

    monkeypatch.setattr("app.services.steam_demo_downloader.urlopen", lambda *_args, **_kwargs: FakeResponse())
    try:
        budget = SteamImportStorageBudget()
        path = _download_demo_file(
            "https://example.test/demo.dem",
            "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
            storage_budget=budget,
        )
    finally:
        get_settings.cache_clear()

    assert path.read_bytes() == b"abcd"
    assert budget.downloaded_bytes == 4
    shutil_parent = path.parent
    # The caller normally removes the temp dir; this direct unit test owns it.
    import shutil

    shutil.rmtree(shutil_parent, ignore_errors=True)


def test_streamed_bz2_decompression_counts_bytes(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    from app.config import get_settings

    get_settings.cache_clear()
    payload = bz2.compress(b"demo-data")

    class FakeResponse:
        headers = {"Content-Length": str(len(payload))}

        def __init__(self):
            self.chunks = [payload[:3], payload[3:], b""]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            return self.chunks.pop(0)

    monkeypatch.setattr("app.services.steam_demo_downloader.urlopen", lambda *_args, **_kwargs: FakeResponse())
    try:
        budget = SteamImportStorageBudget()
        path = _download_demo_file(
            "https://example.test/demo.dem.bz2",
            "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
            storage_budget=budget,
        )
    finally:
        get_settings.cache_clear()

    assert path.read_bytes() == b"demo-data"
    assert budget.downloaded_bytes == len(payload)
    assert budget.decompressed_bytes == len(b"demo-data")
    import shutil

    shutil.rmtree(path.parent, ignore_errors=True)


def test_steam_downloader_passes_gc_match_time_to_demo_import(db, monkeypatch, tmp_path):
    match = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"share_code":"CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL","status":"demo_download_pending"}',
    )
    db.add(match)
    db.commit()
    demo_path = tmp_path / "demo.dem"
    demo_path.write_bytes(b"demo")
    captured = {}

    def fake_download_demo_file(_url, _share_code, storage_budget=None):
        return demo_path

    def fake_import_demo_file(_db, _demo_path, **kwargs):
        captured.update(kwargs)
        return {
            "match_id": 123,
            "imported": 1,
            "skipped_duplicates": 0,
            "stored_path": str(demo_path),
            "demo_retention_policy": DEMO_RETENTION_POLICY_RETAIN_RAW,
            "demo_retention_status": DEMO_RETENTION_STATUS_RETAINED_FOR_DEV,
            "raw_demo_path": str(demo_path),
            "raw_demo_size_bytes": demo_path.stat().st_size,
            "parser_success": True,
        }

    monkeypatch.setattr("app.services.steam_demo_downloader._download_demo_file", fake_download_demo_file)
    monkeypatch.setattr("app.services.steam_demo_downloader.import_demo_file", fake_import_demo_file)

    result = _download_and_import_match(
        db,
        match,
        share_code="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        steam_gc_item={
            "share_code": "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
            "match_id": "3822708819734036647",
            "match_time": 1783022400,
            "demo_url": "https://replay123.valve.net/730/demo.dem.bz2",
        },
        player_identifier=None,
    )

    db.refresh(match)
    assert captured["steam_metadata"]["played_at"] == "2026-07-02T20:00:00"
    assert captured["steam_metadata"]["played_at_source"] == "steam_gc_match_time"
    assert result["played_at"] == "2026-07-02T20:00:00"
    assert result["demo_retention_status"] == DEMO_RETENTION_STATUS_RETAINED_FOR_DEV
    assert "steam_gc_match_time" in match.raw_json
    assert "retain_raw_for_parser_development" in match.raw_json


def test_steam_downloader_writes_exact_gc_match_time_to_imported_match(db, monkeypatch, tmp_path):
    placeholder = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"share_code":"CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL","status":"demo_download_pending"}',
    )
    db.add(placeholder)
    db.commit()
    demo_path = tmp_path / "demo.dem"
    demo_path.write_bytes(b"demo")

    def fake_download_demo_file(_url, _share_code, storage_budget=None):
        return demo_path

    def fake_import_demo_file(inner_db, _demo_path, **_kwargs):
        imported = Match(
            source="demo",
            external_match_id="imported-exact",
            played_at=datetime(1999, 1, 1, 0, 0),
            raw_json=json.dumps({"played_at_source": "file_modified_fallback", "match": {}}),
        )
        inner_db.add(imported)
        inner_db.commit()
        inner_db.refresh(imported)
        return {"match_id": imported.id, "imported": 1, "skipped_duplicates": 0, "stored_path": str(demo_path)}

    monkeypatch.setattr("app.services.steam_demo_downloader._download_demo_file", fake_download_demo_file)
    monkeypatch.setattr("app.services.steam_demo_downloader.import_demo_file", fake_import_demo_file)

    result = _download_and_import_match(
        db,
        placeholder,
        share_code="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        steam_gc_item={
            "share_code": "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
            "match_id": "3822708819734036647",
            "match_time": 1783022400,
            "demo_url": "https://replay123.valve.net/730/demo.dem.bz2",
        },
        player_identifier=None,
    )

    imported = db.get(Match, result["demo_match_id"])
    assert imported.played_at == datetime(2026, 7, 2, 20, 0)
    truth = match_date_truth(imported)
    assert truth["status"] == STEAM_IMPORT_EXACT_MATCH_DATE_AVAILABLE
    assert truth["source"] == "steam_gc_match_time"


def test_steam_downloader_evaluates_recommendations_after_exact_date_truth(db, monkeypatch, tmp_path):
    survival = _seed_steam_recommendation_baseline(db)
    placeholder = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"share_code":"CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL","status":"demo_download_pending"}',
    )
    db.add(placeholder)
    db.commit()
    demo_path = tmp_path / "demo.dem"
    demo_path.write_bytes(b"demo")
    captured = {}

    def fake_download_demo_file(_url, _share_code, storage_budget=None):
        return demo_path

    def fake_import_demo_file(inner_db, _demo_path, **kwargs):
        captured.update(kwargs)
        imported = _add_steam_demo_match(
            inner_db,
            external_match_id="imported-auto-eval",
            played_at=datetime(1999, 1, 1, 0, 0),
            raw_json={
                "played_at_source": "file_modified_fallback",
                "match": {"played_at_source": "file_modified_fallback"},
            },
        )
        return {
            "match_id": imported.id,
            "imported": 1,
            "skipped_duplicates": 0,
            "stored_path": str(demo_path),
            "recommendation_evaluations": [],
            "recommendation_evaluation": {
                "status": "deferred",
                "count": 0,
                "evaluations": [],
                "match_id": imported.id,
                "reason": "steam_date_truth_pending",
            },
        }

    monkeypatch.setattr("app.services.steam_demo_downloader._download_demo_file", fake_download_demo_file)
    monkeypatch.setattr("app.services.steam_demo_downloader.import_demo_file", fake_import_demo_file)

    result = _download_and_import_match(
        db,
        placeholder,
        share_code="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        steam_gc_item={
            "share_code": "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
            "match_id": "3822708819734036647",
            "match_time": 1783022400,
            "demo_url": "https://replay123.valve.net/730/demo.dem.bz2",
        },
        player_identifier=None,
    )

    imported = db.get(Match, result["demo_match_id"])
    evaluations = db.scalars(
        select(MatchRecommendationEvaluation).where(MatchRecommendationEvaluation.match_id == imported.id)
    ).all()
    assert captured["evaluate_recommendations"] is False
    assert match_date_truth(imported)["status"] == STEAM_IMPORT_EXACT_MATCH_DATE_AVAILABLE
    assert result["recommendation_evaluation"]["status"] == "created"
    assert result["recommendation_evaluation"]["count"] == 1
    assert result["recommendation_evaluations"][0]["recommendation_id"] == survival.id
    assert len(evaluations) == 1
    assert evaluations[0].recommendation_id == survival.id
    assert "metric_confidence" in json.loads(evaluations[0].evidence_json)
    assert evaluate_recommendations_for_match(db, imported.id) == []
    db.refresh(placeholder)
    placeholder_raw = json.loads(placeholder.raw_json)
    assert placeholder_raw["recommendation_evaluation"]["status"] == "created"
    assert db.query(MatchRecommendationEvaluation).filter_by(match_id=imported.id).count() == 1


def test_steam_downloader_missing_gc_match_time_does_not_keep_file_mtime_as_match_date(db, monkeypatch, tmp_path):
    placeholder = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"share_code":"CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL","status":"demo_download_pending"}',
    )
    db.add(placeholder)
    db.commit()
    demo_path = tmp_path / "demo.dem"
    demo_path.write_bytes(b"demo")

    def fake_download_demo_file(_url, _share_code, storage_budget=None):
        return demo_path

    def fake_import_demo_file(inner_db, _demo_path, **_kwargs):
        imported = Match(
            source="demo",
            external_match_id="imported-no-date",
            played_at=datetime(2030, 1, 1, 0, 0),
            raw_json=json.dumps(
                {
                    "played_at": "2030-01-01T00:00:00",
                    "played_at_source": "file_modified_fallback",
                    "match": {
                        "played_at": "2030-01-01T00:00:00",
                        "played_at_source": "file_modified_fallback",
                    },
                }
            ),
        )
        inner_db.add(imported)
        inner_db.commit()
        inner_db.refresh(imported)
        return {
            "match_id": imported.id,
            "imported": 1,
            "skipped_duplicates": 0,
            "stored_path": str(demo_path),
        }

    monkeypatch.setattr("app.services.steam_demo_downloader._download_demo_file", fake_download_demo_file)
    monkeypatch.setattr("app.services.steam_demo_downloader.import_demo_file", fake_import_demo_file)

    result = _download_and_import_match(
        db,
        placeholder,
        share_code="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        steam_gc_item={
            "share_code": "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
            "match_id": "3822708819734036647",
            "demo_url": "https://replay123.valve.net/730/demo.dem.bz2",
        },
        player_identifier=None,
    )

    imported = db.get(Match, result["demo_match_id"])
    assert imported.played_at is None
    assert result["match_date_status"] == STEAM_IMPORT_EXACT_MATCH_DATE_UNAVAILABLE
    assert result["recommendation_evaluation"]["status"] == "not_eligible"
    assert result["recommendation_evaluation"]["count"] == 0
    assert result["recommendation_evaluations"] == []
    truth = match_date_truth(imported)
    assert truth["status"] == STEAM_IMPORT_EXACT_MATCH_DATE_UNAVAILABLE
    assert truth["source"] == "unavailable"
    db.refresh(placeholder)
    assert "exact_match_date_unavailable" in placeholder.raw_json


def test_steam_freshness_ignores_approximate_imported_match_dates(db, monkeypatch):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    db.add(
        Match(
            source="demo",
            external_match_id="manual-future",
            played_at=datetime(2030, 1, 1, 0, 0),
            raw_json=json.dumps({"played_at_source": "file_modified_fallback"}),
        )
    )
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL")
    db.commit()
    captured = {}
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])

    def fake_download_pending_steam_demos(_db, **kwargs):
        captured.update(kwargs)
        return {"configured": True, "processed": 0, "imported": 0, "failed": 0, "results": []}

    monkeypatch.setattr(
        "app.services.steam_demo_downloader.download_pending_steam_demos",
        fake_download_pending_steam_demos,
    )

    try:
        result = import_all_available_steam_matches(db)
    finally:
        get_settings.cache_clear()

    assert result["result"]["latest_imported_played_at_before_job"] is None
    assert captured["min_played_at"] is None


def test_steam_download_parser_failure_records_retained_demo_metadata(db, monkeypatch, tmp_path):
    from app.services.demo_parser import DemoParseError

    match = Match(
        source="steam_history",
        external_match_id="CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
        raw_json='{"share_code":"CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL","status":"demo_download_pending"}',
    )
    db.add(match)
    db.commit()
    demo_path = tmp_path / "failed.dem"
    demo_path.write_bytes(b"HL2DEMO")

    def fake_fetch_demo_urls(_share_codes):
        return {
            "ok": True,
            "results": [
                {
                    "ok": True,
                    "share_code": "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL",
                    "match_id": "3822708819734036647",
                    "match_time": 1783022400,
                    "demo_url": "https://replay123.valve.net/730/demo.dem.bz2",
                }
            ],
        }

    def fake_download_demo_file(_url, _share_code, storage_budget=None):
        return demo_path

    def fake_import_demo_file(_db, _demo_path, **_kwargs):
        raise DemoParseError(
            "parser failed",
            retention={
                "demo_retention_policy": DEMO_RETENTION_POLICY_RETAIN_RAW,
                "demo_retention_status": DEMO_RETENTION_STATUS_RETAINED_AFTER_FAILURE,
                "raw_demo_path": str(demo_path),
                "raw_demo_size_bytes": demo_path.stat().st_size,
                "parser_success": False,
            },
        )

    monkeypatch.setattr("app.services.steam_demo_downloader.steam_demo_downloader_configured", lambda: True)
    monkeypatch.setattr("app.services.steam_demo_downloader._fetch_demo_urls", fake_fetch_demo_urls)
    monkeypatch.setattr("app.services.steam_demo_downloader._download_demo_file", fake_download_demo_file)
    monkeypatch.setattr("app.services.steam_demo_downloader.import_demo_file", fake_import_demo_file)

    result = download_pending_steam_demos(db)

    db.refresh(match)
    assert result["failed"] == 1
    assert result["results"][0]["demo_retention_status"] == DEMO_RETENTION_STATUS_RETAINED_AFTER_FAILURE
    assert "retained_after_failure" in match.raw_json


def _seed_steam_recommendation_baseline(db):
    for index in range(15):
        _add_steam_demo_match(
            db,
            external_match_id=f"baseline-{index}",
            played_at=datetime(2026, 6, index + 1, 12, 0),
            raw_json={
                "match_date_status": "exact_match_date_available",
                "match_date_source": "steam_gc_match_time",
                "played_at_source": "steam_gc_match_time",
            },
            entry_deaths=4,
            early_deaths=4,
            kast=70,
            adr=80,
        )
    survival = ensure_default_recommendation(db)
    assert survival is not None
    for recommendation in db.scalars(select(CoachRecommendation)).all():
        if recommendation.id != survival.id:
            recommendation.baseline_metrics_json = json.dumps({"matches_count": 15})
    db.commit()
    db.refresh(survival)
    return survival


def _add_steam_demo_match(
    db,
    *,
    external_match_id: str,
    played_at: datetime | None,
    raw_json: dict,
    entry_deaths: int = 2,
    early_deaths: int = 2,
    kast: float = 76,
    adr: float = 82,
) -> Match:
    match = Match(
        source="demo",
        external_match_id=external_match_id,
        played_at=played_at,
        map_name="Mirage",
        result="win",
        rounds_for=13,
        rounds_against=10,
        kills=20,
        deaths=16,
        assists=4,
        kd=1.25,
        adr=adr,
        kast=kast,
        rating=1.05,
        entry_kills=2,
        entry_deaths=entry_deaths,
        early_deaths=early_deaths,
        utility_damage=70,
        flash_assists=1,
        raw_json=json.dumps(raw_json),
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match
