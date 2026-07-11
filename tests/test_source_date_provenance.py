from __future__ import annotations

from app.services.parsing.evidence import source_date_provenance


def test_available_steam_source_date_provenance_is_explicit():
    result = source_date_provenance(
        {"played_at": "2026-07-11T14:39:30", "played_at_source": "steam_gc_match_time"}
    )

    assert result == {
        "status": "available",
        "source_system": "steam_history",
        "source_field": "played_at",
        "trust_class": "source_provided",
        "timezone_semantics": "UTC instant normalized from the persisted Steam GC match time",
    }


def test_file_modified_fallback_provenance_is_available_but_approximate():
    result = source_date_provenance(
        {"played_at": "2026-07-11T14:39:30", "played_at_source": "file_modified_fallback"}
    )

    assert result["status"] == "available"
    assert result["source_system"] == "demo_storage"
    assert result["trust_class"] == "approximate_fallback"


def test_unavailable_provenance_preserves_date_without_fabricating_source():
    result = source_date_provenance({"played_at": "2026-07-11T14:39:30"})

    assert result == {
        "status": "unavailable",
        "reason_code": "source_marker_not_persisted",
        "date_value_preserved": True,
    }
    assert result
    assert "source_system" not in result


def test_explicit_unavailable_provenance_is_never_empty():
    result = source_date_provenance({"played_at_source": "unavailable"})

    assert result["status"] == "unavailable"
    assert result["reason_code"] == "source_marker_unavailable"
    assert result != {}
