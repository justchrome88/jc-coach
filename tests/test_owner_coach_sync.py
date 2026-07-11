from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db.models import (
    AnalysisRun,
    AppSetting,
    CoachHypothesis,
    CoachMission,
    DemoParseArtifact,
    ImportJob,
    Match,
    MetricSnapshot,
    MissionCriteria,
    MissionProgressEvaluation,
    SteamAccount,
    User,
)
from app.services import owner_coach_sync, steam_integration
from app.services.match_processing import process_owner_match_after_parser_artifact
from app.services.mission_domain import activate_coach_mission, create_analysis_run, create_coach_hypothesis
from app.services.owner_coach_sync import OWNER_COACH_SYNC_RESULT_SCHEMA_VERSION, run_owner_coach_sync

OWNER_STEAM_ID = "76561198000000101"
OTHER_STEAM_ID = "76561198000000202"
SHARE_CODE = "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"


def test_owner_resolution_is_explicit_and_unknown_owner_fails_closed(db):
    owner, account = _owner(db)

    valid = run_owner_coach_sync(db, owner_user_id=owner.id, dry_run=True)
    unknown = run_owner_coach_sync(db, owner_user_id=owner.id + 1000, dry_run=True)

    assert valid["run"]["steam_account_id"] == account.id
    assert valid["run"]["status"] == "success_no_changes"
    assert unknown["run"]["status"] == "blocked"
    assert unknown["errors"][0]["reason_code"] == "owner_not_found"
    assert unknown["discovery"] == {}


@pytest.mark.parametrize("specific_kind", ["match", "sharecode"])
def test_specific_identity_denies_cross_owner_scope(db, specific_kind):
    owner, _ = _owner(db)
    other, other_account = _owner(db, steam_id=OTHER_STEAM_ID, email="other@example.test")
    other_match = _history_match(db, owner=other, account=other_account, sharecode=SHARE_CODE)

    kwargs = {"specific_match_id": other_match.id} if specific_kind == "match" else {"specific_sharecode": SHARE_CODE}
    result = run_owner_coach_sync(db, owner_user_id=owner.id, **kwargs)

    assert result["run"]["status"] == "blocked"
    assert result["errors"][0]["reason_code"] == "cross_owner_match_denied"
    assert db.get(AppSetting, f"lock:owner_coach_sync:{owner.id}") is None


def test_complete_owner_state_is_serializable_noop_without_durable_creation(db, tmp_path):
    owner, account = _owner(db)
    match = _demo_match(db, owner=owner, account=account, demo_file=tmp_path / "complete.dem")
    artifact = _artifact(db, match)
    snapshots = _complete_snapshots(db, match=match, steam_id=account.steam_id, artifact=artifact)
    before = _durable_counts(db)

    first = run_owner_coach_sync(db, owner_user_id=owner.id)
    second = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert first["schema_version"] == OWNER_COACH_SYNC_RESULT_SCHEMA_VERSION
    assert first["run"]["status"] == "success_no_changes"
    assert first["matches"][0]["status"] == "reused"
    assert first["matches"][0]["lineage"]["parser_artifact"]["id"] == artifact.id
    assert first["matches"][0]["lineage"]["metric_snapshot_ids"]["reused"] == [snapshot.id for snapshot in snapshots]
    assert all(bucket["count"] == 0 for bucket in first["mutations"]["created"].values())
    assert second["run"]["status"] == "success_no_changes"
    assert _durable_counts(db) == before
    assert json.loads(json.dumps(first))["schema_version"] == OWNER_COACH_SYNC_RESULT_SCHEMA_VERSION
    assert "payload_json" not in json.dumps(first)


def test_dry_run_plans_new_owner_match_and_creates_nothing(db):
    owner, account = _owner(db)
    history = _history_match(db, owner=owner, account=account, sharecode=SHARE_CODE)
    before = _durable_counts(db)

    result = run_owner_coach_sync(db, owner_user_id=owner.id, dry_run=True)

    assert result["run"]["status"] == "success"
    assert result["run"]["lock"] == {"status": "not_acquired", "reason": "dry_run"}
    assert result["discovery"]["classifications"]["new"] == 1
    assert result["matches"][0]["identity"]["source_match_id"] == history.id
    assert result["matches"][0]["planned_actions"] == [
        "acquire_demo",
        "retain_demo",
        "parse_demo",
        "process_owner_metrics",
        "refresh_coach_state",
    ]
    assert all(bucket["count"] == 0 for bucket in result["mutations"]["created"].values())
    assert _durable_counts(db) == before


def test_new_demo_acquisition_cap_remains_one_per_sync(db):
    owner, account = _owner(db)
    for index in range(3):
        _history_match(
            db,
            owner=owner,
            account=account,
            sharecode=f"{SHARE_CODE}-{index}",
        )

    result = run_owner_coach_sync(db, owner_user_id=owner.id, max_new_matches=3, dry_run=True)

    assert result["discovery"]["candidate_count"] == 3
    assert result["discovery"]["selected_count"] == 1
    assert result["discovery"]["new_demo_acquisition_cap"] == 1
    assert sum(item["selected"] for item in result["matches"]) == 1
    assert sum(item["reason_codes"] == ["new_demo_acquisition_cap"] for item in result["matches"]) == 2


def test_new_match_runs_accepted_phases_and_repeated_input_is_idempotent(db, monkeypatch, tmp_path):
    owner, account = _owner(db)
    history = _history_match(db, owner=owner, account=account, sharecode=SHARE_CODE)
    retained = tmp_path / "retained.dem"
    retained.write_bytes(b"deterministic retained demo")
    calls: list[str] = []

    def acquire(*args, **kwargs):
        calls.append("acquire")
        job = ImportJob(
            provider="steam",
            job_type="demo_import_orchestration",
            status="completed",
            user_id=owner.id,
            steam_account_id=account.id,
            logical_target_key=kwargs["logical_target_key"],
            result_json=json.dumps({"overall_outcome": "completed"}),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        history.demo_file = str(retained)
        history.import_job_id = job.id
        db.commit()
        return job

    def parse(*args, **kwargs):
        calls.append("parse")
        assert calls == ["acquire", "parse"]
        match = _demo_match(db, owner=owner, account=account, demo_file=retained)
        match.import_job_id = kwargs["acquisition_metadata"]["import_job_id"]
        db.commit()
        artifact = _artifact(db, match)
        return {"match_id": match.id, "imported": 1, "skipped_duplicates": 0, "artifact_id": artifact.id}

    def process(*args, **kwargs):
        calls.append("process")
        artifact = db.get(DemoParseArtifact, kwargs["parser_artifact_id"])
        assert artifact is not None
        assert calls == ["acquire", "parse", "process"]
        return process_owner_match_after_parser_artifact(*args, **kwargs)

    monkeypatch.setattr(owner_coach_sync, "run_demo_import_orchestration", acquire)
    monkeypatch.setattr(owner_coach_sync, "import_demo_file", parse)
    monkeypatch.setattr(owner_coach_sync, "process_owner_match_after_parser_artifact", process)

    first = run_owner_coach_sync(db, owner_user_id=owner.id)
    after_first = _durable_counts(db)
    second = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert first["run"]["status"] == "success"
    assert calls == ["acquire", "parse", "process"]
    lineage = first["matches"][0]["lineage"]
    assert lineage["sharecode"] == SHARE_CODE
    assert lineage["import_job"]["id"] == history.import_job_id
    assert lineage["match_id"]
    assert lineage["retained_demo"]["path"] == str(retained)
    assert lineage["parser_artifact"]["id"]
    assert lineage["event_set_ids"][0].startswith("parser-artifact:")
    assert lineage["metric_snapshot_ids"]["created"]
    assert lineage["analysis_run"]["id"] is None
    assert second["run"]["status"] == "success_no_changes"
    assert second["matches"][0]["status"] == "reused"
    assert second["matches"][0]["lineage"]["analysis_run"]["reused"] is None
    assert second["matches"][0]["lineage"]["coach_hypothesis_ids"]["reused"] == []
    assert calls == ["acquire", "parse", "process"]
    assert _durable_counts(db) == after_first


def test_real_sync_rediscovers_preview_identity_and_processes_exactly_one_without_duplicate_lineage(
    db, monkeypatch, tmp_path
):
    owner, account = _owner(db)
    account.match_auth_code = "test-auth-code"
    account.last_share_code = SHARE_CODE
    db.commit()
    fresh = f"{SHARE_CODE}-remote-fresh"
    monkeypatch.setenv("STEAM_WEB_API_KEY", "test-key")
    get_settings.cache_clear()
    responses = [[fresh], []]
    monkeypatch.setattr(steam_integration, "_collect_match_share_codes", lambda **_kwargs: responses.pop(0))
    retained = tmp_path / "remote-fresh.dem"
    retained.write_bytes(b"remote fresh deterministic proof")

    def acquire(*_args, **kwargs):
        source = db.scalar(select(Match).where(Match.external_match_id == fresh))
        job = ImportJob(
            provider="steam",
            job_type="demo_import_orchestration",
            status="completed",
            user_id=owner.id,
            steam_account_id=account.id,
            logical_target_key=kwargs["logical_target_key"],
            result_json=json.dumps({"overall_outcome": "completed"}),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        source.demo_file = str(retained)
        source.import_job_id = job.id
        db.commit()
        return job

    monkeypatch.setattr(owner_coach_sync, "run_demo_import_orchestration", acquire)
    monkeypatch.setattr(owner_coach_sync, "import_demo_file", _fake_parser(db, owner, account, retained))

    first = run_owner_coach_sync(db, owner_user_id=owner.id)
    counts = _durable_counts(db)
    second = run_owner_coach_sync(db, owner_user_id=owner.id)
    identity_hash = hashlib.sha256(fresh.encode()).hexdigest()

    assert first["run"]["status"] == "success"
    assert first["discovery"]["discovery_mode"] == "real_sync"
    assert first["discovery"]["remote_discovery"]["inserted"] == 1
    selected = [item for item in first["matches"] if item["selected"]]
    assert len(selected) == 1
    assert hashlib.sha256(selected[0]["identity"]["sharecode"].encode()).hexdigest() == identity_hash
    assert second["run"]["status"] == "success_no_changes"
    assert db.query(Match).filter(Match.source == "steam_history", Match.external_match_id == fresh).count() == 1
    assert db.query(DemoParseArtifact).count() == counts["demo_parse_artifacts"]
    get_settings.cache_clear()


def test_real_sync_provider_failure_is_explicit_and_does_not_claim_clean_exhaustion(db, monkeypatch):
    owner, account = _owner(db)
    account.match_auth_code = "test-auth-code"
    account.last_share_code = SHARE_CODE
    db.commit()
    monkeypatch.setenv("STEAM_WEB_API_KEY", "test-key")
    get_settings.cache_clear()

    def fail(**_kwargs):
        raise TimeoutError("temporary provider failure")

    monkeypatch.setattr(steam_integration, "_collect_match_share_codes", fail)
    result = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert result["run"]["status"] == "blocked"
    assert result["errors"][0]["reason_code"] == "remote_provider_failure"
    assert result["remote_discovery"]["status"] == "provider_error"
    assert db.query(Match).filter(Match.external_match_id != SHARE_CODE).count() == 0
    get_settings.cache_clear()


def test_existing_retained_import_resumes_at_parser_without_reacquisition(db, monkeypatch, tmp_path):
    owner, account = _owner(db)
    retained = tmp_path / "incomplete.dem"
    retained.write_bytes(b"incomplete deterministic demo")
    history = _history_match(db, owner=owner, account=account, sharecode=SHARE_CODE)
    job = ImportJob(
        provider="steam",
        job_type="demo_import_orchestration",
        status="completed",
        user_id=owner.id,
        steam_account_id=account.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    history.demo_file = str(retained)
    history.import_job_id = job.id
    db.commit()
    calls: list[str] = []

    def parse(*args, **kwargs):
        calls.append("parse")
        match = _demo_match(db, owner=owner, account=account, demo_file=retained)
        match.import_job_id = job.id
        db.commit()
        _artifact(db, match)
        return {"match_id": match.id, "imported": 1, "skipped_duplicates": 0}

    monkeypatch.setattr(
        owner_coach_sync,
        "run_demo_import_orchestration",
        lambda *args, **kwargs: pytest.fail("retained import must not reacquire"),
    )
    monkeypatch.setattr(owner_coach_sync, "import_demo_file", parse)

    result = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert result["run"]["status"] == "success"
    assert calls == ["parse"]
    assert result["matches"][0]["lineage"]["import_job"]["id"] == job.id


def test_existing_artifact_and_snapshot_are_reused_while_missing_work_resumes(db, tmp_path):
    owner, account = _owner(db)
    match = _demo_match(db, owner=owner, account=account, demo_file=tmp_path / "artifact.dem")
    artifact = _artifact(db, match)
    first_processing = process_owner_match_after_parser_artifact(
        db,
        user_id=owner.id,
        match_id=match.id,
        parser_artifact_id=artifact.id,
    )
    utility_id = first_processing["metric_snapshot_ids"]["by_source"]["utility_metrics"]["all"][0]
    db.delete(db.get(MetricSnapshot, utility_id))
    db.commit()
    before_artifact_id = artifact.id

    result = run_owner_coach_sync(db, owner_user_id=owner.id)

    lineage = result["matches"][0]["lineage"]
    assert result["run"]["status"] == "success"
    assert lineage["parser_artifact"]["id"] == before_artifact_id
    assert lineage["metric_snapshot_ids"]["reused"]
    assert lineage["metric_snapshot_ids"]["created"]
    assert lineage["analysis_run"]["created"] is None
    assert first_processing["analysis_run"]["id"] is None


def test_retryable_failure_is_sanitized_releases_lock_and_can_retry(db, monkeypatch, tmp_path):
    owner, account = _owner(db)
    history = _history_match(db, owner=owner, account=account, sharecode=SHARE_CODE)
    clock = {"now": datetime(2026, 7, 10, 12, 0)}
    monkeypatch.setattr(owner_coach_sync, "_utcnow", lambda: clock["now"])

    def fail_acquisition(*args, **kwargs):
        raise RuntimeError("https://steam.invalid/replay?token=super-secret")

    monkeypatch.setattr(owner_coach_sync, "run_demo_import_orchestration", fail_acquisition)
    failed = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert failed["run"]["status"] == "failed"
    assert failed["matches"][0]["status"] == "failed_retryable"
    assert failed["errors"][0]["phase"] == "acquisition"
    assert failed["errors"][0]["retryable"] is True
    assert "super-secret" not in json.dumps(failed)
    assert db.get(AppSetting, f"lock:owner_coach_sync:{owner.id}") is None

    retained = tmp_path / "retry.dem"
    retained.write_bytes(b"retry deterministic demo")

    def acquire(*args, **kwargs):
        job = ImportJob(
            provider="steam",
            job_type="demo_import_orchestration",
            status="completed",
            user_id=owner.id,
            steam_account_id=account.id,
            logical_target_key=kwargs["logical_target_key"],
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        history.demo_file = str(retained)
        history.import_job_id = job.id
        db.commit()
        return job

    monkeypatch.setattr(owner_coach_sync, "run_demo_import_orchestration", acquire)
    monkeypatch.setattr(owner_coach_sync, "import_demo_file", _fake_parser(db, owner, account, retained))
    clock["now"] += owner_coach_sync.RETRY_COOLDOWN + timedelta(seconds=1)

    retried = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert retried["run"]["status"] == "success"
    assert retried["matches"][0]["status"] == "created"


def test_real_baseline_shape_classifies_54_complete_and_9_legacy_pending_as_noop(db, tmp_path):
    owner, account = _owner(db)
    boundary_time = datetime(2026, 7, 10, 12, 0)
    complete_sources = []
    for index in range(54):
        history = _history_match(
            db,
            owner=owner,
            account=account,
            sharecode=f"{SHARE_CODE}-complete-{index}",
        )
        demo = _demo_match(db, owner=owner, account=account, demo_file=tmp_path / f"complete-{index}.dem")
        artifact = _artifact(db, demo)
        _complete_snapshots(db, match=demo, steam_id=account.steam_id, artifact=artifact)
        raw = json.loads(history.raw_json)
        raw.update({"status": "demo_imported", "imported_demo_match_id": demo.id})
        history.raw_json = json.dumps(raw)
        history.created_at = boundary_time - timedelta(days=2)
        complete_sources.append(history)
    for index in range(9):
        legacy = _history_match(
            db,
            owner=owner,
            account=account,
            sharecode=f"{SHARE_CODE}-legacy-{index}",
            raw_extra={"status": "demo_download_pending"},
        )
        legacy.created_at = boundary_time - timedelta(days=3)
    account.last_share_code = complete_sources[-1].external_match_id
    account.last_sync_at = boundary_time
    db.commit()
    before = _durable_counts(db)

    first = run_owner_coach_sync(db, owner_user_id=owner.id, dry_run=True)
    second = run_owner_coach_sync(db, owner_user_id=owner.id, dry_run=True)

    assert first["run"]["status"] == "success_no_changes"
    assert first["discovery"]["candidate_count"] == 63
    assert first["discovery"]["selected_count"] == 0
    assert first["discovery"]["internal_classifications"]["already_complete"] == 54
    assert first["discovery"]["legacy_stale_pending_count"] == 9
    assert first["discovery"]["reason_codes"]["legacy_pending_before_sync_boundary"] == 9
    assert first["discovery"]["remote_discovery_performed"] is False
    assert (
        first["discovery"]["remote_discovery_reason_code"]
        == "remote_discovery_not_performed_in_persisted_dry_run"
    )
    assert all(bucket["count"] == 0 for bucket in first["mutations"]["created"].values())
    assert second["run"]["status"] == "success_no_changes"
    assert _durable_counts(db) == before


def test_deeper_fresh_identity_is_selected_past_stale_terminal_and_cooling_retry(db, monkeypatch, tmp_path):
    owner, account = _owner(db)
    fresh = _history_match(db, owner=owner, account=account, sharecode=f"{SHARE_CODE}-fresh")
    now = datetime(2026, 7, 10, 18, 0)
    retry_time = now - timedelta(hours=6)
    next_eligible_at = now + timedelta(hours=18)
    monkeypatch.setattr(owner_coach_sync, "_utcnow", lambda: now)
    retryable = _history_match(
        db,
        owner=owner,
        account=account,
        sharecode=f"{SHARE_CODE}-retry",
        raw_extra={
            "status": "demo_download_error",
            "error": "temporary_demo_unavailable",
            "owner_coach_sync_failure": {
                "phase": "acquisition",
                "reason_code": "temporary_demo_unavailable",
                "retryable": True,
                "attempt_count": 1,
                "failed_at": retry_time.isoformat(),
                "next_eligible_at": next_eligible_at.isoformat(),
            },
        },
    )
    terminal = _history_match(
        db,
        owner=owner,
        account=account,
        sharecode=f"{SHARE_CODE}-terminal",
        raw_extra={"status": "demo_unavailable", "error": "not found"},
    )
    legacy = _history_match(
        db,
        owner=owner,
        account=account,
        sharecode=f"{SHARE_CODE}-legacy",
        raw_extra={"status": "demo_download_pending"},
    )
    sync_job = ImportJob(
        provider="steam",
        job_type="match_history_sync",
        status="completed",
        user_id=owner.id,
        steam_account_id=account.id,
        result_json=json.dumps(
            {
                "sync_outcome": "SUCCESS_NEW_MATCH_IMPORTED",
                "collected_share_codes": [fresh.external_match_id],
                "inserted": 1,
            }
        ),
        finished_at=retry_time,
    )
    db.add(sync_job)
    fresh.created_at = retry_time - timedelta(minutes=1)
    retryable.created_at = retry_time - timedelta(minutes=1)
    terminal.created_at = retry_time - timedelta(minutes=1)
    legacy.created_at = retry_time - timedelta(minutes=1)
    account.last_share_code = fresh.external_match_id
    account.last_sync_at = retry_time
    db.commit()
    retained = tmp_path / "fresh-after-boundary.dem"
    retained.write_bytes(b"fresh accepted discovery fixture")

    def acquire(*args, **kwargs):
        job = ImportJob(
            provider="steam",
            job_type="demo_import_orchestration",
            status="completed",
            user_id=owner.id,
            steam_account_id=account.id,
            logical_target_key=kwargs["logical_target_key"],
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        fresh.demo_file = str(retained)
        fresh.import_job_id = job.id
        db.commit()
        return job

    monkeypatch.setattr(owner_coach_sync, "run_demo_import_orchestration", acquire)
    monkeypatch.setattr(owner_coach_sync, "import_demo_file", _fake_parser(db, owner, account, retained))

    result = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert result["run"]["status"] == "success"
    selected = [item for item in result["matches"] if item["selected"]]
    assert [item["identity"]["source_match_id"] for item in selected] == [fresh.id]
    assert selected[0]["internal_classification"] == "fresh_actionable"
    assert selected[0]["status"] == "created"
    assert selected[0]["reason_codes"] == ["owner_match_cycle_completed"]
    assert selected[0]["lineage"]["parser_artifact"]["id"]
    assert selected[0]["lineage"]["metric_snapshot_ids"]["created"]
    assert selected[0]["lineage"]["analysis_run"]["id"] is None
    assert result["discovery"]["internal_classifications"]["legacy_stale_pending"] == 1
    assert result["discovery"]["internal_classifications"]["unavailable_terminal"] == 1
    assert result["discovery"]["internal_classifications"]["unavailable_retryable"] == 1


def test_specific_sharecode_can_backfill_legacy_without_changing_ordinary_sync(db):
    owner, account = _owner(db)
    legacy = _history_match(
        db,
        owner=owner,
        account=account,
        sharecode=SHARE_CODE,
        raw_extra={"status": "demo_download_pending"},
    )
    account.last_sync_at = datetime(2026, 7, 10, 12, 0)
    legacy.created_at = account.last_sync_at - timedelta(days=1)
    db.commit()

    ordinary = run_owner_coach_sync(db, owner_user_id=owner.id, dry_run=True)
    backfill = run_owner_coach_sync(
        db,
        owner_user_id=owner.id,
        specific_sharecode=SHARE_CODE,
        dry_run=True,
    )

    assert ordinary["run"]["status"] == "success_no_changes"
    assert ordinary["matches"][0]["internal_classification"] == "legacy_stale_pending"
    assert backfill["run"]["status"] == "success"
    assert backfill["matches"][0]["internal_classification"] == "fresh_actionable"
    assert backfill["matches"][0]["selected"] is True
    assert backfill["discovery"]["reason_codes"] == {"specific_backfill_requested": 1}


def test_accepted_sync_lineage_keeps_31_outstanding_candidates_fresh_after_newest_completion(db, tmp_path):
    owner, account = _owner(db)
    history = [
        _history_match(
            db,
            owner=owner,
            account=account,
            sharecode=f"{SHARE_CODE}-batch-{index}",
        )
        for index in range(32)
    ]
    newest = history[-1]
    demo = _demo_match(db, owner=owner, account=account, demo_file=tmp_path / "newest-complete.dem")
    artifact = _artifact(db, demo)
    _complete_snapshots(db, match=demo, steam_id=account.steam_id, artifact=artifact)
    newest_raw = json.loads(newest.raw_json)
    newest_raw.update({"status": "demo_imported", "imported_demo_match_id": demo.id})
    newest.raw_json = json.dumps(newest_raw)
    sync_time = datetime(2026, 7, 10, 12, 0)
    db.add(
        ImportJob(
            provider="steam",
            job_type="match_history_sync",
            status="completed",
            user_id=owner.id,
            steam_account_id=account.id,
            result_json=json.dumps(
                {
                    "sync_outcome": "SUCCESS_NEW_MATCH_IMPORTED",
                    "collected_share_codes": [item.external_match_id for item in history],
                    "inserted": 32,
                }
            ),
            finished_at=sync_time,
        )
    )
    account.last_share_code = newest.external_match_id
    account.last_sync_at = sync_time
    db.commit()

    result = run_owner_coach_sync(db, owner_user_id=owner.id, dry_run=True)

    assert result["discovery"]["internal_classifications"]["already_complete"] == 1
    assert result["discovery"]["internal_classifications"]["fresh_actionable"] == 31
    assert result["discovery"]["legacy_stale_pending_count"] == 0
    assert result["discovery"]["selected_count"] == 1
    assert result["discovery"]["bounded"] is True


def test_temporary_unavailable_is_cooled_down_and_becomes_terminal_after_bounded_retry(db, monkeypatch):
    owner, account = _owner(db)
    _history_match(db, owner=owner, account=account, sharecode=SHARE_CODE)
    clock = {"now": datetime(2026, 7, 10, 12, 0)}
    calls = 0
    monkeypatch.setattr(owner_coach_sync, "_utcnow", lambda: clock["now"])

    def unavailable(*args, **kwargs):
        nonlocal calls
        calls += 1
        job = ImportJob(
            provider="steam",
            job_type="demo_import_orchestration",
            status="failed",
            user_id=owner.id,
            steam_account_id=account.id,
            logical_target_key=kwargs["logical_target_key"],
            result_json=json.dumps({"acquisition": {"outcome": "steam_unavailable"}}),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    monkeypatch.setattr(owner_coach_sync, "run_demo_import_orchestration", unavailable)

    first = run_owner_coach_sync(db, owner_user_id=owner.id)
    cooling = run_owner_coach_sync(db, owner_user_id=owner.id)
    clock["now"] += owner_coach_sync.RETRY_COOLDOWN + timedelta(seconds=1)
    exhausted = run_owner_coach_sync(db, owner_user_id=owner.id)
    repeated = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert first["matches"][0]["status"] == "failed_retryable"
    assert cooling["run"]["status"] == "success_no_changes"
    assert cooling["matches"][0]["internal_classification"] == "unavailable_retryable"
    assert cooling["matches"][0]["reason_codes"] == ["retry_not_yet_eligible"]
    assert cooling["matches"][0]["retry"]["attempt_count"] == 1
    assert exhausted["matches"][0]["status"] == "failed_terminal"
    assert exhausted["errors"][0]["reason_code"] == "retry_attempts_exhausted"
    assert repeated["run"]["status"] == "success_no_changes"
    assert repeated["matches"][0]["internal_classification"] == "unavailable_terminal"
    assert calls == 2


@pytest.mark.parametrize(
    ("raw_status", "raw_error", "classification"),
    [
        ("demo_download_error", "Replay expired with HTTP 410", "unavailable"),
        ("demo_download_error", "invalid share code", "failed_terminal"),
    ],
)
def test_terminal_or_unavailable_demo_is_not_retried(db, monkeypatch, raw_status, raw_error, classification):
    owner, account = _owner(db)
    _history_match(
        db,
        owner=owner,
        account=account,
        sharecode=SHARE_CODE,
        raw_extra={"status": raw_status, "error": raw_error},
    )
    monkeypatch.setattr(
        owner_coach_sync,
        "run_demo_import_orchestration",
        lambda *args, **kwargs: pytest.fail("terminal candidates must not run acquisition"),
    )

    result = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert result["run"]["status"] == "success_no_changes"
    assert result["matches"][0]["discovery_classification"] == classification
    assert result["matches"][0]["selected"] is False


def test_acquisition_unavailable_result_becomes_durable_terminal_state(db, monkeypatch):
    owner, account = _owner(db)
    history = _history_match(db, owner=owner, account=account, sharecode=SHARE_CODE)
    calls = 0

    def unavailable(*args, **kwargs):
        nonlocal calls
        calls += 1
        job = ImportJob(
            provider="steam",
            job_type="demo_import_orchestration",
            status="failed",
            user_id=owner.id,
            steam_account_id=account.id,
            logical_target_key=kwargs["logical_target_key"],
            result_json=json.dumps({"acquisition": {"outcome": "not_found"}}),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    monkeypatch.setattr(owner_coach_sync, "run_demo_import_orchestration", unavailable)

    first = run_owner_coach_sync(db, owner_user_id=owner.id)
    second = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert first["run"]["status"] == "failed"
    assert first["matches"][0]["status"] == "failed_terminal"
    assert first["matches"][0]["lineage"]["import_job"]["status"] == "failed"
    assert second["run"]["status"] == "success_no_changes"
    assert second["matches"][0]["status"] == "unavailable"
    assert calls == 1
    assert json.loads(history.raw_json)["owner_coach_sync_failure"]["retryable"] is False


def test_max_bound_and_continue_mode_produce_deterministic_partial_success(db, monkeypatch, tmp_path):
    owner, account = _owner(db)
    matches = [
        _demo_match(db, owner=owner, account=account, demo_file=tmp_path / f"match-{index}.dem") for index in range(3)
    ]
    for match in matches:
        _artifact(db, match)
    failing_id = matches[-1].id
    calls: list[int] = []

    def process(*args, **kwargs):
        calls.append(kwargs["match_id"])
        if kwargs["match_id"] == failing_id:
            raise RuntimeError("deterministic parser consumer failure")
        return process_owner_match_after_parser_artifact(*args, **kwargs)

    monkeypatch.setattr(owner_coach_sync, "process_owner_match_after_parser_artifact", process)

    bounded = run_owner_coach_sync(db, owner_user_id=owner.id, max_new_matches=2)

    assert bounded["discovery"]["selected_count"] == 2
    assert bounded["discovery"]["bounded"] is True
    assert bounded["run"]["status"] == "partial_success"
    assert bounded["totals"]["failed"] == 1
    assert len(calls) == 2
    assert sum(item["reason_codes"] == ["max_new_matches_bound"] for item in bounded["matches"]) == 1


def test_strict_mode_stops_after_failure_without_touching_later_match(db, monkeypatch, tmp_path):
    owner, account = _owner(db)
    older = _demo_match(db, owner=owner, account=account, demo_file=tmp_path / "older.dem")
    newest = _demo_match(db, owner=owner, account=account, demo_file=tmp_path / "newest.dem")
    _artifact(db, older)
    _artifact(db, newest)

    def process(*args, **kwargs):
        if kwargs["match_id"] == newest.id:
            raise RuntimeError("strict deterministic failure")
        return process_owner_match_after_parser_artifact(*args, **kwargs)

    monkeypatch.setattr(owner_coach_sync, "process_owner_match_after_parser_artifact", process)
    result = run_owner_coach_sync(
        db,
        owner_user_id=owner.id,
        max_new_matches=2,
        continue_on_match_error=False,
    )

    by_id = {item["identity"]["source_match_id"]: item for item in result["matches"]}
    assert result["run"]["status"] == "failed"
    assert result["run"]["continue_on_match_error"] is False
    assert by_id[newest.id]["status"] == "failed_retryable"
    assert by_id[older.id]["reason_codes"] == ["strict_mode_stopped"]
    assert db.scalar(select(MetricSnapshot).where(MetricSnapshot.match_id == older.id)) is None


def test_owner_keyed_lock_blocks_same_owner_allows_other_owner_and_recovers_stale(db, monkeypatch):
    owner, _ = _owner(db)
    other, _ = _owner(db, steam_id=OTHER_STEAM_ID, email="lock-other@example.test")
    now = datetime(2026, 7, 10, 18, 0)
    monkeypatch.setattr(owner_coach_sync, "_utcnow", lambda: now)
    live = owner_coach_sync._acquire_owner_sync_lock(db, owner_user_id=owner.id)
    assert live is not None

    blocked = run_owner_coach_sync(db, owner_user_id=owner.id)
    other_result = run_owner_coach_sync(db, owner_user_id=other.id)

    assert blocked["run"]["status"] == "already_running"
    assert other_result["run"]["status"] == "success_no_changes"
    assert owner_coach_sync._release_owner_sync_lock(db, live) is True

    stale_value = json.dumps(
        {
            "operation": "owner_coach_sync",
            "token": "stale-token",
            "acquired_at": (now - timedelta(hours=2)).isoformat(),
            "expires_at": (now - timedelta(hours=1)).isoformat(),
        },
        sort_keys=True,
    )
    db.add(AppSetting(key=f"lock:owner_coach_sync:{owner.id}", value=stale_value))
    db.commit()

    recovered = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert recovered["run"]["status"] == "success_no_changes"
    assert recovered["run"]["lock"]["recovered_stale"] is True
    assert recovered["run"]["lock"]["released"] is True
    assert db.get(AppSetting, f"lock:owner_coach_sync:{owner.id}") is None


def test_lock_releases_after_unexpected_exception(db, monkeypatch):
    owner, _ = _owner(db)

    def explode(*args, **kwargs):
        raise RuntimeError("deterministic discovery exception")

    monkeypatch.setattr(owner_coach_sync, "_discover_candidates", explode)

    result = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert result["run"]["status"] == "failed"
    assert result["errors"][0]["reason_code"] == "unexpected_sync_failure"
    assert result["run"]["lock"]["released"] is True
    assert db.get(AppSetting, f"lock:owner_coach_sync:{owner.id}") is None


def test_coach_output_includes_owner_mission_progress_and_suppression(db, tmp_path):
    owner, account = _owner(db)
    mission = _active_mission(db, owner=owner, steam_id=account.steam_id)
    match = _demo_match(db, owner=owner, account=account, demo_file=tmp_path / "mission.dem")
    _artifact(db, match)

    result = run_owner_coach_sync(db, owner_user_id=owner.id)

    assert result["run"]["status"] == "success"
    assert result["coach"]["active_missions"][0]["mission_id"] == mission.id
    assert result["coach"]["latest_progress"][0]["evaluation_id"] is None
    assert result["coach"]["recommendation_suppression"]["suppressed_count"] >= 0
    assert result["matches"][0]["lineage"]["mission_progress_evaluation_ids"]["all"] == []
    assert result["mutations"]["reused"]["missions"]["ids"] == [mission.id]
    assert result["mutations"]["reused"]["criteria"]["count"] == 2


def _owner(
    db,
    *,
    steam_id: str = OWNER_STEAM_ID,
    email: str = "owner@example.test",
) -> tuple[User, SteamAccount]:
    owner = User(email=email, display_name="Owner", password_hash="hash", is_active=1)
    db.add(owner)
    db.commit()
    db.refresh(owner)
    account = SteamAccount(user_id=owner.id, steam_id=steam_id, persona_name="Owner")
    db.add(account)
    db.commit()
    db.refresh(account)
    return owner, account


def _history_match(
    db,
    *,
    owner: User,
    account: SteamAccount,
    sharecode: str,
    raw_extra: dict | None = None,
) -> Match:
    raw = {
        "provider": "steam",
        "steam_account_id": account.id,
        "steam_id": account.steam_id,
        "share_code": sharecode,
        "status": "share_code_collected",
    }
    raw.update(raw_extra or {})
    match = Match(
        user_id=owner.id,
        steam_account_id=account.id,
        source="steam_history",
        external_match_id=sharecode,
        raw_json=json.dumps(raw),
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def _demo_match(db, *, owner: User, account: SteamAccount, demo_file: Path) -> Match:
    match = Match(
        user_id=owner.id,
        steam_account_id=account.id,
        source="demo",
        external_match_id=f"demo-{owner.id}-{account.id}-{demo_file.name}",
        demo_file=str(demo_file),
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def _artifact(db, match: Match, *, status: str = "completed") -> DemoParseArtifact:
    owner_steam_id = db.get(SteamAccount, match.steam_account_id).steam_id
    payload = {
        "parser": "owner-sync-fixture",
        "deep": {
            "round_boundaries": [
                {"round_number": 1, "event_type": "round_end", "tick": 6400},
                {"round_number": 2, "event_type": "round_end", "tick": 12800},
            ],
            "player_hurt_events": [
                {
                    "round_number": 1,
                    "tick": 1200,
                    "attacker_name": "Owner",
                    "attacker_steamid": owner_steam_id,
                    "victim_name": "Other",
                    "victim_steamid": OTHER_STEAM_ID,
                    "weapon": "hegrenade",
                    "damage_health": 30,
                }
            ],
            "player_death_events": [
                {
                    "round_number": 2,
                    "tick": 9200,
                    "attacker_name": "Other",
                    "attacker_steamid": OTHER_STEAM_ID,
                    "victim_name": "Owner",
                    "victim_steamid": owner_steam_id,
                    "weapon": "m4a1",
                }
            ],
            "player_rounds": [
                {
                    "round_number": 1,
                    "player_name": "Owner",
                    "player_steamid": owner_steam_id,
                    "survived": True,
                },
                {
                    "round_number": 2,
                    "player_name": "Owner",
                    "player_steamid": owner_steam_id,
                    "survived": False,
                },
            ],
            "grenade_events": [
                {
                    "round_number": 1,
                    "tick": 1100,
                    "player_name": "Owner",
                    "player_steamid": owner_steam_id,
                    "grenade_type": "hegrenade",
                }
            ],
        },
    }
    artifact = DemoParseArtifact(
        match_id=match.id,
        import_job_id=match.import_job_id,
        parser_name="owner-sync-fixture",
        parser_version="g01",
        payload_version="owner-sync-fixture-v1",
        status=status,
        source_demo_file=match.demo_file,
        demo_sha1=f"{match.id:040d}"[-40:],
        event_counts_json=json.dumps({"player_hurt": 1, "player_death": 1}),
        confidence_json=json.dumps(
            {
                "parser_confidence": "medium",
                "metric_confidence": {
                    "adr": "medium",
                    "entry_duels": "medium",
                    "grenades": "medium",
                    "kast": "medium",
                    "utility": "medium",
                },
            }
        ),
        data_gaps_json=json.dumps([]),
        payload_json=json.dumps(payload),
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def _complete_snapshots(
    db,
    *,
    match: Match,
    steam_id: str,
    artifact: DemoParseArtifact,
) -> list[MetricSnapshot]:
    snapshots = []
    for source in ("core_combat_metrics", "utility_metrics"):
        snapshot = MetricSnapshot(
            match_id=match.id,
            player_key=f"steam:{steam_id}",
            player_name="Owner",
            player_steamid=steam_id,
            source=source,
            source_parser_artifact_id=artifact.id,
            source_event_set_id=f"parser-artifact:{artifact.id}:events:fixture",
            metrics_json=json.dumps({"utility_damage": 30, "survival_rate": 0.5}),
            confidence_baseline_json=json.dumps({"overall": "medium"}),
            caveats_json=json.dumps([]),
            metadata_json=json.dumps({}),
        )
        db.add(snapshot)
        snapshots.append(snapshot)
    db.commit()
    for snapshot in snapshots:
        db.refresh(snapshot)
    return snapshots


def _fake_parser(db, owner: User, account: SteamAccount, retained: Path):
    def parse(*args, **kwargs):
        match = _demo_match(db, owner=owner, account=account, demo_file=retained)
        match.import_job_id = kwargs["acquisition_metadata"]["import_job_id"]
        db.commit()
        _artifact(db, match)
        return {"match_id": match.id, "imported": 1, "skipped_duplicates": 0}

    return parse


def _active_mission(db, *, owner: User, steam_id: str) -> CoachMission:
    run = create_analysis_run(db, user_id=owner.id, owner_steam_id=steam_id)
    hypothesis = create_coach_hypothesis(
        db,
        user_id=owner.id,
        analysis_run_id=run.id,
        insight_card={
            "id": "g01-duel-mission",
            "problem": "Opening deaths need a measurable owner mission.",
            "evidence": [{"metric_id": "opening_death_rate", "value": 0.3, "metric_confidence": "medium"}],
            "confidence": "medium",
            "caveats": [],
            "recommended_focus": "Review bounded opening-death evidence.",
            "mission_readiness": {
                "can_become_mission": True,
                "canonical_domain_key": "bad_fight_selection",
                "family": "bad_fight_selection",
                "target_metric_candidate": "opening_death_rate",
                "baseline_value": 0.3,
                "confidence_eligibility": {
                    "level": "medium",
                    "usable_for_missions": True,
                    "hard_recommendation_eligible": True,
                },
                "blocking_reason_codes": [],
            },
        },
    )
    return activate_coach_mission(
        db,
        user_id=owner.id,
        hypothesis_id=hypothesis.id,
        title="Improve opening duel discipline",
    )


def _durable_counts(db) -> dict[str, int]:
    models = (
        ImportJob,
        Match,
        DemoParseArtifact,
        MetricSnapshot,
        AnalysisRun,
        CoachHypothesis,
        CoachMission,
        MissionCriteria,
        MissionProgressEvaluation,
        AppSetting,
    )
    return {model.__tablename__: db.query(model).count() for model in models}
