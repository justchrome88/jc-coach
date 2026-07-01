import json
from types import SimpleNamespace

import pytest

from app.services.ai_coach import (
    CodexCliHandoffProvider,
    LocalLLMProvider,
    ai_provider_health,
    build_ai_coach_payload,
    latest_ai_coach_report,
    list_ai_coach_reports,
    save_ai_coach_result,
    serialize_ai_coach_report,
)
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


def test_save_ai_coach_result_persists_ai_report(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    report = save_ai_coach_result(db, "# AI report\n\nFocus on survival.", source_ref="manual")
    latest = latest_ai_coach_report(db)
    serialized = serialize_ai_coach_report(report)

    assert report.report_type == "ai_coach"
    assert report.source_ref == "manual"
    assert latest is not None
    assert latest.id == report.id
    assert serialized["status"] == "saved"
    assert serialized["payload_hash"]
    assert serialized["payload_matches_count"] == 2


def test_ai_coach_report_history_is_newest_first(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    first = save_ai_coach_result(db, "First report", source_ref="manual-1")
    second = save_ai_coach_result(db, "Second report", source_ref="manual-2")

    reports = list_ai_coach_reports(db)

    assert [report.id for report in reports[:2]] == [second.id, first.id]


def test_save_ai_coach_result_rejects_empty_text(db):
    with pytest.raises(ValueError):
        save_ai_coach_result(db, "   ")


def test_local_llm_provider_calls_ollama(monkeypatch):
    settings = SimpleNamespace(
        local_llm_base_url="http://127.0.0.1:11434",
        local_llm_model="test-model",
        local_llm_timeout_seconds=5,
    )
    monkeypatch.setattr("app.services.ai_coach.get_settings", lambda: settings)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps({"response": "AI report"}).encode()

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:11434/api/generate"
        assert timeout == 5
        return FakeResponse()

    monkeypatch.setattr("app.services.ai_coach.urllib.request.urlopen", fake_urlopen)

    result = LocalLLMProvider().generate(
        {
            "summary": {"matches_count": 1},
            "detected_weaknesses": [],
            "map_stats": [],
            "period_comparison": {},
            "coach_focus": {"title": "test"},
        }
    )

    assert result == "AI report"


def test_ai_provider_health_for_handoff(monkeypatch):
    settings = SimpleNamespace(ai_provider="codex_cli_handoff")
    monkeypatch.setattr("app.services.ai_coach.get_settings", lambda: settings)

    health = ai_provider_health()

    assert health["provider"] == "codex_cli_handoff"
    assert health["status"] == "handoff"
