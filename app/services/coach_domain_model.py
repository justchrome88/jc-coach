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
