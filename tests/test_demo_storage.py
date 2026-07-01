import json
from pathlib import Path

from app.db.models import Match
from app.services.demo_storage import demo_storage_report, write_demo_storage_manifest


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
    assert report["totals"]["files"] == 2
    assert report["totals"]["referenced_files"] == 1
    assert report["totals"]["referenced_match_rows"] == 1
    assert report["totals"]["unreferenced_files"] == 1
    assert report["totals"]["future_deletion_candidates"] == 1
    assert report["totals"]["future_deletion_candidate_files"] == 1
    assert report["unreferenced_files"][0]["name"] == unreferenced_path.name


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
