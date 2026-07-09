from app.services.coach_insights import (
    INSIGHT_CARD_SCHEMA_VERSION,
    no_data_insight_card,
    serialize_insight_cards,
    validate_insight_cards,
)


def _valid_card() -> dict:
    return {
        "problem": "Opening duel survival is the current evidence-backed focus.",
        "evidence": [
            {
                "metric_id": "entry_deaths",
                "value": 3,
                "metric_confidence": "medium",
                "description": "Entry deaths are elevated in the current sample.",
            }
        ],
        "confidence": "medium",
        "caveats": ["Opening duel detection depends on parser/source order."],
        "recommended_focus": "Play first 20 seconds slower and avoid isolated opening fights.",
    }


def test_insight_card_schema_accepts_required_fields_and_serializer_adds_version():
    card = _valid_card()

    assert validate_insight_cards([card]) == ()

    serialized = serialize_insight_cards([card])

    assert serialized == [
        {
            "schema_version": INSIGHT_CARD_SCHEMA_VERSION,
            **card,
        }
    ]


def test_insight_card_schema_rejects_missing_required_field():
    card = _valid_card()
    card.pop("recommended_focus")

    issues = validate_insight_cards([card])

    assert any(issue.code == "missing_insight_card_field" for issue in issues)
    assert any(issue.path == "$.insight_cards[0].recommended_focus" for issue in issues)


def test_no_evidence_insight_card_requires_low_confidence_and_caveat():
    card = {
        "problem": "No validated coach insight is available yet.",
        "evidence": [],
        "confidence": "medium",
        "caveats": [],
        "recommended_focus": "Use the current accepted recommendation until more evidence exists.",
    }

    issues = validate_insight_cards([card])
    codes = {issue.code for issue in issues}

    assert "insight_no_evidence_requires_low_confidence" in codes
    assert "insight_no_evidence_requires_caveat" in codes


def test_insight_card_caveats_must_be_non_empty_strings():
    card = _valid_card()
    card["caveats"] = [123]

    issues = validate_insight_cards([card])

    assert any(issue.code == "invalid_insight_caveat" for issue in issues)
    assert serialize_insight_cards([card]) == []


def test_no_data_insight_card_is_schema_validated_low_confidence_payload():
    card = no_data_insight_card("No supported evidence was available for this card.")

    assert validate_insight_cards([card]) == ()
    assert card["schema_version"] == INSIGHT_CARD_SCHEMA_VERSION
    assert card["confidence"] == "low"
    assert card["evidence"] == []
    assert card["caveats"] == ["No supported evidence was available for this card."]
