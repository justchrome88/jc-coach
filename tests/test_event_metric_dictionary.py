import json
from pathlib import Path

from app.services.parsing.event_dictionary import (
    EVENT_METRIC_DICTIONARY,
    NORMALIZED_EVENT_SCHEMA,
    V0_10_REQUIRED_EVENT_CATEGORIES,
    event_metric_dictionary_payload,
    event_types,
    parser_source_event_names,
)
from app.services.shared.metric_policy import metric_definition, usage_decision

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "parser"


def test_v010_event_dictionary_covers_required_categories():
    available_categories = {
        definition.category
        for definition in EVENT_METRIC_DICTIONARY.values()
        if definition.support in {"supported", "weak"}
    }

    assert set(V0_10_REQUIRED_EVENT_CATEGORIES).issubset(available_categories)
    assert {"event_type", "category", "source_event", "confidence", "payload"}.issubset(NORMALIZED_EVENT_SCHEMA)


def test_supported_and_weak_events_have_registered_metric_consumers():
    for definition in EVENT_METRIC_DICTIONARY.values():
        if definition.support == "unsupported":
            continue

        assert definition.metric_consumers, definition.event_type
        assert definition.parser_source_events, definition.event_type
        for metric_id in definition.metric_consumers:
            assert metric_definition(metric_id).metric_id != "unknown", (definition.event_type, metric_id)


def test_weak_and_unsupported_events_carry_caveats_not_fake_precision():
    weak_events = [definition for definition in EVENT_METRIC_DICTIONARY.values() if definition.support == "weak"]
    unsupported_events = event_types(support="unsupported")

    assert weak_events
    assert unsupported_events

    for definition in weak_events:
        assert definition.caveats, definition.event_type
        assert any(
            usage_decision(metric_id, "recommendation") != "allowed" for metric_id in definition.metric_consumers
        ), definition.event_type

    for event_type in unsupported_events:
        definition = EVENT_METRIC_DICTIONARY[event_type]
        assert definition.caveats, event_type
        assert all(usage_decision(metric_id, "ai") == "suppressed" for metric_id in definition.metric_consumers)


def test_parser_evidence_fixture_event_counts_are_declared_parser_sources():
    evidence = json.loads((FIXTURE_DIR / "parser_evidence_accepted_c2.json").read_text())

    assert set(evidence["event_counts"]).issubset(parser_source_event_names())


def test_event_metric_dictionary_payload_is_serializable_and_explicit():
    payload = event_metric_dictionary_payload()

    assert payload["version"] == "event-metric-dictionary-v0.10"
    assert {event["support"] for event in payload["events"]} == {"supported", "weak", "unsupported"}
    assert json.loads(json.dumps(payload)) == payload
