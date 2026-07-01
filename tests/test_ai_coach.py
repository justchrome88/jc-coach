from types import SimpleNamespace

from app.services.ai_coach import CodexCliHandoffProvider, build_ai_coach_payload
from app.services.importer import import_rows


def test_build_ai_coach_payload_uses_structured_match_data(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    payload = build_ai_coach_payload(db)

    assert payload["product"] == "CS2 Personal Coach"
    assert payload["summary"]["matches_count"] == 2
    assert payload["rules"]["do_not_invent_facts"] is True
    assert len(payload["recent_matches"]) == 2


def test_codex_handoff_provider_writes_prompt_and_payload(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        ai_handoff_dir=tmp_path,
        ai_codex_command="codex exec",
    )
    monkeypatch.setattr("app.services.ai_coach.get_settings", lambda: settings)

    result = CodexCliHandoffProvider().prepare(
        {
            "summary": {"matches_count": 1},
            "detected_weaknesses": [],
            "map_stats": [],
            "period_comparison": {},
            "coach_focus": {"title": "test"},
        }
    )

    assert result["status"] == "handoff_ready"
    assert result["provider"] == "codex_cli_handoff"
    assert "codex exec" in result["command"]
    assert list(tmp_path.glob("*/codex_prompt.md"))
    assert list(tmp_path.glob("*/coach_payload.json"))
