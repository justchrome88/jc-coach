import json
import subprocess

from app.db.models import Match
from app.services.ingestion.demo_acquisition import (
    DEMO_ALREADY_AVAILABLE,
    DEMO_AUTH_MISSING,
    DEMO_DOWNLOAD_QUEUED_OR_READY,
    DEMO_RATE_LIMITED_OR_TIMEOUT,
    acquire_steam_demo_reference,
    run_steam_demo_acquisition_job,
    validate_steam_demo_acquisition_config,
)
from app.services.ingestion.jobs import create_import_request

SHARE_CODE = "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"


def test_demo_acquisition_reports_auth_missing_without_secret_values(db, monkeypatch):
    monkeypatch.setenv("STEAM_BOT_USERNAME", "")
    monkeypatch.setenv("STEAM_BOT_PASSWORD", "")
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "")
    from app.config import get_settings

    get_settings.cache_clear()
    db.add(
        Match(
            source="steam_history",
            external_match_id=SHARE_CODE,
            raw_json=json.dumps({"share_code": SHARE_CODE}),
        )
    )
    db.commit()
    job = create_import_request(
        db,
        provider="steam",
        job_type="demo_acquisition",
        payload={"share_code": SHARE_CODE},
        initial_status="queued",
    )

    try:
        result = run_steam_demo_acquisition_job(db, job.id)
    finally:
        get_settings.cache_clear()

    db.refresh(job)
    persisted = json.loads(job.result_json)
    assert result["status"] == "failed"
    assert persisted["overall_outcome"] == DEMO_AUTH_MISSING
    assert persisted["config"]["credential_mode"] == "missing"
    assert "STEAM_BOT_REFRESH_TOKEN" in persisted["config"]["missing"][0]
    assert "secret" not in json.dumps(persisted).lower()


def test_demo_acquisition_job_persists_mocked_download_ready_result(db, monkeypatch):
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "test-refresh-token")
    from app.config import get_settings

    get_settings.cache_clear()
    match = Match(
        source="steam_history",
        external_match_id=SHARE_CODE,
        raw_json=json.dumps({"share_code": SHARE_CODE, "status": "demo_download_pending"}),
    )
    db.add(match)
    db.commit()
    job = create_import_request(
        db,
        provider="steam",
        job_type="demo_acquisition",
        payload={"share_code": SHARE_CODE},
        initial_status="queued",
    )

    def fake_fetcher(codes):
        assert codes == [SHARE_CODE]
        return {
            "ok": True,
            "results": [
                {
                    "ok": True,
                    "share_code": SHARE_CODE,
                    "match_id": "3822708819734036647",
                    "match_time": 1783022400,
                    "demo_url": "https://replay.example.test/demo.dem.bz2",
                }
            ],
        }

    try:
        result = run_steam_demo_acquisition_job(db, job.id, fetcher=fake_fetcher)
    finally:
        get_settings.cache_clear()

    db.refresh(job)
    db.refresh(match)
    persisted = json.loads(job.result_json)
    raw = json.loads(match.raw_json)
    assert result["status"] == "completed"
    assert persisted["overall_outcome"] == DEMO_DOWNLOAD_QUEUED_OR_READY
    assert persisted["demo_reference"]["host"] == "replay.example.test"
    assert persisted["demo_reference"]["has_url"] is True
    assert persisted["helper_payload_status"] == {"ok": True, "results_count": 1}
    assert raw["demo_acquisition"]["outcome"] == DEMO_DOWNLOAD_QUEUED_OR_READY


def test_demo_acquisition_maps_timeout_to_actionable_result(db, monkeypatch):
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "test-refresh-token")
    from app.config import get_settings

    get_settings.cache_clear()
    db.add(Match(source="steam_history", external_match_id=SHARE_CODE, raw_json=json.dumps({"share_code": SHARE_CODE})))
    db.commit()

    def timeout_fetcher(_codes):
        raise subprocess.TimeoutExpired(cmd=["node", "fetch-demo-urls.js"], timeout=15)

    try:
        result = acquire_steam_demo_reference(db, share_code=SHARE_CODE, fetcher=timeout_fetcher)
    finally:
        get_settings.cache_clear()

    assert result["overall_outcome"] == DEMO_RATE_LIMITED_OR_TIMEOUT
    assert result["clean_success"] is False
    assert result["error"]["type"] == "TimeoutExpired"
    assert "Retry later" in result["next_action"]


def test_demo_acquisition_returns_already_available_without_fetching(db, monkeypatch):
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "test-refresh-token")
    from app.config import get_settings

    get_settings.cache_clear()
    db.add(
        Match(
            source="steam_history",
            external_match_id=SHARE_CODE,
            demo_file="/opt/jc-coach/data/incoming_demos/existing.dem",
            raw_json=json.dumps({"share_code": SHARE_CODE, "status": "demo_imported"}),
        )
    )
    db.commit()

    def fail_if_called(_codes):
        raise AssertionError("already available acquisition must not call Steam")

    try:
        result = acquire_steam_demo_reference(db, share_code=SHARE_CODE, fetcher=fail_if_called)
    finally:
        get_settings.cache_clear()

    assert result["overall_outcome"] == DEMO_ALREADY_AVAILABLE
    assert result["clean_success"] is True
    assert result["next_action"].startswith("Use the existing stored demo")


def test_demo_acquisition_config_validation_reports_public_status(monkeypatch):
    monkeypatch.setenv("STEAM_BOT_USERNAME", "bot-user")
    monkeypatch.setenv("STEAM_BOT_PASSWORD", "bot-password")
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        status = validate_steam_demo_acquisition_config()
    finally:
        get_settings.cache_clear()

    assert status["auth_configured"] is True
    assert status["credential_mode"] == "username_password"
    assert "bot-password" not in json.dumps(status)
