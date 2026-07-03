from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

MetricReliability = Literal["trusted", "medium", "approximate", "low", "unavailable"]
MetricUsage = Literal["display", "diagnosis", "recommendation", "ai"]
UsageDecision = Literal["allowed", "warn", "suppressed"]

USAGES: tuple[MetricUsage, ...] = ("display", "diagnosis", "recommendation", "ai")


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    display_name: str
    source: str
    formula: str
    reliability: MetricReliability
    limitations: tuple[str, ...]
    usage: dict[MetricUsage, UsageDecision]
    aliases: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["limitations"] = list(self.limitations)
        payload["aliases"] = list(self.aliases)
        return payload


UNKNOWN_METRIC = MetricDefinition(
    metric_id="unknown",
    display_name="Unknown metric",
    source="not registered",
    formula="not defined",
    reliability="unavailable",
    limitations=("Metric is not registered in Metric Truth Layer.",),
    usage={usage: "suppressed" for usage in USAGES},
)


def _usage(
    display: UsageDecision = "allowed",
    diagnosis: UsageDecision = "allowed",
    recommendation: UsageDecision = "allowed",
    ai: UsageDecision = "allowed",
) -> dict[MetricUsage, UsageDecision]:
    return {
        "display": display,
        "diagnosis": diagnosis,
        "recommendation": recommendation,
        "ai": ai,
    }


METRIC_REGISTRY: dict[str, MetricDefinition] = {
    "result": MetricDefinition(
        "result",
        "Match result",
        "Match.result from CSV/JSON/Steam/parser import.",
        "win/loss/draw label supplied by source or importer.",
        "trusted",
        ("Trusted only as far as source match identity/result is correct.",),
        _usage(),
        aliases=("winrate",),
    ),
    "round_score": MetricDefinition(
        "round_score",
        "Round score",
        "Match.rounds_for and Match.rounds_against.",
        "rounds_for:rounds_against.",
        "trusted",
        ("Side attribution is separate and lower confidence than total score.",),
        _usage(),
        aliases=("rounds_for", "rounds_against", "score", "round_diff"),
    ),
    "kills": MetricDefinition(
        "kills",
        "Kills",
        "Match.kills or DemoPlayerRound aggregation.",
        "Total player kills in the match.",
        "trusted",
        ("Depends on correct target player selection for parsed demos.",),
        _usage(),
    ),
    "deaths": MetricDefinition(
        "deaths",
        "Deaths",
        "Match.deaths or DemoPlayerRound aggregation.",
        "Total player deaths in the match.",
        "trusted",
        ("Depends on correct target player selection for parsed demos.",),
        _usage(),
    ),
    "assists": MetricDefinition(
        "assists",
        "Assists",
        "Match.assists or DemoPlayerRound aggregation.",
        "Total player assists in the match.",
        "medium",
        ("Assist semantics depend on source/parser event support.",),
        _usage(ai="warn"),
    ),
    "kd_ratio": MetricDefinition(
        "kd_ratio",
        "K/D",
        "Match.kd or kills/deaths.",
        "kills / deaths; undefined when deaths are zero unless source supplies a value.",
        "trusted",
        ("Aggregated K/D can hide role/map context.",),
        _usage(),
        aliases=("kd", "avg_kd"),
    ),
    "adr": MetricDefinition(
        "adr",
        "ADR",
        "Match.adr or damage divided by rounds.",
        "total damage / played rounds.",
        "medium",
        ("Reliable when damage events and round counts exist; CSV/manual values rely on user/source input.",),
        _usage(ai="warn"),
        aliases=("avg_adr",),
    ),
    "kast": MetricDefinition(
        "kast",
        "KAST",
        "Match.kast or parser player-round K/A/survive/trade proxy.",
        "percent of rounds with kill, assist, survived or traded participation.",
        "approximate",
        ("Trade component is not fully reliable until traded-death facts are hardened.",),
        _usage(diagnosis="warn", recommendation="warn", ai="warn"),
        aliases=("avg_kast",),
    ),
    "hltv_rating": MetricDefinition(
        "hltv_rating",
        "Rating",
        "Match.rating from source/import.",
        "Source-provided rating; not a local verified HLTV 2.0 implementation.",
        "approximate",
        ("Formula may differ by source; do not use as primary diagnosis evidence.",),
        _usage(diagnosis="warn", recommendation="warn", ai="warn"),
        aliases=("rating", "avg_rating"),
    ),
    "kills_per_round": MetricDefinition(
        "kills_per_round",
        "Kills per round",
        "Derived from kills and total rounds.",
        "kills / (rounds_for + rounds_against).",
        "medium",
        ("Requires complete round score.",),
        _usage(ai="warn"),
    ),
    "deaths_per_round": MetricDefinition(
        "deaths_per_round",
        "Deaths per round",
        "Derived from deaths and total rounds.",
        "deaths / (rounds_for + rounds_against).",
        "medium",
        ("Requires complete round score.",),
        _usage(ai="warn"),
    ),
    "headshot_rate": MetricDefinition(
        "headshot_rate",
        "Headshot rate",
        "Match.headshot_percent or weapon stats aggregation.",
        "headshot kills / kills * 100.",
        "medium",
        ("Not a crosshair-placement metric; low sample sizes are noisy.",),
        _usage(diagnosis="warn", recommendation="warn", ai="warn"),
        aliases=("headshot_percent", "avg_headshot_percent"),
    ),
    "entry_kills": MetricDefinition(
        "entry_kills",
        "Entry kills",
        "Match.entry_kills or parser opening duel facts.",
        "First-kill/opening-duel kills attributed to the player.",
        "medium",
        ("Opening duel detection depends on parser/source event order.",),
        _usage(ai="warn"),
    ),
    "entry_deaths": MetricDefinition(
        "entry_deaths",
        "Entry deaths",
        "Match.entry_deaths or parser opening duel facts.",
        "First-death/opening-duel deaths attributed to the player.",
        "medium",
        ("Opening duel detection depends on parser/source event order.",),
        _usage(ai="warn"),
        aliases=("entry_deaths_per_match", "entry_diff"),
    ),
    "early_deaths": MetricDefinition(
        "early_deaths",
        "Early deaths",
        "Match.early_deaths when available.",
        "Deaths inside the parser early-round timing window when timing anchors are available.",
        "approximate",
        ("Missing timing anchors produce no value; do not fallback to entry_deaths.",),
        _usage(diagnosis="warn", recommendation="warn", ai="warn"),
        aliases=("early_deaths_per_match",),
    ),
    "trade_kills": MetricDefinition(
        "trade_kills",
        "Trade kills",
        "DemoDuel.trade_kill from parser death-event order.",
        "Kill within parser trade window after teammate death.",
        "low",
        ("Trade window/team-side inference needs parser hardening.",),
        _usage(display="warn", diagnosis="suppressed", recommendation="suppressed", ai="warn"),
        aliases=("trade_kill",),
    ),
    "traded_deaths": MetricDefinition(
        "traded_deaths",
        "Traded deaths",
        "Not currently stored as a reliable match metric.",
        "Unavailable until parser emits traded/untraded death facts.",
        "unavailable",
        ("Do not claim traded-death rate from current data.",),
        _usage(display="suppressed", diagnosis="suppressed", recommendation="suppressed", ai="suppressed"),
        aliases=("traded_death", "untraded_death"),
    ),
    "utility_damage": MetricDefinition(
        "utility_damage",
        "Utility damage",
        "Match.utility_damage or parser grenade/damage events.",
        "Damage attributed to grenade utility.",
        "medium",
        ("Attribution depends on parser support for utility weapon names and damage events.",),
        _usage(ai="warn"),
        aliases=("avg_utility_damage",),
    ),
    "flash_assists": MetricDefinition(
        "flash_assists",
        "Flash assists",
        "Match.flash_assists or parser blind/kill correlation.",
        "Kills assisted by player flash events.",
        "approximate",
        ("Blind duration and kill correlation are best-effort.",),
        _usage(diagnosis="warn", recommendation="warn", ai="warn"),
        aliases=("avg_flash_assists",),
    ),
    "enemies_flashed": MetricDefinition(
        "enemies_flashed",
        "Enemies flashed",
        "Match.enemies_flashed or parser blind events.",
        "Enemy players affected by flash events.",
        "approximate",
        ("Counts do not prove useful team impact without context.",),
        _usage(diagnosis="warn", recommendation="warn", ai="warn"),
    ),
    "grenade_rating": MetricDefinition(
        "grenade_rating",
        "Grenade rating",
        "Derived/product concept from utility damage and flash value.",
        "No stable formula yet.",
        "unavailable",
        ("Use utility_damage/flash_assists separately until formula is defined.",),
        _usage(display="suppressed", diagnosis="suppressed", recommendation="suppressed", ai="suppressed"),
    ),
    "aim_rating": MetricDefinition(
        "aim_rating",
        "Aim rating",
        "Derived/product concept from aim profile.",
        "No stable formula yet.",
        "unavailable",
        ("ADR/HS/opening-duel components exist, but no stable composite aim_rating exists.",),
        _usage(display="suppressed", diagnosis="suppressed", recommendation="suppressed", ai="suppressed"),
    ),
    "accuracy": MetricDefinition(
        "accuracy",
        "Accuracy",
        "DemoWeaponStat shots/hits when weapon_fire and hit events exist.",
        "hits / shots * 100.",
        "low",
        ("Requires reliable weapon_fire/hit correlation; currently not hard diagnosis evidence.",),
        _usage(display="warn", diagnosis="suppressed", recommendation="suppressed", ai="warn"),
    ),
    "swing_score": MetricDefinition(
        "swing_score",
        "Swing score",
        "Deep parser win-probability swing approximation.",
        "Sum of approximate round win-probability deltas from player events.",
        "approximate",
        ("Model is heuristic and depends on parser event completeness.",),
        _usage(diagnosis="warn", recommendation="warn", ai="warn"),
        aliases=("avg_swing_score",),
    ),
    "side_split_metrics": MetricDefinition(
        "side_split_metrics",
        "Side split metrics",
        "side_t_rounds_* and side_ct_rounds_* on Match.",
        "Side-specific won/lost rounds and winrate.",
        "low",
        ("Side switching/team inference is low confidence until parser hardening.",),
        _usage(display="warn", diagnosis="suppressed", recommendation="suppressed", ai="warn"),
        aliases=("side_t_rounds_won", "side_t_rounds_lost", "side_ct_rounds_won", "side_ct_rounds_lost"),
    ),
    "crosshair_placement": MetricDefinition(
        "crosshair_placement",
        "Crosshair placement",
        "Not available from current stable facts.",
        "Unavailable until view-angle/position timeline is reliable.",
        "unavailable",
        ("Must remain data gap; do not infer from ADR/HS alone.",),
        _usage(display="suppressed", diagnosis="suppressed", recommendation="suppressed", ai="suppressed"),
    ),
}

_ALIASES = {
    alias: definition.metric_id
    for definition in METRIC_REGISTRY.values()
    for alias in (definition.metric_id, *definition.aliases)
}


def metric_definition(metric_id: str) -> MetricDefinition:
    canonical_id = _ALIASES.get(metric_id, metric_id)
    return METRIC_REGISTRY.get(canonical_id, UNKNOWN_METRIC)


def metric_reliability(metric_id: str) -> MetricReliability:
    return metric_definition(metric_id).reliability


def usage_decision(metric_id: str, usage: MetricUsage) -> UsageDecision:
    return metric_definition(metric_id).usage.get(usage, "suppressed")


def is_metric_allowed(metric_id: str, usage: MetricUsage) -> bool:
    return usage_decision(metric_id, usage) in {"allowed", "warn"}


def is_metric_allowed_for_hard_claim(metric_id: str, usage: MetricUsage) -> bool:
    return usage_decision(metric_id, usage) == "allowed"


def metric_warning(metric_id: str, usage: MetricUsage) -> str | None:
    definition = metric_definition(metric_id)
    decision = usage_decision(metric_id, usage)
    if decision == "allowed":
        return None
    if decision == "suppressed":
        return f"{definition.metric_id} suppressed for {usage}: {definition.reliability} reliability."
    return f"{definition.metric_id} should be used with warning for {usage}: {definition.reliability} reliability."


def suppressed_metrics_for_usage(usage: MetricUsage) -> list[str]:
    return sorted(
        definition.metric_id
        for definition in METRIC_REGISTRY.values()
        if usage_decision(definition.metric_id, usage) == "suppressed"
    )


def metric_truth_payload(metric_ids: list[str] | tuple[str, ...] | None = None) -> list[dict]:
    definitions = [metric_definition(metric_id) for metric_id in metric_ids] if metric_ids else METRIC_REGISTRY.values()
    seen: set[str] = set()
    payload = []
    for definition in definitions:
        if definition.metric_id in seen:
            continue
        seen.add(definition.metric_id)
        payload.append(definition.to_dict())
    return payload
