from __future__ import annotations

import json
from datetime import UTC, datetime

from app.config import get_settings
from app.db.models import ImportJob, Match, SteamAccount, User
from app.services.fresh_match_discovery import (
    FRESH_DISCOVERY_EVIDENCE_SCHEMA_VERSION,
    PERSISTED_DRY_RUN_REASON,
    fresh_match_ready_for_h01a,
    persisted_dry_run_evidence,
    preview_owner_fresh_matches,
)
from app.services.owner_coach_sync import run_owner_coach_sync

CURSOR = "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"
FRESH = "CSGO-cAQhC-XL4SM-wWoxt-NNdVO-anUaK"


def test_remote_preview_exposes_fresh_safe_identity_without_persistence_or_cursor_advance(db, monkeypatch):
    owner, account = _owner(db, monkeypatch)
    before = _state(db, account)

    evidence = preview_owner_fresh_matches(
        db,
        owner_user_id=owner.id,
        collector=lambda **_kwargs: [FRESH],
        db_sha_before="same",
        db_sha_after="same",
        discovered_at=datetime(2026, 7, 11, tzinfo=UTC),
    )

    assert evidence["schema_version"] == FRESH_DISCOVERY_EVIDENCE_SCHEMA_VERSION
    assert evidence["fresh_actionable_count"] == 1
    assert evidence["persisted"] is False
    assert evidence["actionable"] is True
    assert evidence["safe_identity_suffix"].endswith(FRESH[-8:])
    assert FRESH not in json.dumps(evidence)
    assert evidence["logical_state_unchanged"] is True
    assert evidence["mutation_count"] == 0
    assert _state(db, account) == before


def test_remote_preview_is_owner_scoped_and_cross_owner_fails_closed(db, monkeypatch):
    owner, account = _owner(db, monkeypatch)
    other = User(email="other@example.test", display_name="Other", password_hash="hash", is_active=1)
    db.add(other)
    db.commit()
    db.refresh(other)

    evidence = preview_owner_fresh_matches(
        db,
        owner_user_id=other.id,
        steam_account_id=account.id,
        collector=lambda **_kwargs: [FRESH],
    )

    assert evidence["status"] == "blocked"
    assert evidence["steam_account_id"] is None
    assert evidence["fresh_actionable_count"] == 0
    assert evidence["provider_errors"][0]["reason_code"] == "owner_steam_account_mismatch"


def test_remote_preview_provider_failure_is_explicit_and_non_mutating(db, monkeypatch):
    owner, account = _owner(db, monkeypatch)
    before = _state(db, account)

    def fail(**_kwargs):
        raise TimeoutError("provider details must not escape")

    evidence = preview_owner_fresh_matches(db, owner_user_id=owner.id, collector=fail)

    assert evidence["status"] == "provider_error"
    assert evidence["provider_errors"] == [
        {
            "reason_code": "remote_provider_failure",
            "safe_message": "Remote Steam discovery failed.",
            "exception_class": "TimeoutError",
        }
    ]
    assert "provider details" not in json.dumps(evidence)
    assert _state(db, account) == before


def test_persisted_dry_run_is_explicitly_remote_isolated_and_non_contradictory(db, monkeypatch):
    owner, account = _owner(db, monkeypatch)
    account.last_sync_at = datetime(2030, 1, 1)
    db.commit()
    for index in range(9):
        _persisted_match(db, owner, account, f"legacy-{index}")

    result = run_owner_coach_sync(db, owner_user_id=owner.id, dry_run=True)
    evidence = persisted_dry_run_evidence(owner_user_id=owner.id, steam_account_id=account.id, result=result)

    assert result["discovery"]["remote_discovery_performed"] is False
    assert result["discovery"]["remote_discovery_reason_code"] == PERSISTED_DRY_RUN_REASON
    assert evidence["mutation_count"] == 0
    assert evidence["fresh_actionable_count"] == 0
    assert evidence["legacy_stale_pending"] == 9
    assert PERSISTED_DRY_RUN_REASON in evidence["reason_codes"]


def test_combined_contract_marks_fresh_ready_but_never_processing_success_from_preview_alone(db, monkeypatch):
    owner, account = _owner(db, monkeypatch)
    remote = preview_owner_fresh_matches(
        db,
        owner_user_id=owner.id,
        collector=lambda **_kwargs: [FRESH],
    )
    dry_result = run_owner_coach_sync(db, owner_user_id=owner.id, dry_run=True)
    dry = persisted_dry_run_evidence(owner_user_id=owner.id, steam_account_id=account.id, result=dry_result)
    proof = {
        "preview_identity_hash": remote["safe_identity_hash"],
        "consumed_identity_hash": remote["safe_identity_hash"],
        "processed_exactly_one": True,
        "duplicate_lineage_created": False,
    }

    ready = fresh_match_ready_for_h01a(remote_preview=remote, persisted_dry_run=dry, real_sync_proof=proof)
    stale = fresh_match_ready_for_h01a(remote_preview=remote, persisted_dry_run=dry, real_sync_proof={})

    assert ready["decision"] == "FRESH_MATCH_READY_FOR_H01A"
    assert stale["decision"] == "NOT_READY"
    assert remote["persisted"] is False
    assert db.query(Match).filter(Match.external_match_id == FRESH).count() == 0


def _owner(db, monkeypatch) -> tuple[User, SteamAccount]:
    monkeypatch.setenv("STEAM_WEB_API_KEY", "test-key")
    get_settings.cache_clear()
    owner = User(email="owner@example.test", display_name="Owner", password_hash="hash", is_active=1)
    db.add(owner)
    db.commit()
    db.refresh(owner)
    account = SteamAccount(
        user_id=owner.id,
        steam_id="76561198056634139",
        persona_name="Owner",
        match_auth_code="test-auth-code",
        last_share_code=CURSOR,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return owner, account


def _persisted_match(db, owner: User, account: SteamAccount, identity: str, *, status: str = "share_code_collected"):
    match = Match(
        user_id=owner.id,
        steam_account_id=account.id,
        source="steam_history",
        external_match_id=identity,
        raw_json=json.dumps(
            {
                "provider": "steam",
                "steam_account_id": account.id,
                "steam_id": account.steam_id,
                "share_code": identity,
                "status": status,
            }
        ),
    )
    db.add(match)
    db.commit()
    return match


def _state(db, account: SteamAccount) -> tuple[int, int, str | None, object]:
    db.refresh(account)
    return (
        db.query(Match).count(),
        db.query(ImportJob).count(),
        account.last_share_code,
        account.last_sync_at,
    )
