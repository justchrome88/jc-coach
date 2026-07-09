from app.services.coach_insights import (
    INSIGHT_CARD_SCHEMA_VERSION,
    MEDIUM_CONFIDENCE_CAVEAT,
    bad_fight_trade_insight_from_snapshot,
    coach_insights_from_snapshots,
    no_data_insight_card,
    serialize_insight_cards,
    survival_opening_death_insight_from_snapshot,
    survival_opening_death_insights_from_snapshots,
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


def test_survival_opening_death_insight_uses_exact_metric_snapshot_evidence():
    card = survival_opening_death_insight_from_snapshot(
        _snapshot(
            metrics={
                "rounds": 10,
                "opening_deaths": 3,
                "opening_death_rate": 0.3,
                "survived_rounds": 5,
                "survival_rate": 0.5,
            },
            confidence={
                "opening_death_rate": {"level": "medium"},
                "survival_rate": {"level": "high"},
            },
            caveats=["Parser source order can make opening duel evidence approximate."],
        )
    )

    assert card is not None
    assert validate_insight_cards([card]) == ()
    assert card["problem"] == (
        "Frequent opening deaths are the strongest evidence-backed survival problem in this match snapshot."
    )
    assert card["confidence"] == "medium"
    assert card["evidence"] == [
        {
            "metric_id": "opening_death_rate",
            "value": 0.3,
            "threshold": 0.22,
            "metric_confidence": "medium",
            "sample_count": 10,
            "match_ids": [42],
            "source": "core_combat_metrics",
            "description": "Opening deaths are 3 over 10 rounds (0.300), meeting the 0.220 insight threshold.",
        },
        {
            "metric_id": "survival_rate",
            "value": 0.5,
            "threshold": 0.55,
            "metric_confidence": "high",
            "sample_count": 10,
            "match_ids": [42],
            "source": "core_combat_metrics",
            "description": (
                "Survival rate is 0.500: 5 survived rounds and 5 death rounds over 10 rounds, "
                "at or below the 0.550 insight threshold."
            ),
        },
    ]
    assert MEDIUM_CONFIDENCE_CAVEAT in card["caveats"]
    assert "Opening death evidence depends on parser opening duel event order." in card["caveats"]
    assert "Parser source order can make opening duel evidence approximate." in card["caveats"]


def test_survival_opening_death_insight_can_use_survival_without_opening_deaths():
    card = survival_opening_death_insight_from_snapshot(
        _snapshot(
            metrics={
                "rounds": 12,
                "opening_deaths": 1,
                "opening_death_rate": 0.083,
                "survived_rounds": 6,
                "survival_rate": 0.5,
            },
            confidence={
                "opening_death_rate": {"level": "high"},
                "survival_rate": {"level": "high"},
            },
        )
    )

    assert card is not None
    assert validate_insight_cards([card]) == ()
    assert card["problem"] == (
        "Poor round survival is the strongest evidence-backed survival problem in this match snapshot."
    )
    assert card["confidence"] == "high"
    assert [item["metric_id"] for item in card["evidence"]] == ["survival_rate"]
    assert "Opening death evidence depends on parser opening duel event order." not in card["caveats"]


def test_survival_opening_death_insight_returns_none_for_weak_evidence():
    low_confidence = _snapshot(
        metrics={
            "rounds": 10,
            "opening_deaths": 3,
            "opening_death_rate": 0.3,
            "survived_rounds": 5,
            "survival_rate": 0.5,
        },
        confidence={
            "opening_death_rate": {"level": "low"},
            "survival_rate": {"level": "low"},
        },
    )
    low_sample = _snapshot(
        metrics={
            "rounds": 7,
            "opening_deaths": 3,
            "opening_death_rate": 0.429,
            "survived_rounds": 3,
            "survival_rate": 0.429,
        },
        confidence={
            "opening_death_rate": {"level": "high"},
            "survival_rate": {"level": "high"},
        },
    )

    assert survival_opening_death_insight_from_snapshot(low_confidence) is None
    assert survival_opening_death_insight_from_snapshot(low_sample) is None


def test_survival_opening_death_insights_are_deterministically_prioritized():
    opening = _snapshot(
        match_id=2,
        metrics={
            "rounds": 10,
            "opening_deaths": 3,
            "opening_death_rate": 0.3,
            "survived_rounds": 8,
            "survival_rate": 0.8,
        },
        confidence={
            "opening_death_rate": {"level": "high"},
            "survival_rate": {"level": "high"},
        },
    )
    survival = _snapshot(
        match_id=1,
        metrics={"rounds": 10, "survived_rounds": 4, "survival_rate": 0.4},
        confidence={"survival_rate": {"level": "high"}},
    )

    cards = survival_opening_death_insights_from_snapshots([survival, opening])

    assert [card["evidence"][0]["metric_id"] for card in cards] == ["opening_death_rate", "survival_rate"]


def test_bad_fight_trade_insight_uses_untraded_death_evidence_with_counts_and_rates():
    card = bad_fight_trade_insight_from_snapshot(
        _snapshot(
            metrics={
                "rounds": 10,
                "opening_deaths": 3,
                "opening_death_rate": 0.3,
                "untraded_deaths": 3,
                "traded_deaths": 1,
                "trade_status_known_deaths": 4,
                "untraded_death_rate": 0.75,
                "traded_death_rate": 0.25,
            },
            confidence={
                "opening_death_rate": {"level": "high"},
                "untraded_death_rate": {"level": "high"},
                "traded_death_rate": {"level": "high"},
            },
        )
    )

    assert card is not None
    assert validate_insight_cards([card]) == ()
    assert card["problem"] == "Untraded deaths show bad fight selection or poor trade spacing in this match snapshot."
    assert card["confidence"] == "high"
    assert card["evidence"] == [
        {
            "metric_id": "untraded_death_rate",
            "value": 0.75,
            "threshold": 0.6,
            "metric_confidence": "high",
            "sample_count": 4,
            "match_ids": [42],
            "source": "core_combat_metrics",
            "count": 3,
            "known_trade_status_deaths": 4,
            "rounds": 10,
            "description": (
                "Untraded deaths are 3 of 4 deaths with known trade status (0.750), meeting the 0.600 "
                "insight threshold."
            ),
        },
        {
            "metric_id": "opening_death_rate",
            "value": 0.3,
            "threshold": 0.22,
            "metric_confidence": "high",
            "sample_count": 10,
            "match_ids": [42],
            "source": "core_combat_metrics",
            "description": "Opening deaths are 3 over 10 rounds (0.300), meeting the 0.220 insight threshold.",
        },
    ]
    assert "Untraded death evidence depends on parser trade window and side inference." in card["caveats"]
    assert "Opening death evidence depends on parser opening duel event order." in card["caveats"]


def test_bad_fight_trade_insight_caveats_ambiguous_trade_data_without_hard_claim():
    card = bad_fight_trade_insight_from_snapshot(
        _snapshot(
            metrics={
                "rounds": 10,
                "ambiguous_traded_deaths": 2,
                "trade_status_known_deaths": 0,
            },
            confidence={
                "traded_death_rate": {"level": "low"},
                "untraded_death_rate": {"level": "low"},
            },
            caveats=["Source events do not include both actor/victim team side; traded death is ambiguous."],
        )
    )

    assert card is not None
    assert validate_insight_cards([card]) == ()
    assert card["problem"] == "Trade behavior cannot be judged confidently from this match snapshot."
    assert card["confidence"] == "low"
    assert card["evidence"] == [
        {
            "metric_id": "ambiguous_traded_deaths",
            "value": 2,
            "metric_confidence": "low",
            "sample_count": 2,
            "match_ids": [42],
            "source": "core_combat_metrics",
            "description": (
                "2 death(s) have ambiguous trade status and were excluded from traded/untraded death rates."
            ),
        }
    ]
    assert "Weak or ambiguous trade data cannot support a hard bad-fight or trade recommendation." in card["caveats"]
    assert "Source events do not include both actor/victim team side; traded death is ambiguous." in card["caveats"]


def test_combined_coach_insights_prioritize_bad_fight_trade_before_prior_survival_insight():
    trade = _snapshot(
        match_id=7,
        metrics={
            "rounds": 10,
            "opening_deaths": 3,
            "opening_death_rate": 0.3,
            "untraded_deaths": 3,
            "trade_status_known_deaths": 4,
            "untraded_death_rate": 0.75,
        },
        confidence={
            "opening_death_rate": {"level": "high"},
            "untraded_death_rate": {"level": "high"},
        },
    )
    survival = _snapshot(
        match_id=8,
        metrics={"rounds": 10, "survived_rounds": 4, "survival_rate": 0.4},
        confidence={"survival_rate": {"level": "high"}},
    )

    cards = coach_insights_from_snapshots([survival, trade])

    assert [card["evidence"][0]["metric_id"] for card in cards] == [
        "untraded_death_rate",
        "opening_death_rate",
        "survival_rate",
    ]


def _snapshot(
    *,
    metrics: dict,
    confidence: dict,
    match_id: int = 42,
    caveats: list[str] | None = None,
) -> dict:
    return {
        "id": 100 + match_id,
        "match_id": match_id,
        "player_key": "steam:76561198000000001",
        "source": "core_combat_metrics",
        "source_event_set_id": "fixture:e02",
        "metrics": metrics,
        "confidence_baseline": {"source": "core-combat-metrics-v1", "metrics": confidence},
        "caveats": caveats or [],
        "metadata": {"schema_version": "core-combat-metrics-v1"},
    }
