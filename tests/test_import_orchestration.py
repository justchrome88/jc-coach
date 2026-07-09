import json
from pathlib import Path

from app.api.routes import create_import_job_endpoint, import_contract_endpoint, import_job_endpoint
from app.db.models import Match
from app.services.import_jobs import (
    IMPORT_JOB_COMPLETED,
    IMPORT_JOB_FAILED,
    IMPORT_JOB_SKIPPED_DUPLICATE,
    create_import_request,
)
from app.services.import_orchestration import (
    CANONICAL_IMPORT_JOB_TYPE,
    STORAGE_ALREADY_AVAILABLE,
    STORAGE_DUPLICATE,
    STORAGE_MISSING_FILE,
    STORAGE_STORED,
    import_block_handoff_contract,
    run_demo_import_orchestration,
)
from app.services.parser_artifact_reader import read_normalized_events
from app.services.steam_demo_acquisition import (
    DEMO_ALREADY_AVAILABLE,
    DEMO_AUTH_MISSING,
    DEMO_DOWNLOAD_QUEUED_OR_READY,
)

SHARE_CODE = "CSGO-bS48b-h4SZr-OM6Pi-ZAr9N-2aUeL"
PARSER_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "parser" / "parser_artifact_c02.json"


def test_deterministic_import_orchestration_stores_parser_handoff(db, monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    source = tmp_path / "fixture.dem"
    source.write_bytes(b"HL2DEMO deterministic import orchestration")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        job = run_demo_import_orchestration(
            db,
            payload={"share_code": SHARE_CODE, "fixture_demo_path": str(source)},
            user_id=11,
        )
    finally:
        get_settings.cache_clear()

    result = json.loads(job.result_json)
    match = db.query(Match).filter(Match.external_match_id == SHARE_CODE).one()
    assert job.status == IMPORT_JOB_COMPLETED
    assert result["acquisition"]["outcome"] == DEMO_DOWNLOAD_QUEUED_OR_READY
    assert result["storage"]["outcome"] == STORAGE_STORED
    assert Path(result["storage"]["artifact"]["path"]).is_file()
    assert result["parser_handoff"]["path"] == result["storage"]["artifact"]["parser_handoff_path"]
    assert result["parser_handoff"]["field"] == "parser_handoff_path"
    assert result["parser_handoff"]["match_field"] == "Match.demo_file"
    assert result["parser_handoff"]["parser_artifact_field"] == "DemoParseArtifact.source_demo_file"
    assert match.demo_file == result["parser_handoff"]["path"]
    assert match.user_id == 11
    assert match.import_job_id == job.id
    assert json.loads(match.raw_json)["parser_handoff"]["field"] == "Match.demo_file"


def test_import_orchestration_denies_cross_owner_share_code_reuse(db, monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    first_source = tmp_path / "owner-one.dem"
    second_source = tmp_path / "owner-two.dem"
    first_source.write_bytes(b"HL2DEMO owner one")
    second_source.write_bytes(b"HL2DEMO owner two")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        first = run_demo_import_orchestration(
            db,
            payload={"share_code": SHARE_CODE, "fixture_demo_path": str(first_source)},
            user_id=11,
        )
        second = run_demo_import_orchestration(
            db,
            payload={"share_code": SHARE_CODE, "fixture_demo_path": str(second_source)},
            user_id=22,
        )
    finally:
        get_settings.cache_clear()

    result = json.loads(second.result_json)
    assert first.status == IMPORT_JOB_COMPLETED
    assert second.status == IMPORT_JOB_FAILED
    assert "different user" in result["error"]["message"]
    assert db.query(Match).filter(Match.external_match_id == SHARE_CODE).one().user_id == 11


def test_imported_parser_handoff_path_feeds_normalized_event_reader(db, monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    source = tmp_path / "fixture.dem"
    source.write_bytes(b"HL2DEMO parser acceptance imported artifact")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        job = run_demo_import_orchestration(
            db,
            payload={"share_code": SHARE_CODE, "fixture_demo_path": str(source)},
            user_id=11,
        )
    finally:
        get_settings.cache_clear()

    result = json.loads(job.result_json)
    parser_handoff_path = result["parser_handoff"]["path"]
    assert job.status == IMPORT_JOB_COMPLETED
    assert Path(parser_handoff_path).is_file()

    artifact = json.loads(PARSER_FIXTURE_PATH.read_text())
    artifact["source_demo_file"] = parser_handoff_path
    artifact["payload"]["file"] = parser_handoff_path
    artifact["payload"]["parser_handoff"] = {"kind": "raw_demo_file", "path": parser_handoff_path}
    parser_artifact_path = tmp_path / "parser-artifact-for-imported-demo.json"
    parser_artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    events = read_normalized_events(parser_handoff_path, parser_artifact_path=parser_artifact_path)

    assert events
    assert {event["source"]["source_demo_file"] for event in events} == {parser_handoff_path}
    assert {"round_summary", "player_kill", "damage", "round_survival"}.issubset(
        {event["event_type"] for event in events}
    )
    assert all(event["schema_version"] == "normalized-parser-events-v1" for event in events)


def test_import_orchestration_auth_missing_fails_with_actionable_result(db, monkeypatch):
    monkeypatch.setenv("STEAM_BOT_USERNAME", "")
    monkeypatch.setenv("STEAM_BOT_PASSWORD", "")
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        job = run_demo_import_orchestration(db, payload={"share_code": SHARE_CODE})
    finally:
        get_settings.cache_clear()

    result = json.loads(job.result_json)
    assert job.status == IMPORT_JOB_FAILED
    assert result["acquisition"]["outcome"] == DEMO_AUTH_MISSING
    assert result["storage"] is None
    assert "fixture demo path" in result["error"]["message"]
    assert "secret" not in json.dumps(result).lower()


def test_import_orchestration_reuses_already_available_artifact(db, tmp_path):
    existing = tmp_path / "existing.dem"
    existing.write_bytes(b"HL2DEMO existing retained")
    match = Match(
        source="steam_history",
        external_match_id=SHARE_CODE,
        demo_file=str(existing),
        raw_json=json.dumps({"share_code": SHARE_CODE, "status": "demo_imported"}),
    )
    db.add(match)
    db.commit()

    job = run_demo_import_orchestration(db, payload={"share_code": SHARE_CODE})

    result = json.loads(job.result_json)
    assert job.status == IMPORT_JOB_COMPLETED
    assert result["acquisition"]["outcome"] == DEMO_ALREADY_AVAILABLE
    assert result["storage"]["outcome"] == STORAGE_ALREADY_AVAILABLE
    assert result["parser_handoff"]["path"] == str(existing.resolve())


def test_import_orchestration_downloads_reference_for_storage(db, monkeypatch, tmp_path):
    monkeypatch.setenv("STEAM_BOT_REFRESH_TOKEN", "test-refresh-token")
    upload_dir = tmp_path / "uploads"
    source = tmp_path / "downloaded.dem"
    source.write_bytes(b"HL2DEMO downloaded orchestration")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    match = Match(
        source="steam_history",
        external_match_id=SHARE_CODE,
        raw_json=json.dumps({"share_code": SHARE_CODE, "status": "demo_download_pending"}),
    )
    db.add(match)
    db.commit()

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

    def fake_downloader(url, share_code):
        assert url == "https://replay.example.test/demo.dem.bz2"
        assert share_code == SHARE_CODE
        return source

    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr("app.services.steam_demo_acquisition._fetch_demo_urls", fake_fetcher)
    monkeypatch.setattr("app.services.steam_demo_acquisition._download_demo_file", fake_downloader)
    try:
        job = run_demo_import_orchestration(db, payload={"share_code": SHARE_CODE})
    finally:
        get_settings.cache_clear()

    result = json.loads(job.result_json)
    db.refresh(match)
    assert job.status == IMPORT_JOB_COMPLETED
    assert result["acquisition"]["outcome"] == DEMO_DOWNLOAD_QUEUED_OR_READY
    assert result["acquisition"]["result"]["demo_reference"]["downloaded"] is True
    assert result["storage"]["outcome"] == STORAGE_STORED
    assert Path(result["parser_handoff"]["path"]).is_file()
    assert match.demo_file == result["parser_handoff"]["path"]


def test_import_orchestration_duplicate_storage_reuses_retained_path(db, monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    source = tmp_path / "fixture.dem"
    source.write_bytes(b"HL2DEMO duplicate storage")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        first = run_demo_import_orchestration(db, payload={"fixture_demo_path": str(source)})
        second = run_demo_import_orchestration(db, payload={"fixture_demo_path": str(source)})
    finally:
        get_settings.cache_clear()

    first_result = json.loads(first.result_json)
    second_result = json.loads(second.result_json)
    assert first.status == IMPORT_JOB_COMPLETED
    assert first_result["storage"]["outcome"] == STORAGE_STORED
    assert second.status == IMPORT_JOB_COMPLETED
    assert second_result["storage"]["outcome"] == STORAGE_DUPLICATE
    assert second_result["parser_handoff"]["path"] == first_result["parser_handoff"]["path"]


def test_import_orchestration_active_duplicate_is_skipped(db, tmp_path):
    source = tmp_path / "fixture.dem"
    source.write_bytes(b"HL2DEMO active duplicate")
    active = create_import_request(
        db,
        provider="steam",
        job_type=CANONICAL_IMPORT_JOB_TYPE,
        payload={"share_code": SHARE_CODE, "fixture_demo_path": str(source)},
    )

    duplicate = run_demo_import_orchestration(db, payload={"share_code": SHARE_CODE, "fixture_demo_path": str(source)})

    result = json.loads(duplicate.result_json)
    assert active.id == result["duplicate_of_job_id"]
    assert duplicate.status == IMPORT_JOB_SKIPPED_DUPLICATE


def test_import_orchestration_storage_missing_file_is_actionable(db, tmp_path):
    missing = tmp_path / "missing.dem"

    job = run_demo_import_orchestration(db, payload={"fixture_demo_path": str(missing)})

    result = json.loads(job.result_json)
    assert job.status == IMPORT_JOB_FAILED
    assert result["acquisition"]["outcome"] == DEMO_DOWNLOAD_QUEUED_OR_READY
    assert result["storage"]["outcome"] == STORAGE_MISSING_FILE
    assert "was not found" in result["error"]["message"]


def test_import_jobs_api_starts_and_inspects_canonical_orchestration(db, monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    source = tmp_path / "api-fixture.dem"
    source.write_bytes(b"HL2DEMO api deterministic")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        created = create_import_job_endpoint(
            db,
            {
                "provider": "steam",
                "job_type": CANONICAL_IMPORT_JOB_TYPE,
                "payload": {"share_code": SHARE_CODE, "fixture_demo_path": str(source)},
            },
        )
        inspected = import_job_endpoint(db, created["id"])
    finally:
        get_settings.cache_clear()

    assert created["status"] == IMPORT_JOB_COMPLETED
    assert inspected["id"] == created["id"]
    assert inspected["logical_target_key"] == f"steam:{CANONICAL_IMPORT_JOB_TYPE}:{SHARE_CODE}"
    assert inspected["result"]["acquisition"]["outcome"] == DEMO_DOWNLOAD_QUEUED_OR_READY
    assert inspected["result"]["storage"]["outcome"] == STORAGE_STORED
    assert Path(inspected["result"]["parser_handoff"]["path"]).is_file()


def test_import_block_contract_documents_canonical_path_and_legacy_classifications():
    contract = import_contract_endpoint()
    service_contract = import_block_handoff_contract()

    assert contract == service_contract
    assert contract["canonical_import_path"] == {
        "route": "POST /api/import/jobs",
        "job_type": CANONICAL_IMPORT_JOB_TYPE,
        "provider": "steam",
        "description": "Acquire a demo source, retain the raw .dem artifact, and persist parser handoff metadata.",
    }
    assert contract["inspection_routes"] == ["GET /api/import/jobs/{job_id}", "GET /api/import/jobs"]
    assert contract["parser_handoff_fields"] == {
        "result_path": "result_json.parser_handoff.path",
        "storage_artifact_path": "storage.artifact.parser_handoff_path",
        "match_field": "Match.demo_file",
        "parser_artifact_field": "DemoParseArtifact.source_demo_file",
    }
    classifications = {item["classification"] for item in contract["legacy_import_paths"]}
    assert {"tolerated", "deprecated", "blocker"} <= classifications
    assert {
        item["route"]: item["classification"] for item in contract["legacy_import_paths"]
    }["POST /api/steam/import/all"] == "blocker"
