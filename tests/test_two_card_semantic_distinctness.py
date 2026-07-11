from __future__ import annotations

import pytest

from app.services.coach.semantic_distinctness import (
    DuplicateDomainCardSemanticsError,
    two_card_semantic_distinctness,
)


def test_two_domain_cards_can_share_metric_and_remain_semantically_distinct():
    cards = [
        _card(
            "impact_leak",
            headline="Frequent untraded deaths are the clearest impact leak",
            hypothesis="Useful output is not converting because deaths produce no immediate trade.",
            pattern="Costly deaths limit conversion of otherwise adequate individual impact.",
            reasoning="Damage is adequate, but high untraded deaths limit outcome conversion.",
            focus="Make deaths tradeable or survive while preserving current output.",
        ),
        _card(
            "bad_fight_selection",
            headline="Too many deaths are left untradeable",
            hypothesis="Repeated poor duel selection produces isolated fights teammates cannot trade.",
            pattern="Repeated isolated fights have low death tradeability.",
            reasoning="Tradeability is weak while opening discipline is not the primary issue.",
            focus="Take fewer non-opening duels that teammates cannot immediately contest.",
        ),
    ]

    result = two_card_semantic_distinctness(cards)

    assert result["status"] == "PASS"
    assert result["shared_primary_metric"] == "untraded_death_rate"
    assert result["combined_diagnosis_similarity"] < result["near_duplicate_threshold"]
    assert result["safe_field_hashes"]["impact_leak"] != result["safe_field_hashes"]["bad_fight_selection"]


def test_duplicate_diagnoses_under_different_domain_labels_are_blocked():
    shared = {
        "headline": "Same diagnosis",
        "hypothesis": "The exact same hypothesis applies.",
        "pattern": "The exact same pattern applies.",
        "reasoning": "The exact same reasoning applies.",
        "focus": "Use the exact same focus.",
    }
    cards = [_card("impact_leak", **shared), _card("bad_fight_selection", **shared)]

    with pytest.raises(DuplicateDomainCardSemanticsError, match="duplicate"):
        two_card_semantic_distinctness(cards)


def test_unsupported_exact_tactical_cause_is_blocked():
    cards = [
        _card(
            "impact_leak",
            headline="Impact conversion",
            hypothesis="Deaths reduce conversion.",
            pattern="Untraded deaths repeat.",
            reasoning="The evidence supports a conversion problem.",
            focus="Preserve output while improving tradeability.",
        ),
        _card(
            "bad_fight_selection",
            headline="Exact angle problem",
            hypothesis="An exact angle caused every death.",
            pattern="Unsupported exact position claims.",
            reasoning="The model asserted an exact rotation.",
            focus="Change the exact angle.",
        ),
    ]

    with pytest.raises(DuplicateDomainCardSemanticsError, match="unsupported"):
        two_card_semantic_distinctness(cards)


def _card(
    domain: str,
    *,
    headline: str,
    hypothesis: str,
    pattern: str,
    reasoning: str,
    focus: str,
):
    return {
        "domain": domain,
        "headline": headline,
        "hypothesis": hypothesis,
        "primary_pattern": pattern,
        "reasoning_summary": reasoning,
        "recommended_focus": focus,
        "evidence_references": [{"metric_key": "untraded_death_rate"}],
        "counterevidence_references": [],
        "caveats": ["one-match replay remains insufficient_data"],
        "mission_target": {
            "primary_metric": "untraded_death_rate",
            "target_direction": "lower_is_better",
            "target_value": 0.75,
        },
    }
