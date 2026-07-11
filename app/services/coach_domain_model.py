from __future__ import annotations

from typing import Final

CANONICAL_COACH_DOMAINS: Final[tuple[str, str]] = (
    "impact_leak",
    "bad_fight_selection",
)
METRIC_GROUPS: Final[tuple[str, str, str]] = ("performance", "utility", "aim")

HYPOTHESIS_FAMILY_MAPPING: Final[dict[str, str]] = {
    "impact_leak": "impact_leak",
    "bad_fight_selection": "bad_fight_selection",
    "survival_opening": "bad_fight_selection",
    "bad_fight_trade": "bad_fight_selection",
    "trade_discipline": "bad_fight_selection",
    "utility_value": "context-only",
    "performance": "deprecated/unmapped",
    "utility": "deprecated/unmapped",
    "aim": "context-only",
}

LEGACY_DOMAIN_ALIASES: Final[dict[str, str | None]] = {
    "impact_leak": "impact_leak",
    "bad_fight_selection": "bad_fight_selection",
    "survival_opening": "bad_fight_selection",
    "bad_fight_trade": "bad_fight_selection",
    "trade_discipline": "bad_fight_selection",
    "utility_value": None,
    "performance": None,
    "utility": None,
    "aim": None,
    "coach_performance": None,
    "coach_utility": None,
    "coach_aim": None,
}

ACTIVE_MISSION_MODEL: Final[str] = "at_most_one_per_domain_per_owner"
COACH_DOMAIN_CONTRACTS: Final[tuple[dict[str, object], ...]] = (
    {
        "key": "impact_leak",
        "user_facing_name": "Impact Leak / Useful vs Useless Deaths",
        "purpose": (
            "Detect bounded patterns where supported individual impact does not "
            "convert into rounds or results, including death-cost context."
        ),
        "allowed_evidence": [
            "result",
            "round_score",
            "adr",
            "kast",
            "kills_per_round",
            "deaths",
            "survival_rate",
            "opening_deaths",
            "opening_death_rate",
        ],
        "disallowed_claims": [
            "economy",
            "positioning",
            "rotations",
            "spacing",
            "exact angles",
            "crosshair placement",
            "clutch diagnosis",
            "exact playlist",
        ],
        "hypothesis_families": ["impact_leak"],
        "mission_families": ["impact_leak_conversion"],
        "required_metrics": ["adr", "kast", "deaths", "survival_rate", "rounds_played", "result"],
        "optional_context_metrics": [
            "kills_per_round",
            "opening_deaths",
            "opening_death_rate",
            "effective_enemy_utility_damage",
            "multi_kill_rounds",
        ],
        "minimum_sample_confidence": {
            "matches": 5,
            "rounds": 40,
            "metric_confidence": ["medium", "high"],
        },
        "missing_data_behavior": "no_claim",
        "selection_suppression_behavior": (
            "Eligible only with outcome plus impact evidence; suppressed only "
            "when the owner already has an active impact_leak mission."
        ),
    },
    {
        "key": "bad_fight_selection",
        "user_facing_name": "Bad Fight Selection / Duel Discipline",
        "purpose": (
            "Detect repeated costly opening fights or bounded trade/survival "
            "patterns without inventing spatial or tactical causes."
        ),
        "allowed_evidence": [
            "opening_deaths",
            "opening_death_rate",
            "opening_duel_attempts",
            "opening_duel_win_rate",
            "deaths",
            "survival_rate",
            "untraded_deaths",
            "untraded_death_rate",
            "adr",
            "kast",
        ],
        "disallowed_claims": [
            "exact angles",
            "rotations",
            "spacing",
            "crosshair placement",
            "economy calls",
            "clutch diagnosis",
            "exact playlist",
        ],
        "hypothesis_families": ["survival_opening", "bad_fight_trade", "bad_fight_selection"],
        "mission_families": [
            "opening_duel_discipline",
            "survival_discipline",
            "bounded_trade_discipline",
        ],
        "required_metrics": [
            "rounds_played",
            "opening_deaths",
            "opening_death_rate",
            "survival_rate",
        ],
        "optional_context_metrics": [
            "untraded_deaths",
            "untraded_death_rate",
            "adr",
            "kast",
            "trade_status_known_deaths",
        ],
        "minimum_sample_confidence": {
            "matches": 3,
            "rounds": 8,
            "metric_confidence": ["medium", "high"],
        },
        "missing_data_behavior": "no_claim",
        "selection_suppression_behavior": (
            "Eligible only from supported duel/survival facts; suppressed only "
            "when the owner already has an active bad_fight_selection mission."
        ),
    },
)
COACH_DOMAIN_INVARIANTS: Final[tuple[str, ...]] = (
    "metric group != coach domain",
    "hypothesis family != coach domain",
    "mission id != domain",
    "utility_value cannot generate or suppress as a coach domain",
    "no third coach domain is accepted without an explicit product decision",
    "an active mission suppresses only the same canonical domain",
)


def runtime_coach_domain_contract() -> dict[str, object]:
    """Return the declared contract generated from runtime-owned definitions."""
    return {
        "schema_version": "canonical-coach-domain-model-v2",
        "decision_task": "H01B-R02A2",
        "source_files": [
            "app/services/coach_domain_model.py",
            "_legacy_archive/r02a2-2026-07-11/docs/coach/coach-domain-model.json",
        ],
        "active_mission_model": ACTIVE_MISSION_MODEL,
        "coach_domains": list(COACH_DOMAIN_CONTRACTS),
        "metric_groups": list(METRIC_GROUPS),
        "hypothesis_family_mapping": dict(HYPOTHESIS_FAMILY_MAPPING),
        "invariants": list(COACH_DOMAIN_INVARIANTS),
    }


def canonical_domain_for_family(family: str | None) -> str | None:
    if not family:
        return None
    mapped = HYPOTHESIS_FAMILY_MAPPING.get(family.strip().lower())
    return mapped if mapped in CANONICAL_COACH_DOMAINS else None


def canonicalize_domain_key(domain_key: str | None) -> str | None:
    if not domain_key:
        return None
    normalized = domain_key.strip().lower()
    if normalized in CANONICAL_COACH_DOMAINS:
        return normalized
    return LEGACY_DOMAIN_ALIASES.get(normalized)


def require_canonical_domain(domain_key: str | None) -> str:
    canonical = canonicalize_domain_key(domain_key)
    if canonical is None:
        raise ValueError(f"Noncanonical coach domain: {domain_key or 'missing'}")
    return canonical
