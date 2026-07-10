from __future__ import annotations

import json

from app.db.models import AppSetting
from app.services import owner_coach_sync_batch as batch_service


def test_successful_target_stops_exactly_at_31_and_skips_32nd_success(db, monkeypatch):
    owner_id = 101
    successes = [1, *range(5, 38)]  # 34 eventual successes; target must stop after source id 34.
    outcomes = {-2: "stale", -1: "stale", 1: "success", 2: "unavailable", 3: "retryable", 4: "complete"}
    outcomes.update({source_id: "success" for source_id in successes if source_id != 1})
    calls: list[int | None] = []

    def fake_g01(_db, *, specific_match_id=None, **_kwargs):
        calls.append(specific_match_id)
        if specific_match_id is None:
            return _result(
                [_item(source_id, outcome, selected=source_id == 1) for source_id, outcome in outcomes.items()]
            )
        return _result([_item(specific_match_id, outcomes[specific_match_id], selected=True)])

    monkeypatch.setattr(batch_service, "run_owner_coach_sync", fake_g01)
    batch = batch_service.start_owner_coach_sync_batch(
        db, owner_user_id=owner_id, mode="successful_target", target_successful_new_matches=31
    )
    while batch["batch"]["status"] not in batch_service.TERMINAL_STATUSES:
        batch = batch_service.run_owner_coach_sync_batch_step(
            db, owner_user_id=owner_id, batch_id=batch["batch"]["batch_id"]
        )

    assert batch["batch"]["status"] == "target_reached"
    assert batch["batch"]["stop_reason"] == "successful_target_reached"
    assert batch["batch"]["successful_new_matches"] == 31
    assert 35 not in calls  # source 35 would have been the 32nd successful completion
    assert batch["aggregate_totals"]["unavailable"] == 3
    assert batch["aggregate_totals"]["retryable_failures"] == 1
    assert batch["aggregate_totals"]["reused"] == 1
    assert batch["aggregate_totals"]["legacy_stale_pending"] == 2
    assert -2 not in calls and -1 not in calls
    retry = next(item["retry"] for item in batch["matches"] if item["identity"]["source_match_id"] == 3)
    assert retry["attempt_count"] == 2
    assert retry["decision"] == "terminal_skip"
    assert len({item["identity"]["source_match_id"] for item in batch["matches"]}) == len(batch["matches"])
    assert json.loads(json.dumps(batch))["schema_version"] == batch_service.OWNER_COACH_SYNC_BATCH_RESULT_SCHEMA_VERSION
    assert "token" not in json.dumps(batch)


def test_restart_resume_preserves_12_completed_matches_without_recounting(db, monkeypatch):
    owner_id = 102
    outcomes = {-1: "stale", **{source_id: "success" for source_id in range(1, 40)}}

    def fake_g01(_db, *, specific_match_id=None, **_kwargs):
        if specific_match_id is None:
            return _result(
                [_item(source_id, outcome, selected=source_id == 1) for source_id, outcome in outcomes.items()]
            )
        return _result([_item(specific_match_id, outcomes[specific_match_id], selected=True)])

    monkeypatch.setattr(batch_service, "run_owner_coach_sync", fake_g01)
    batch = batch_service.start_owner_coach_sync_batch(
        db, owner_user_id=owner_id, mode="successful_target", target_successful_new_matches=31
    )
    for _ in range(12):
        batch = batch_service.run_owner_coach_sync_batch_step(
            db, owner_user_id=owner_id, batch_id=batch["batch"]["batch_id"]
        )
    assert batch["batch"]["successful_new_matches"] == 12

    resumed = batch_service.start_owner_coach_sync_batch(
        db, owner_user_id=owner_id, mode="successful_target", target_successful_new_matches=31
    )
    assert resumed["batch"]["batch_id"] == batch["batch"]["batch_id"]
    assert resumed["batch"]["status"] == "already_running"
    while batch["batch"]["status"] not in batch_service.TERMINAL_STATUSES:
        batch = batch_service.run_owner_coach_sync_batch_step(
            db, owner_user_id=owner_id, batch_id=batch["batch"]["batch_id"]
        )
    assert batch["batch"]["successful_new_matches"] == 31
    assert batch["batch"]["status"] == "target_reached"
    assert len({item["identity"]["source_match_id"] for item in batch["matches"]}) == len(batch["matches"])
    assert batch["aggregate_totals"]["legacy_stale_pending"] == 1


def test_same_owner_double_start_reuses_one_batch_and_different_owners_are_independent(db):
    first = batch_service.start_owner_coach_sync_batch(db, owner_user_id=201)
    second = batch_service.start_owner_coach_sync_batch(db, owner_user_id=201)
    other = batch_service.start_owner_coach_sync_batch(db, owner_user_id=202)

    assert first["batch"]["batch_id"] == second["batch"]["batch_id"]
    assert second["batch"]["status"] == "already_running"
    assert other["batch"]["batch_id"] != first["batch"]["batch_id"]
    assert db.get(AppSetting, "lock:owner_coach_sync_batch:201") is not None
    assert db.get(AppSetting, "lock:owner_coach_sync_batch:202") is not None


def test_stale_batch_lock_recovers_the_same_durable_batch(db):
    first = batch_service.start_owner_coach_sync_batch(db, owner_user_id=250)
    lock = db.get(AppSetting, "lock:owner_coach_sync_batch:250")
    assert lock is not None
    payload = json.loads(lock.value)
    payload["expires_at"] = "2000-01-01T00:00:00"
    lock.value = json.dumps(payload, sort_keys=True)
    db.commit()

    resumed = batch_service.start_owner_coach_sync_batch(db, owner_user_id=250)

    assert resumed["batch"]["batch_id"] == first["batch"]["batch_id"]
    assert resumed["batch"]["status"] == "already_running"


def test_no_progress_guard_and_terminal_lock_release(db, monkeypatch):
    owner_id = 301
    monkeypatch.setattr(
        batch_service,
        "run_owner_coach_sync",
        lambda _db, **_kwargs: _result([_item(1, "stalled", selected=True)]),
    )
    batch = batch_service.start_owner_coach_sync_batch(
        db, owner_user_id=owner_id, mode="successful_target", target_successful_new_matches=31
    )
    for _ in range(batch_service.MAX_NO_PROGRESS_ITERATIONS):
        batch = batch_service.run_owner_coach_sync_batch_step(
            db, owner_user_id=owner_id, batch_id=batch["batch"]["batch_id"]
        )

    assert batch["batch"]["status"] == "blocked"
    assert batch["batch"]["stop_reason"] == "no_progress_guard"
    assert db.get(AppSetting, f"lock:owner_coach_sync_batch:{owner_id}") is None


def test_exception_finalizes_and_releases_batch_lock(db, monkeypatch):
    owner_id = 302
    monkeypatch.setattr(
        batch_service, "run_owner_coach_sync", lambda _db, **_kwargs: (_ for _ in ()).throw(RuntimeError())
    )
    batch = batch_service.start_owner_coach_sync_batch(db, owner_user_id=owner_id)
    batch = batch_service.run_owner_coach_sync_batch_step(
        db, owner_user_id=owner_id, batch_id=batch["batch"]["batch_id"]
    )

    assert batch["batch"]["status"] == "failed"
    assert batch["batch"]["stop_reason"] == "unexpected_failure"
    assert db.get(AppSetting, f"lock:owner_coach_sync_batch:{owner_id}") is None


def test_missing_completion_lineage_blocks_without_counting(db, monkeypatch):
    incomplete = _item(1, "success", selected=True)
    incomplete["lineage"]["analysis_run"]["id"] = None
    monkeypatch.setattr(batch_service, "run_owner_coach_sync", lambda _db, **_kwargs: _result([incomplete]))
    batch = batch_service.start_owner_coach_sync_batch(
        db, owner_user_id=303, mode="successful_target", target_successful_new_matches=31
    )
    batch = batch_service.run_owner_coach_sync_batch_step(db, owner_user_id=303, batch_id=batch["batch"]["batch_id"])

    assert batch["batch"]["status"] == "blocked"
    assert batch["batch"]["stop_reason"] == "required_completion_lineage_missing"
    assert batch["batch"]["successful_new_matches"] == 0


def _result(matches):
    return {
        "run": {
            "status": "success",
            "started_at": "2026-07-10T00:00:00",
            "finished_at": "2026-07-10T00:00:01",
            "duration_ms": 1,
        },
        "discovery": {"candidate_count": len(matches), "selected_count": 1, "classifications": {}, "bounded": True},
        "totals": {},
        "matches": matches,
        "mutations": {"created": {"matches": {"count": 0, "ids": []}}},
        "coach": {"active_missions": [], "latest_progress": []},
        "warnings": [],
        "errors": [],
    }


def _item(source_id: int, outcome: str, *, selected: bool):
    classification = {
        "unavailable": "unavailable",
        "retryable": "failed_retryable",
        "complete": "already_complete",
        "stale": "unavailable",
    }.get(outcome, "new")
    if not selected:
        status = {"unavailable": "unavailable", "complete": "reused", "stale": "unavailable"}.get(
            outcome, "skipped"
        )
    else:
        status = {
            "success": "created",
            "retryable": "failed_retryable",
            "complete": "reused",
            "unavailable": "unavailable",
        }.get(outcome, "skipped")
    lineage = {
        "parser_artifact": {"id": source_id, "status": "accepted"},
        "event_set_ids": [f"event:{source_id}"],
        "metric_snapshot_ids": {"all": [source_id], "created": [source_id], "reused": []},
        "analysis_run": {"id": source_id, "created": source_id, "reused": None},
        "retained_demo": {"path": "/sensitive/example.dem", "sha1": f"sha-{source_id}"},
    }
    return {
        "identity": {"source_match_id": source_id, "sharecode": f"share-{source_id}"},
        "discovery_classification": classification,
        "internal_classification": "legacy_stale_pending" if outcome == "stale" else None,
        "selected": selected,
        "status": status,
        "reason_codes": ["owner_match_cycle_completed"] if outcome == "success" and selected else [outcome],
        "lineage": lineage,
        "failure": {"reason_code": "download_failed", "safe_message": "safe"} if status == "failed_retryable" else None,
    }
