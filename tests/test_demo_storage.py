import json
from pathlib import Path

from app.db.models import Match
from app.services.demo_retention import (
    CONSISTENCY_DB_REFERENCES_FILE_EXISTS,
    CONSISTENCY_DB_REFERENCES_FILE_MISSING,
    CONSISTENCY_FILE_WITHOUT_DB_REFERENCE,
    DEMO_RETENTION_POLICY_RETAIN_RAW,
)
from app.services.demo_storage import classify_demo_file_consistency, demo_storage_report, write_demo_storage_manifest


def test_demo_storage_report_classifies_files(db, monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    reports_dir = tmp_path / "reports"
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("REPORTS_DIR", str(reports_dir))
    from app.config import get_settings

    get_settings.cache_clear()
    upload_dir.mkdir()
    referenced_path = upload_dir / "referenced.dem"
    unreferenced_path = upload_dir / "unreferenced.dem"
    referenced_path.write_bytes(b"HL2DEMO")
    unreferenced_path.write_bytes(b"HL2DEMO")
    match = Match(
        source="demo",
        external_match_id="demo-1",
        demo_file=str(referenced_path),
        raw_json=json.dumps({"status": "parsed", "match": {"map_name": "de_mirage"}}),
    )
    db.add(match)
    db.commit()

    try:
        report = demo_storage_report(db)
    finally:
        get_settings.cache_clear()

    assert report["policy"]["raw_delete_after_parse_enabled"] is False
    assert report["policy"]["demo_retention_policy"] == DEMO_RETENTION_POLICY_RETAIN_RAW
    assert report["totals"]["files"] == 2
    assert report["totals"]["referenced_files"] == 1
    assert report["totals"]["referenced_match_rows"] == 1
    assert report["totals"]["unreferenced_files"] == 1
    assert report["totals"]["future_deletion_candidates"] == 1
    assert report["totals"]["future_deletion_candidate_files"] == 1
    assert report["unreferenced_files"][0]["name"] == unreferenced_path.name
    assert report["file_db_consistency"]["counts"][CONSISTENCY_DB_REFERENCES_FILE_EXISTS] == 1
    assert report["file_db_consistency"]["counts"][CONSISTENCY_FILE_WITHOUT_DB_REFERENCE] == 1


def test_write_demo_storage_manifest(db, monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        report = write_demo_storage_manifest(db)
    finally:
        get_settings.cache_clear()

    manifest_path = Path(report["manifest_path"])
    assert manifest_path.is_file()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["totals"]["files"] == 0


def test_file_db_consistency_classifier_detects_existing_missing_and_unreferenced(db, tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    existing_path = upload_dir / "existing.dem"
    missing_path = upload_dir / "missing.dem"
    unreferenced_path = upload_dir / "unreferenced.dem"
    existing_path.write_bytes(b"HL2DEMO")
    unreferenced_path.write_bytes(b"HL2DEMO")
    db.add_all(
        [
            Match(source="demo", external_match_id="existing", demo_file=str(existing_path)),
            Match(source="demo", external_match_id="missing", demo_file=str(missing_path)),
        ]
    )
    db.commit()

    result = classify_demo_file_consistency(db, upload_dir=upload_dir)

    assert result["counts"][CONSISTENCY_DB_REFERENCES_FILE_EXISTS] == 1
    assert result["counts"][CONSISTENCY_DB_REFERENCES_FILE_MISSING] == 1
    assert result["counts"][CONSISTENCY_FILE_WITHOUT_DB_REFERENCE] == 1
