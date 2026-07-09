import json

from app.api.routes import create_import_job_endpoint
from app.db.models import ImportJob
from app.services.import_jobs import (
    IMPORT_JOB_COMPLETED,
    IMPORT_JOB_FAILED,
    IMPORT_JOB_REQUESTED,
    IMPORT_JOB_SKIPPED_DUPLICATE,
    complete_import_job,
    create_import_request,
    fail_import_job,
    queue_import_job,
    start_import_job,
)


def test_import_job_creation_persists_structured_request(db):
    job = create_import_request(
        db,
        provider="steam",
        job_type="demo_acquisition",
        payload={"share_code": "CSGO-abcde-abcde-abcde-abcde-abcde", "source": "test"},
        user_id=7,
    )

    persisted = db.get(ImportJob, job.id)
    assert persisted is not None
    assert persisted.status == IMPORT_JOB_REQUESTED
    assert persisted.user_id == 7
    assert persisted.logical_target_key == "steam:demo_acquisition:CSGO-abcde-abcde-abcde-abcde-abcde"
    assert json.loads(persisted.requested_payload_json)["source"] == "test"


def test_import_job_duplicate_request_is_persisted_as_skipped_duplicate(db):
    first = create_import_request(
        db,
        provider="steam",
        job_type="demo_acquisition",
        payload={"share_code": "CSGO-abcde-abcde-abcde-abcde-abcde"},
    )
    duplicate = create_import_request(
        db,
        provider="steam",
        job_type="demo_acquisition",
        payload={"share_code": "CSGO-abcde-abcde-abcde-abcde-abcde"},
    )

    assert first.status == IMPORT_JOB_REQUESTED
    assert duplicate.status == IMPORT_JOB_SKIPPED_DUPLICATE
    assert duplicate.finished_at is not None
    assert json.loads(duplicate.result_json)["duplicate_of_job_id"] == first.id
    active_jobs = db.query(ImportJob).filter(ImportJob.status.in_([IMPORT_JOB_REQUESTED])).all()
    assert [job.id for job in active_jobs] == [first.id]


def test_import_job_status_transition_and_result_persistence(db):
    job = create_import_request(db, provider="steam", job_type="demo_acquisition", payload={"demo_sha1": "abc"})

    queue_import_job(db, job)
    start_import_job(db, job)
    complete_import_job(db, job, result={"demo": {"sha1": "abc"}, "next_step": "parse_demo"})

    db.refresh(job)
    assert job.status == IMPORT_JOB_COMPLETED
    assert job.started_at is not None
    assert job.finished_at is not None
    assert json.loads(job.result_json)["next_step"] == "parse_demo"


def test_import_job_failure_contract_is_structured(db):
    job = create_import_request(db, provider="steam", job_type="demo_acquisition", payload={"demo_file": "demo.dem"})

    queue_import_job(db, job)
    start_import_job(db, job)
    fail_import_job(db, job, "download failed", result={"stage": "download"})

    db.refresh(job)
    result = json.loads(job.result_json)
    assert job.status == IMPORT_JOB_FAILED
    assert job.error_message == "download failed"
    assert result["stage"] == "download"
    assert result["error"]["message"] == "download failed"


def test_import_job_rejects_invalid_transition(db):
    job = create_import_request(db, provider="steam", job_type="demo_acquisition", payload={"demo_sha1": "abc"})

    try:
        complete_import_job(db, job, result={})
    except ValueError as exc:
        assert "Invalid import job transition" in str(exc)
    else:
        raise AssertionError("requested import jobs must not complete without queue/start")


def test_import_job_api_seam_serializes_created_request(db):
    response = create_import_job_endpoint(
        db,
        {
            "provider": "steam",
            "job_type": "demo_acquisition",
            "payload": {"share_code": "CSGO-abcde-abcde-abcde-abcde-abcde"},
            "user_id": 11,
        },
    )

    assert response["status"] == IMPORT_JOB_REQUESTED
    assert response["user_id"] == 11
    assert response["requested_payload"]["share_code"] == "CSGO-abcde-abcde-abcde-abcde-abcde"
    assert response["result"] == {}
