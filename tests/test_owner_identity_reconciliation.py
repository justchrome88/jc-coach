from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, text

from app.db.models import Base
from app.services.owner.reconciliation import OwnerReconciliationError, reconcile_owner_identity

EVIDENCE = [
    "legacy_created_by_pre_auth_steam_bootstrap",
    "canonical_only_active_credentialed_owner",
    "auth_introduced_after_legacy_creation",
    "legacy_has_no_credentials_or_login",
]


@pytest.fixture
def reconciliation_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reconciliation.db'}", future=True)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users(id,display_name,email,password_hash,is_active) VALUES "
                "(1,'Steam 0001',NULL,NULL,1),"
                "(17,'Owner','owner@example.com','hash',1),"
                "(18,'Other','other@example.com','hash',1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO steam_accounts(id,user_id,steam_id,sync_enabled) "
                "VALUES (1,1,'76561198000000001',1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO import_jobs(id,provider,job_type,status,user_id,steam_account_id,requested_payload_json) "
                "VALUES (1,'steam','history','completed',1,1,:payload)"
            ),
            {"payload": json.dumps({"owner_user_id": 1, "secret": "unchanged"})},
        )
        connection.execute(
            text(
                "INSERT INTO matches(id,user_id,steam_account_id,import_job_id,source,external_match_id,raw_json) "
                "VALUES (1,1,1,1,'steam','match-1',:payload)"
            ),
            {"payload": json.dumps({"user_id": 1})},
        )
        connection.execute(
            text(
                "INSERT INTO analysis_runs("
                "id,user_id,mode,status,selected_metric_snapshot_ids_json,analysis_scope_json,source_payload_json"
                ") "
                "VALUES (1,1,'personal','completed','[]',:scope,'{}')"
            ),
            {"scope": json.dumps({"owner_user_id": 1})},
        )
        connection.execute(
            text(
                "INSERT INTO coach_hypotheses("
                "id,analysis_run_id,user_id,status,problem,evidence_json,caveats_json,recommended_focus,"
                "mission_readiness_json,target_metric_candidates_json,source_card_json) "
                "VALUES (1,1,1,'accepted','p','{}','[]','f','{}','[]','{}')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO coach_missions(id,hypothesis_id,user_id,status,title,focus,source_payload_json) "
                "VALUES (1,1,1,'active','t','f','{}')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO mission_criteria(id,mission_id,user_id,metric_name,role,direction,rule_json) "
                "VALUES (1,1,1,'adr','primary','increase','{}')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO mission_progress_evaluations(id,mission_id,user_id,status,result_json,caveats_json) "
                "VALUES (1,1,1,'improving','{}','[]')"
            )
        )
        batch = {
            "batch": {
                "batch_id": "blocked",
                "owner_user_id": 17,
                "status": "blocked",
                "stop_reason": "owner_steam_account_missing",
            }
        }
        connection.execute(
            text("INSERT INTO app_settings(key,value) VALUES ('owner_coach_sync_batch:blocked',:value)"),
            {"value": json.dumps(batch)},
        )
    return engine


def call(engine, **kwargs):
    return reconcile_owner_identity(
        engine,
        legacy_user_id=1,
        canonical_user_id=17,
        identity_evidence=EVIDENCE,
        **kwargs,
    )


def test_dry_run_inventory_is_complete_sanitized_and_non_mutating(reconciliation_engine):
    plan = call(reconciliation_engine)
    assert plan["identity"]["equivalence_proven"] is True
    assert {row["table"] for row in plan["inventory"]} >= {
        "steam_accounts", "import_jobs", "matches", "analysis_runs", "coach_hypotheses",
        "coach_missions", "mission_criteria", "mission_progress_evaluations",
    }
    assert plan["sanitized"] is True
    assert "owner@example.com" not in json.dumps(plan)
    assert "unchanged" not in json.dumps(plan)
    with reconciliation_engine.connect() as connection:
        assert connection.execute(text("SELECT user_id FROM steam_accounts WHERE id=1")).scalar_one() == 1


def test_equivalence_unproven_blocks(reconciliation_engine):
    with pytest.raises(OwnerReconciliationError, match="identity_equivalence_unproven"):
        reconcile_owner_identity(
            reconciliation_engine, legacy_user_id=1, canonical_user_id=17, identity_evidence=EVIDENCE[:2]
        )


def test_conflicting_steam_identity_blocks(reconciliation_engine):
    with reconciliation_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO steam_accounts(id,user_id,steam_id,sync_enabled) "
                "VALUES (2,17,'76561198000000002',0)"
            )
        )
    plan = call(reconciliation_engine)
    assert "conflicting_steam_identities" in plan["refusals"]


def test_conflicting_auth_credentials_block(reconciliation_engine):
    with reconciliation_engine.begin() as connection:
        connection.execute(text("UPDATE users SET email='legacy@example.com',password_hash='hash' WHERE id=1"))
    plan = call(reconciliation_engine)
    assert "conflicting_auth_credentials" in plan["refusals"]


def test_apply_reconciles_full_lineage_and_preserves_terminal_batch(reconciliation_engine):
    result = call(reconciliation_engine, apply=True, confirm_identity_merge=True)
    assert all(result["post_invariants"].values())
    with reconciliation_engine.connect() as connection:
        for table_name in (
            "steam_accounts", "import_jobs", "matches", "analysis_runs", "coach_hypotheses",
            "coach_missions", "mission_criteria", "mission_progress_evaluations",
        ):
            assert connection.execute(text(f"SELECT user_id FROM {table_name} WHERE id=1")).scalar_one() == 17
        scope = connection.execute(text("SELECT analysis_scope_json FROM analysis_runs WHERE id=1")).scalar_one()
        assert json.loads(scope)["owner_user_id"] == 17
        batch_value = connection.execute(
            text("SELECT value FROM app_settings WHERE key='owner_coach_sync_batch:blocked'")
        ).scalar_one()
        batch = json.loads(batch_value)
        assert batch["batch"]["status"] == "blocked"
        assert batch["batch"]["stop_reason"] == "owner_steam_account_missing"


def test_apply_requires_confirmation(reconciliation_engine):
    with pytest.raises(OwnerReconciliationError, match="apply_requires_confirm_identity_merge"):
        call(reconciliation_engine, apply=True)


def test_collision_detection_rejects_owner_lock(reconciliation_engine):
    with reconciliation_engine.begin() as connection:
        connection.execute(text("INSERT INTO app_settings(key,value) VALUES ('lock:owner_coach_sync:1','{}')"))
    plan = call(reconciliation_engine)
    assert "owner_sync_lock_present" in plan["refusals"]


def test_transaction_rolls_back_on_injected_failure(reconciliation_engine):
    with pytest.raises(RuntimeError, match="injected_owner_reconciliation_failure"):
        call(
            reconciliation_engine,
            apply=True,
            confirm_identity_merge=True,
            inject_failure_after="matches",
        )
    with reconciliation_engine.connect() as connection:
        assert connection.execute(text("SELECT user_id FROM steam_accounts WHERE id=1")).scalar_one() == 1
        assert connection.execute(text("SELECT user_id FROM matches WHERE id=1")).scalar_one() == 1


def test_repeated_apply_and_post_apply_dry_run_are_noops(reconciliation_engine):
    call(reconciliation_engine, apply=True, confirm_identity_merge=True)
    second = call(reconciliation_engine, apply=True, confirm_identity_merge=True)
    dry = call(reconciliation_engine)
    assert second["idempotent_noop"] is True
    assert dry["migration_summary"]["total_direct_rows"] == 0
    assert dry["migration_summary"]["total_json_rows"] == 0
