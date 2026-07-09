import hashlib
import json
from pathlib import Path

from app.db.models import DemoParseArtifact, Match
from app.services.artifact_integrity import (
    ARTIFACT_STATE_AVAILABLE,
    ARTIFACT_STATE_CHECKSUM_MISMATCH,
    ARTIFACT_STATE_MISSING,
    ARTIFACT_STATE_STALE,
    parser_artifact_integrity_report,
)
from app.services.demo_retention import (
    ARTIFACT_CATEGORY_RAW_DEMO,
    CONSISTENCY_DB_REFERENCES_FILE_CHANGED,
    CONSISTENCY_DB_REFERENCES_FILE_EXISTS,
    CONSISTENCY_DB_REFERENCES_FILE_MISSING,
    CONSISTENCY_FILE_WITHOUT_DB_REFERENCE,
    DEMO_RETENTION_POLICY_RETAIN_RAW,
    RETENTION_CLASS_RETAINED_RAW,
)
from app.services.demo_storage import (
    classify_demo_file_consistency,
    demo_storage_report,
    deterministic_demo_path,
    store_demo_file,
    write_demo_storage_manifest,
)


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


def test_storage_path_generation_and_duplicate_store(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    from app.config import get_settings

    get_settings.cache_clear()
    source = tmp_path / "source.dem"
    source.write_bytes(b"HL2DEMO deterministic")
    sha1 = hashlib.sha1(source.read_bytes()).hexdigest()

    try:
        first = store_demo_file(source, "Original Match.dem")
        second = store_demo_file(source, "Original Match.dem")
    finally:
        get_settings.cache_clear()

    assert Path(first["path"]) == deterministic_demo_path(sha1, upload_dir=upload_dir)
    assert first["storage_status"] == "stored"
    assert second["storage_status"] == "already_stored"
    assert first["path"] == second["path"]
    assert len(list(upload_dir.rglob("*.dem"))) == 1
    assert first["state"] == ARTIFACT_STATE_AVAILABLE
    assert first["integrity"]["path"] == first["path"]
    assert first["integrity"]["sha1"] == sha1
    assert first["integrity"]["size_bytes"] == len(b"HL2DEMO deterministic")
    assert first["integrity"]["rebuild_needed"] is False
    assert first["integrity"]["reparse_needed"] is False
    assert first["parser_handoff_path"] == first["path"]
    assert first["retention"]["category"] == ARTIFACT_CATEGORY_RAW_DEMO
    assert first["retention"]["retention_class"] == RETENTION_CLASS_RETAINED_RAW
    assert first["retention"]["delete_allowed"] is False
    assert first["retention"]["requires_explicit_backup_or_list_for_delete"] is True


def test_demo_storage_report_includes_nested_retained_files(db, monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    from app.config import get_settings

    get_settings.cache_clear()
    nested = upload_dir / "retained" / "ab" / "abcd.dem"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"HL2DEMO")
    db.add(Match(source="demo", external_match_id="nested", demo_file=str(nested)))
    db.commit()

    try:
        report = demo_storage_report(db)
    finally:
        get_settings.cache_clear()

    assert report["totals"]["files"] == 1
    assert report["totals"]["referenced_files"] == 1
    assert report["largest_files"][0]["relative_path"] == "retained/ab/abcd.dem"


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
    missing_item = next(item for item in result["items"] if item["status"] == CONSISTENCY_DB_REFERENCES_FILE_MISSING)
    assert missing_item["artifact_integrity"]["state"] == ARTIFACT_STATE_MISSING
    assert missing_item["rebuild_needed"] is True
    assert missing_item["reparse_needed"] is True
    assert missing_item["action"] == "restore_or_reacquire_artifact_then_reparse"


def test_file_db_consistency_classifier_detects_checksum_mismatch(db, tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    retained_path = upload_dir / "retained" / "aa" / "changed.dem"
    retained_path.parent.mkdir(parents=True)
    original = b"HL2DEMO original"
    retained_path.write_bytes(original)
    original_sha1 = hashlib.sha1(original).hexdigest()
    db.add(
        Match(
            source="demo",
            external_match_id="changed",
            demo_file=str(retained_path),
            raw_json=json.dumps({"storage": {"sha1": original_sha1, "size_bytes": len(original)}}),
        )
    )
    db.commit()
    retained_path.write_bytes(b"HL2DEMO changed artifact")

    result = classify_demo_file_consistency(db, upload_dir=upload_dir)

    assert result["counts"][CONSISTENCY_DB_REFERENCES_FILE_CHANGED] == 1
    item = result["items"][0]
    assert item["artifact_integrity"]["state"] == ARTIFACT_STATE_CHECKSUM_MISMATCH
    assert item["artifact_integrity"]["expected_sha1"] == original_sha1
    assert item["rebuild_needed"] is True
    assert item["reparse_needed"] is True
    assert item["action"] == "reparse_from_retained_raw_demo"


def test_parser_artifact_integrity_marks_derived_output_stale_when_source_missing(db, tmp_path):
    source = tmp_path / "retained.dem"
    source.write_bytes(b"HL2DEMO parser source")
    sha1 = hashlib.sha1(source.read_bytes()).hexdigest()
    match = Match(source="demo", external_match_id="parser-stale", demo_file=str(source))
    db.add(match)
    db.commit()
    db.refresh(match)
    db.add(
        DemoParseArtifact(
            match_id=match.id,
            parser_name="demoparser2",
            payload_version="2026-07-02.1",
            status="parsed",
            source_demo_file=str(source),
            demo_sha1=sha1,
            event_counts_json="{}",
            confidence_json="{}",
            data_gaps_json="{}",
            payload_json=json.dumps({"source_artifact": {"size_bytes": source.stat().st_size}}),
        )
    )
    db.commit()
    source.unlink()

    report = parser_artifact_integrity_report(db)

    assert report["counts"][ARTIFACT_STATE_STALE] == 1
    item = report["items"][0]
    assert item["state"] == ARTIFACT_STATE_STALE
    assert item["source_artifact"]["state"] == ARTIFACT_STATE_MISSING
    assert item["rebuild_needed"] is True
    assert item["reparse_needed"] is True
    assert item["action"] == "restore_or_reacquire_source_then_rebuild_parser_artifact"


def test_parser_artifact_integrity_marks_derived_output_stale_when_source_changes(db, tmp_path):
    source = tmp_path / "retained.dem"
    source.write_bytes(b"HL2DEMO parser source")
    sha1 = hashlib.sha1(source.read_bytes()).hexdigest()
    match = Match(source="demo", external_match_id="parser-changed", demo_file=str(source))
    db.add(match)
    db.commit()
    db.refresh(match)
    db.add(
        DemoParseArtifact(
            match_id=match.id,
            parser_name="demoparser2",
            payload_version="2026-07-02.1",
            status="parsed",
            source_demo_file=str(source),
            demo_sha1=sha1,
            event_counts_json="{}",
            confidence_json="{}",
            data_gaps_json="{}",
            payload_json=json.dumps({"source_artifact": {"size_bytes": source.stat().st_size}}),
        )
    )
    db.commit()
    source.write_bytes(b"HL2DEMO parser source changed")

    report = parser_artifact_integrity_report(db)

    assert report["counts"][ARTIFACT_STATE_STALE] == 1
    item = report["items"][0]
    assert item["source_artifact"]["state"] == ARTIFACT_STATE_CHECKSUM_MISMATCH
    assert item["rebuild_needed"] is True
    assert item["reparse_needed"] is True
    assert item["action"] == "rebuild_parser_artifact_from_current_source"
