from app.services.shared.demo_retention import (
    ARTIFACT_CATEGORY_COACH_OUTPUT,
    ARTIFACT_CATEGORY_METRIC_SNAPSHOT,
    ARTIFACT_CATEGORY_NORMALIZED_EVENT_STORE,
    ARTIFACT_CATEGORY_PARSER_ARTIFACT,
    ARTIFACT_CATEGORY_RAW_DEMO,
    ARTIFACT_CATEGORY_TEMPORARY_FILE,
    RETENTION_CLASS_DERIVED_REBUILDABLE,
    RETENTION_CLASS_FINAL_OUTPUT,
    RETENTION_CLASS_RETAINED_RAW,
    artifact_retention_metadata,
    cleanup_temporary_artifacts,
    is_retained_raw_artifact,
    is_temporary_artifact,
)


def test_artifact_retention_classification_covers_new_artifact_categories():
    assert artifact_retention_metadata(ARTIFACT_CATEGORY_RAW_DEMO)["retention_class"] == RETENTION_CLASS_RETAINED_RAW
    assert (
        artifact_retention_metadata(ARTIFACT_CATEGORY_PARSER_ARTIFACT)["retention_class"]
        == RETENTION_CLASS_DERIVED_REBUILDABLE
    )
    assert (
        artifact_retention_metadata(ARTIFACT_CATEGORY_NORMALIZED_EVENT_STORE)["retention_class"]
        == RETENTION_CLASS_DERIVED_REBUILDABLE
    )
    assert (
        artifact_retention_metadata(ARTIFACT_CATEGORY_METRIC_SNAPSHOT)["retention_class"]
        == RETENTION_CLASS_DERIVED_REBUILDABLE
    )
    assert (
        artifact_retention_metadata(ARTIFACT_CATEGORY_COACH_OUTPUT)["retention_class"]
        == RETENTION_CLASS_FINAL_OUTPUT
    )


def test_safe_cleanup_deletes_only_task_owned_temporary_files(tmp_path):
    retained_raw = tmp_path / "retained.dem"
    task_temp = tmp_path / "task.tmp"
    caller_temp = tmp_path / "caller.tmp"
    retained_raw.write_bytes(b"HL2DEMO retained")
    task_temp.write_text("delete me", encoding="utf-8")
    caller_temp.write_text("keep me", encoding="utf-8")

    result = cleanup_temporary_artifacts(
        [
            {"path": str(retained_raw), "retention": artifact_retention_metadata(ARTIFACT_CATEGORY_RAW_DEMO)},
            {
                "path": str(task_temp),
                "retention": artifact_retention_metadata(ARTIFACT_CATEGORY_TEMPORARY_FILE, cleanup_owner="task"),
            },
            {
                "path": str(caller_temp),
                "retention": artifact_retention_metadata(ARTIFACT_CATEGORY_TEMPORARY_FILE, cleanup_owner="caller"),
            },
        ]
    )

    assert result["deleted"] == [str(task_temp)]
    assert retained_raw.is_file()
    assert not task_temp.exists()
    assert caller_temp.is_file()
    assert is_retained_raw_artifact({"retention": artifact_retention_metadata(ARTIFACT_CATEGORY_RAW_DEMO)})
    assert is_temporary_artifact({"retention": artifact_retention_metadata(ARTIFACT_CATEGORY_TEMPORARY_FILE)})
