import json

from app.db.models import ImportJob, Match
from app.services.steam_integration import (
    STEAM_INITIAL_CURSOR_SENTINEL,
    STEAM_SYNC_DUPLICATE_ALREADY_IMPORTED,
    STEAM_SYNC_STEAM_TEMPORARY_ERROR,
    STEAM_SYNC_SUCCESS_NEW_MATCH_IMPORTED,
    STEAM_SYNC_SUCCESS_NO_NEW_MATCHES,
    link_steam_account,
    sync_match_history_job,
    update_match_auth_code,
)

INITIAL_CODE = "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"
NEXT_CODE = "CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK"
THIRD_CODE = "CSGO-SYSZK-hOFfp-WtBsM-WtsNK-pcy6A"


def _prepare_sync_job(db, monkeypatch, latest_share_code=None):
    monkeypatch.setenv("STEAM_WEB_API_KEY", "web-api-key")
    from app.config import get_settings

    get_settings.cache_clear()
    account = link_steam_account(db, "76561198056634139", persona_name="JC")
    update_match_auth_code(db, account.id, "AUTH-CODE", latest_share_code)
    job = db.query(ImportJob).filter(ImportJob.job_type == "match_history_sync").one()
    return account, job, get_settings


def test_initial_cursor_uses_explicit_knowncode_zero_sentinel(db, monkeypatch):
    account, job, get_settings = _prepare_sync_job(db, monkeypatch)
    captured = {}

    def fake_collect(**kwargs):
        captured.update(kwargs)
        return [NEXT_CODE]

    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", fake_collect)
    try:
        result = sync_match_history_job(db, job.id)
    finally:
        get_settings.cache_clear()

    db.refresh(account)
    payload = result["result"]
    assert captured["known_code"] == STEAM_INITIAL_CURSOR_SENTINEL
    assert payload["cursor_source"] == "initial_sentinel_no_saved_cursor"
    assert payload["knowncode_zero_is_initial_sentinel"] is True
    assert payload["sync_outcome"] == STEAM_SYNC_SUCCESS_NEW_MATCH_IMPORTED
    assert payload["cursor_advanced"] is True
    assert account.last_share_code == NEXT_CODE


def test_successful_new_match_advances_cursor_only_after_local_persistence(db, monkeypatch):
    account, job, get_settings = _prepare_sync_job(db, monkeypatch, INITIAL_CODE)
    monkeypatch.setattr(
        "app.services.steam_integration._collect_match_share_codes",
        lambda **_kwargs: [NEXT_CODE, THIRD_CODE],
    )
    try:
        result = sync_match_history_job(db, job.id)
    finally:
        get_settings.cache_clear()

    db.refresh(account)
    assert result["result"]["sync_outcome"] == STEAM_SYNC_SUCCESS_NEW_MATCH_IMPORTED
    assert result["result"]["inserted"] == 2
    assert result["result"]["cursor_advanced"] is True
    assert account.last_share_code == THIRD_CODE
    assert db.query(Match).filter(Match.source == "steam_history").count() == 3


def test_failed_steam_response_does_not_advance_cursor(db, monkeypatch):
    account, job, get_settings = _prepare_sync_job(db, monkeypatch, INITIAL_CODE)

    def fake_collect(**_kwargs):
        raise RuntimeError("temporary Steam API failure")

    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", fake_collect)
    try:
        result = sync_match_history_job(db, job.id)
    finally:
        get_settings.cache_clear()

    db.refresh(account)
    db.refresh(job)
    assert result["status"] == "failed"
    assert result["result"]["sync_outcome"] == STEAM_SYNC_STEAM_TEMPORARY_ERROR
    assert "temporary Steam API failure" in result["error"]
    assert account.last_share_code == INITIAL_CODE


def test_duplicate_share_code_does_not_create_duplicate_and_can_advance_cursor(db, monkeypatch):
    account, job, get_settings = _prepare_sync_job(db, monkeypatch, INITIAL_CODE)
    db.add(
        Match(
            source="steam_history",
            external_match_id=NEXT_CODE,
            raw_json=json.dumps({"provider": "steam", "share_code": NEXT_CODE}),
        )
    )
    db.commit()
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [NEXT_CODE])
    try:
        result = sync_match_history_job(db, job.id)
    finally:
        get_settings.cache_clear()

    db.refresh(account)
    assert result["result"]["sync_outcome"] == STEAM_SYNC_DUPLICATE_ALREADY_IMPORTED
    assert result["result"]["inserted"] == 0
    assert result["result"]["duplicates"] == 1
    assert account.last_share_code == NEXT_CODE
    assert db.query(Match).filter(Match.source == "steam_history", Match.external_match_id == NEXT_CODE).count() == 1


def test_no_new_matches_is_success_and_does_not_advance_cursor(db, monkeypatch):
    account, job, get_settings = _prepare_sync_job(db, monkeypatch, INITIAL_CODE)
    monkeypatch.setattr("app.services.steam_integration._collect_match_share_codes", lambda **_kwargs: [])
    try:
        result = sync_match_history_job(db, job.id)
    finally:
        get_settings.cache_clear()

    db.refresh(account)
    assert result["status"] == "completed"
    assert result["result"]["sync_outcome"] == STEAM_SYNC_SUCCESS_NO_NEW_MATCHES
    assert result["result"]["cursor_advanced"] is False
    assert account.last_share_code == INITIAL_CODE
