import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.db.models import Match
from app.services.ai_coach import (
    AI_COACH_DOMAIN_CONTRACT_VERSION,
    AI_COACH_PAYLOAD_SCHEMA_VERSION,
    AI_COACH_PROMPT_VERSION,
    AI_COACH_SNAPSHOT_CONTRACT_VERSION,
    AI_COACH_SNAPSHOT_GENERATED_BY,
    CodexCliHandoffProvider,
    LocalLLMProvider,
    ai_provider_health,
    build_ai_coach_payload,
    build_ai_coach_prompt,
    latest_ai_coach_report,
    list_ai_coach_reports,
    save_ai_coach_result,
    serialize_ai_coach_report,
)
from app.services.importer import import_rows
from app.services.metric_truth import METRIC_REGISTRY_VERSION


def test_build_ai_coach_payload_uses_structured_match_data(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    payload = build_ai_coach_payload(db)

    assert payload["product"] == "CS2 Personal Coach"
    assert payload["summary"]["matches_count"] == 2
    assert payload["rules"]["do_not_invent_facts"] is True
    assert len(payload["recent_matches"]) == 2
    assert payload["metric_confidence"]["metrics"]["grenade_rating"]["level"] == "unavailable"
    assert payload["metric_confidence"]["metrics"]["traded_deaths"]["level"] == "unavailable"


def test_ai_coach_payload_includes_deterministic_contract_snapshot(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    first = build_ai_coach_payload(db)
    second = build_ai_coach_payload(db)

    expected = {
        "ai_coach_prompt_version": AI_COACH_PROMPT_VERSION,
        "ai_coach_payload_schema_version": AI_COACH_PAYLOAD_SCHEMA_VERSION,
        "metric_registry_version": METRIC_REGISTRY_VERSION,
        "snapshot_generated_by": AI_COACH_SNAPSHOT_GENERATED_BY,
        "snapshot_contract_version": AI_COACH_SNAPSHOT_CONTRACT_VERSION,
    }
    assert first["contract_snapshot"] == expected
    assert second["contract_snapshot"] == expected
    assert first["contract_snapshot"] == second["contract_snapshot"]
    assert first["metric_truth"]["metric_registry_version"] == METRIC_REGISTRY_VERSION


def test_ai_coach_payload_includes_deterministic_domain_constraints(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    first = build_ai_coach_payload(db)
    second = build_ai_coach_payload(db)

    assert first["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert first["domain_contract_version"] == second["domain_contract_version"]
    assert first["domain_constraints"] == second["domain_constraints"]
    assert first["claim_guardrails"] == second["claim_guardrails"]
    assert first["metric_confidence_policy"] == second["metric_confidence_policy"]
    assert first["playlist_mode_policy"] == second["playlist_mode_policy"]
    assert first["recommendation_policy"] == second["recommendation_policy"]
    assert first["public_readiness_policy"] == second["public_readiness_policy"]

    assert first["domain_constraints"]["accepted_active_hard_recommendation_id"] == 5
    assert first["recommendation_policy"]["current_accepted_active_hard_recommendation_id"] == 5
    assert first["recommendation_policy"]["legacy_recommendations_not_for_new_hard_evaluations"] == [1, 3, 4]
    assert first["domain_constraints"]["steam_import_max_demos_per_run"] == 1
    assert first["domain_constraints"]["v1_0_claim_allowed"] is False
    assert first["public_readiness_policy"]["public_readiness"] == "blocked"
    assert first["public_readiness_policy"]["friends_readiness"] == "blocked"
    assert first["public_readiness_policy"]["public_or_friends_claim_allowed"] is False


def test_ai_coach_prompt_carries_contract_snapshot_without_removing_caveats(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    payload = build_ai_coach_payload(db)
    prompt = build_ai_coach_prompt(payload)
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)

    assert AI_COACH_PROMPT_VERSION in prompt
    assert METRIC_REGISTRY_VERSION in prompt
    assert AI_COACH_DOMAIN_CONTRACT_VERSION in prompt
    assert "domain_constraints" in prompt
    assert "claim_guardrails" in prompt
    assert payload["metric_confidence_policy"]["weak_metrics_must_remain_caveated"] is True
    assert payload["metric_confidence_policy"]["missing_metric_confidence_blocks_hard_advice"] is True
    assert "crosshair_placement" in payload["metric_truth"]["suppressed_for_diagnosis"]
    assert "crosshair_placement" in payload["metric_truth"]["suppressed_for_recommendation"]
    assert payload["metric_confidence"]["metrics"]["crosshair_placement"]["level"] == "unavailable"
    assert "trade_kills" in payload["metric_truth"]["suppressed_for_recommendation"]
    assert payload["playlist_mode_policy"]["mode_status"] == "unknown_or_provenance_only"
    assert payload["playlist_mode_policy"]["source_labels_are_provenance_not_playlist"] is True
    for unsupported_mode in ("Premier", "Competitive", "Wingman", "Casual", "Deathmatch", "FACEIT"):
        assert unsupported_mode in payload["playlist_mode_policy"]["unsupported_exact_playlist_claims"]
        assert f'"accepted_playlist": "{unsupported_mode}"' not in payload_json
    assert '"v1_0_claim_allowed": true' not in payload_json
    assert '"public_or_friends_claim_allowed": true' not in payload_json


def test_ai_payload_uses_exact_recent_matches_and_reports_exclusions(db):
    db.add_all(
        [
            Match(
                source="demo",
                external_match_id="exact-ai",
                played_at=datetime(2026, 6, 1),
                result="win",
                raw_json=_date_truth_raw("exact_match_date_available", "steam_gc_match_time"),
            ),
            Match(
                source="demo",
                external_match_id="approx-ai",
                played_at=datetime(2026, 7, 1),
                result="loss",
                raw_json=_date_truth_raw("approximate_match_date", "file_modified_fallback"),
            ),
        ]
    )
    db.commit()

    payload = build_ai_coach_payload(db)

    assert [match["id"] for match in payload["recent_matches"]] == [1]
    assert payload["metric_confidence"]["date_window"]["approximate_date_matches"] == 1
    assert payload["rules"]["use_exact_date_windows_for_trends"] is True


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
    assert result["ai_coach_prompt_version"] == AI_COACH_PROMPT_VERSION
    assert result["ai_coach_payload_schema_version"] == AI_COACH_PAYLOAD_SCHEMA_VERSION
    assert result["metric_registry_version"] == METRIC_REGISTRY_VERSION
    assert result["snapshot_generated_by"] == AI_COACH_SNAPSHOT_GENERATED_BY
    assert result["snapshot_contract_version"] == AI_COACH_SNAPSHOT_CONTRACT_VERSION
    assert result["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert result["domain_constraints"]["accepted_active_hard_recommendation_id"] == 5
    assert result["metric_confidence_policy"]["weak_metrics_must_remain_caveated"] is True
    assert result["playlist_mode_policy"]["mode_status"] == "unknown_or_provenance_only"
    assert result["public_readiness_policy"]["public_readiness"] == "blocked"
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
    assert serialized["metadata"]["ai_coach_prompt_version"] == AI_COACH_PROMPT_VERSION
    assert serialized["metadata"]["ai_coach_payload_schema_version"] == AI_COACH_PAYLOAD_SCHEMA_VERSION
    assert serialized["metadata"]["metric_registry_version"] == METRIC_REGISTRY_VERSION
    assert serialized["metadata"]["snapshot_generated_by"] == AI_COACH_SNAPSHOT_GENERATED_BY
    assert serialized["metadata"]["snapshot_contract_version"] == AI_COACH_SNAPSHOT_CONTRACT_VERSION
    assert serialized["metadata"]["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert serialized["metadata"]["domain_contract"]["domain_contract_version"] == AI_COACH_DOMAIN_CONTRACT_VERSION
    assert serialized["metadata"]["domain_constraints"]["accepted_active_hard_recommendation_id"] == 5
    assert serialized["metadata"]["claim_guardrails"]["do_not_invent_parser_data"] is True
    assert serialized["metadata"]["metric_confidence_policy"]["weak_metrics_must_remain_caveated"] is True
    assert serialized["metadata"]["playlist_mode_policy"]["mode_status"] == "unknown_or_provenance_only"
    assert serialized["metadata"]["public_readiness_policy"]["v1_0_claim_allowed"] is False
    assert serialized["metadata"]["public_readiness_policy"]["friends_readiness"] == "blocked"
    assert (
        serialized["metadata"]["contract_snapshot"]
        == serialized["metadata"]["payload_snapshot"]["contract_snapshot"]
    )
    assert (
        serialized["metadata"]["domain_contract"]
        == {
            "domain_contract_version": serialized["metadata"]["payload_snapshot"]["domain_contract_version"],
            "domain_constraints": serialized["metadata"]["payload_snapshot"]["domain_constraints"],
            "claim_guardrails": serialized["metadata"]["payload_snapshot"]["claim_guardrails"],
            "metric_confidence_policy": serialized["metadata"]["payload_snapshot"]["metric_confidence_policy"],
            "playlist_mode_policy": serialized["metadata"]["payload_snapshot"]["playlist_mode_policy"],
            "recommendation_policy": serialized["metadata"]["payload_snapshot"]["recommendation_policy"],
            "public_readiness_policy": serialized["metadata"]["payload_snapshot"]["public_readiness_policy"],
        }
    )


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


def _date_truth_raw(status: str, source: str) -> str:
    return json.dumps(
        {
            "match_date_status": status,
            "match_date_source": source,
            "played_at_source": source,
        }
    )
