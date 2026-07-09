from app.services.coach_insights import (
    INSIGHT_CARD_SCHEMA_VERSION,
    MEDIUM_CONFIDENCE_CAVEAT,
    bad_fight_trade_insight_from_snapshot,
    coach_insight_candidates_from_snapshots,
    coach_insights_from_snapshots,
    coach_insights_with_mission_readiness_from_snapshots,
    no_data_insight_card,
    prioritize_coach_insights,
    serialize_insight_cards,
    survival_opening_death_insight_from_snapshot,
    survival_opening_death_insights_from_snapshots,
    utility_value_insight_from_snapshot,
    validate_insight_cards,
)

UTILITY_OMISSION_CAVEAT = (
    "Unsupported grenade_rating and flash_assists must remain omitted unless accepted source data exists."
)
UTILITY_WEAK_DATA_CAVEAT = (
    "Weak flash and detonation facts cannot be converted into grenade value, flash assists, lineups, "
    "or grenade_rating."
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


def test_combined_coach_insights_select_top_two_prioritized_cards():
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

    assert len(cards) == 2
    assert [card["evidence"][0]["metric_id"] for card in cards] == [
        "untraded_death_rate",
        "opening_death_rate",
    ]


def test_coach_insight_candidates_preserve_full_ranked_candidate_list_for_diagnostics():
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

    cards = coach_insight_candidates_from_snapshots([survival, trade])

    assert [card["evidence"][0]["metric_id"] for card in cards] == [
        "untraded_death_rate",
        "opening_death_rate",
        "survival_rate",
    ]


def test_prioritizer_uses_confidence_before_evidence_strength_within_same_severity():
    high_confidence = utility_value_insight_from_snapshot(
        _utility_snapshot(
            match_id=10,
            metrics={"utility_damage": 45},
            confidence={"utility_damage": {"level": "high", "usable_for_insights": True}},
        )
    )
    medium_confidence_with_more_damage = utility_value_insight_from_snapshot(
        _utility_snapshot(
            match_id=11,
            metrics={"utility_damage": 120},
            confidence={"utility_damage": {"level": "medium", "usable_for_insights": True}},
        )
    )

    cards = prioritize_coach_insights([medium_confidence_with_more_damage, high_confidence])

    assert [card["evidence"][0]["match_ids"] for card in cards] == [[10], [11]]
    assert [card["confidence"] for card in cards] == ["high", "medium"]


def test_prioritizer_uses_evidence_strength_then_sample_count_as_tie_breakers():
    weaker_opening = survival_opening_death_insight_from_snapshot(
        _snapshot(
            match_id=12,
            metrics={
                "rounds": 10,
                "opening_deaths": 3,
                "opening_death_rate": 0.3,
                "survived_rounds": 8,
                "survival_rate": 0.8,
            },
            confidence={"opening_death_rate": {"level": "high"}},
        )
    )
    stronger_opening = survival_opening_death_insight_from_snapshot(
        _snapshot(
            match_id=13,
            metrics={
                "rounds": 10,
                "opening_deaths": 4,
                "opening_death_rate": 0.4,
                "survived_rounds": 8,
                "survival_rate": 0.8,
            },
            confidence={"opening_death_rate": {"level": "high"}},
        )
    )
    same_strength_larger_sample = survival_opening_death_insight_from_snapshot(
        _snapshot(
            match_id=14,
            metrics={
                "rounds": 14,
                "opening_deaths": 4,
                "opening_death_rate": 0.3,
                "survived_rounds": 10,
                "survival_rate": 0.714,
            },
            confidence={"opening_death_rate": {"level": "high"}},
        )
    )

    cards = prioritize_coach_insights([weaker_opening, stronger_opening, same_strength_larger_sample], limit=3)

    assert [card["evidence"][0]["match_ids"] for card in cards] == [[13], [14], [12]]


def test_low_confidence_context_cannot_outrank_high_confidence_critical_problem():
    low_confidence_context = bad_fight_trade_insight_from_snapshot(
        _snapshot(
            match_id=15,
            metrics={"rounds": 10, "ambiguous_traded_deaths": 9, "trade_status_known_deaths": 0},
            confidence={"untraded_death_rate": {"level": "low"}},
        )
    )
    high_confidence_critical = bad_fight_trade_insight_from_snapshot(
        _snapshot(
            match_id=16,
            metrics={
                "rounds": 10,
                "untraded_deaths": 2,
                "trade_status_known_deaths": 3,
                "untraded_death_rate": 0.667,
            },
            confidence={"untraded_death_rate": {"level": "high"}},
        )
    )

    cards = prioritize_coach_insights([low_confidence_context, high_confidence_critical])

    assert cards[0]["confidence"] == "high"
    assert cards[0]["evidence"][0]["metric_id"] == "untraded_death_rate"


def test_utility_value_insight_uses_supported_damage_without_grenade_rating_claim():
    card = utility_value_insight_from_snapshot(
        _utility_snapshot(
            metrics={
                "utility_damage": 49,
                "he_damage": 42,
                "molotov_damage": 7,
                "enemies_flashed": 1,
                "flash_detonations": 1,
            },
            confidence={
                "utility_damage": {
                    "level": "medium",
                    "usable_for_insights": True,
                    "hard_recommendation_eligible": True,
                },
                "enemies_flashed": {"level": "low", "usable_for_insights": False},
                "grenade_rating": {"level": "unavailable", "usable_for_insights": False},
            },
            caveats=["Utility damage is inferred from parser weapon name on player_hurt."],
        )
    )

    assert card is not None
    assert validate_insight_cards([card]) == ()
    assert card["problem"] == "Utility damage is the only supported utility value signal in this match snapshot."
    assert card["confidence"] == "medium"
    assert card["evidence"] == [
        {
            "metric_id": "utility_damage",
            "value": 49,
            "threshold": 40,
            "metric_confidence": "medium",
            "match_ids": [42],
            "source": "utility_metrics",
            "description": (
                "Utility damage is 49 in this snapshot, meeting the 40 first-pass insight threshold. "
                "Supported damage breakdown: he_damage=42, molotov_damage=7."
            ),
            "breakdown": {"he_damage": 42, "molotov_damage": 7},
            "source_event_count": 2,
        }
    ]
    assert MEDIUM_CONFIDENCE_CAVEAT in card["caveats"]
    assert UTILITY_OMISSION_CAVEAT in card["caveats"]
    assert "Utility damage is inferred from parser weapon name on player_hurt." in card["caveats"]


def test_unsupported_utility_data_produces_low_confidence_no_claim_with_caveat():
    card = utility_value_insight_from_snapshot(
        _utility_snapshot(
            metrics={},
            confidence={
                "utility_damage": {
                    "level": "unavailable",
                    "reasons": [
                        (
                            "No supported utility_damage events for this player; utility damage is omitted "
                            "instead of set to zero."
                        )
                    ],
                    "usable_for_insights": False,
                },
                "grenade_rating": {"level": "unavailable", "usable_for_insights": False},
            },
            caveats=[
                "Utility damage source data is missing; utility damage metrics are unavailable.",
                "Downstream coach and metrics layers must not infer grenade quality from missing utility data.",
            ],
        )
    )

    assert card is not None
    assert validate_insight_cards([card]) == ()
    assert card["problem"] == "Utility value cannot be judged confidently from this match snapshot."
    assert card["confidence"] == "low"
    assert card["evidence"] == []
    assert "No supported utility_damage evidence met the first-pass utility insight gate." in card["caveats"]
    assert (
        "Downstream coach and metrics layers must not infer grenade quality from missing utility data."
        in card["caveats"]
    )


def test_weak_flash_utility_data_stays_low_confidence_context_only():
    card = utility_value_insight_from_snapshot(
        _utility_snapshot(
            metrics={"enemies_flashed": 1, "flash_detonations": 1},
            confidence={
                "enemies_flashed": {"level": "low", "usable_for_insights": False},
                "flash_detonations": {"level": "low", "usable_for_insights": False},
                "utility_damage": {"level": "unavailable", "usable_for_insights": False},
            },
            caveats=["Source row omitted blind duration; flash value must remain low-confidence."],
        )
    )

    assert card is not None
    assert validate_insight_cards([card]) == ()
    assert card["confidence"] == "low"
    assert [item["metric_id"] for item in card["evidence"]] == ["enemies_flashed", "flash_detonations"]
    assert all(item["metric_confidence"] == "low" for item in card["evidence"])
    assert UTILITY_WEAK_DATA_CAVEAT in card["caveats"]
    assert "Source row omitted blind duration; flash value must remain low-confidence." in card["caveats"]


def test_utility_value_confidence_gate_blocks_hard_claim_from_low_confidence_damage():
    card = utility_value_insight_from_snapshot(
        _utility_snapshot(
            metrics={"utility_damage": 90},
            confidence={
                "utility_damage": {
                    "level": "low",
                    "reasons": ["Utility damage source events are incomplete."],
                    "usable_for_insights": False,
                }
            },
        )
    )

    assert card is not None
    assert validate_insight_cards([card]) == ()
    assert card["problem"] == "Utility value cannot be judged confidently from this match snapshot."
    assert card["confidence"] == "low"
    assert card["evidence"] == [
        {
            "metric_id": "utility_damage",
            "value": 90,
            "metric_confidence": "low",
            "match_ids": [42],
            "source": "utility_metrics",
            "description": (
                "utility_damage is present but did not pass the supported utility insight gate; "
                "treat it as caveated context only."
            ),
            "threshold": 40,
        }
    ]
    assert "Utility damage source events are incomplete." in card["caveats"]


def test_mission_readiness_allows_mission_eligible_owner_card():
    utility = _utility_snapshot(
        metrics={"utility_damage": 94, "molotov_damage": 93},
        confidence={
            "utility_damage": {
                "level": "medium",
                "usable_for_insights": True,
                "usable_for_missions": True,
                "hard_recommendation_eligible": True,
            }
        },
    )

    cards = coach_insights_with_mission_readiness_from_snapshots([utility])

    readiness = cards[0]["mission_readiness"]
    assert readiness["can_become_mission"] is True
    assert readiness["target_metric_candidate"] == "utility_damage"
    assert readiness["baseline_value"] == 94
    assert readiness["confidence_eligibility"] == {
        "level": "medium",
        "usable_for_missions": True,
        "hard_recommendation_eligible": True,
    }
    assert readiness["missing_requirements"] == []
    assert readiness["blocking_reason_codes"] == []


def test_mission_readiness_blocks_suppressed_snapshot_metric_with_reason_codes():
    survival = _snapshot(
        metrics={"rounds": 14, "survived_rounds": 5, "survival_rate": 0.357},
        confidence={
            "survival_rate": {
                "level": "medium",
                "usable_for_insights": True,
                "usable_for_missions": False,
                "hard_recommendation_eligible": False,
                "reason_codes": ["suppressed_metric_blocks_hard_recommendation"],
            }
        },
    )

    cards = coach_insights_with_mission_readiness_from_snapshots([survival])

    readiness = cards[0]["mission_readiness"]
    assert readiness["can_become_mission"] is False
    assert readiness["target_metric_candidate"] == "survival_rate"
    assert readiness["baseline_value"] == 0.357
    assert "usable_for_missions" in readiness["missing_requirements"]
    assert "hard_recommendation_eligible" in readiness["missing_requirements"]
    assert "confidence_not_mission_eligible" in readiness["blocking_reason_codes"]
    assert "metric_not_hard_recommendation_eligible" in readiness["blocking_reason_codes"]
    assert "suppressed_metric_blocks_hard_recommendation" in readiness["blocking_reason_codes"]


def test_low_or_unavailable_confidence_cannot_become_hard_mission():
    low_confidence_utility = _utility_snapshot(
        metrics={"utility_damage": 90},
        confidence={
            "utility_damage": {
                "level": "low",
                "usable_for_insights": False,
                "usable_for_missions": False,
                "hard_recommendation_eligible": False,
                "reason_codes": ["low_confidence_blocks_hard_recommendation"],
            }
        },
    )

    cards = coach_insights_with_mission_readiness_from_snapshots([low_confidence_utility])

    readiness = cards[0]["mission_readiness"]
    assert readiness["can_become_mission"] is False
    assert readiness["target_metric_candidate"] == "utility_damage"
    assert readiness["confidence_eligibility"]["level"] == "low"
    assert "mission_eligible_confidence" in readiness["missing_requirements"]
    assert "low_or_unavailable_confidence" in readiness["blocking_reason_codes"]
    assert "low_confidence_blocks_hard_recommendation" in readiness["blocking_reason_codes"]


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


def _utility_snapshot(
    *,
    metrics: dict,
    confidence: dict,
    match_id: int = 42,
    caveats: list[str] | None = None,
) -> dict:
    return {
        "id": 200 + match_id,
        "match_id": match_id,
        "player_key": "steam:76561198000000001",
        "source": "utility_metrics",
        "source_event_set_id": "fixture:c05:utility",
        "metrics": metrics,
        "confidence_baseline": {
            "source": "utility-metrics-v1",
            "metrics": confidence,
            "event_coverage": {
                "utility_damage_events": 2,
                "flash_effect_events": 1,
                "utility_detonation_events": 4,
                "utility_data_gap_events": 1,
            },
        },
        "caveats": caveats or [],
        "metadata": {"schema_version": "utility-metrics-v1"},
    }
