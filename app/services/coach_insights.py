from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

INSIGHT_CARD_SCHEMA_VERSION = "coach-insight-card-v1"
SURVIVAL_OPENING_INSIGHT_VERSION = "survival-opening-insight-v1"
BAD_FIGHT_TRADE_INSIGHT_VERSION = "bad-fight-trade-insight-v1"
VALID_INSIGHT_CONFIDENCE = {"low", "medium", "high"}
REQUIRED_INSIGHT_CARD_FIELDS = ("problem", "evidence", "confidence", "caveats", "recommended_focus")
USABLE_INSIGHT_CONFIDENCE = {"medium", "high"}
MIN_SURVIVAL_OPENING_ROUNDS = 8
MIN_OPENING_DEATHS = 2
OPENING_DEATH_RATE_THRESHOLD = 0.22
SURVIVAL_RATE_THRESHOLD = 0.55
MIN_TRADE_STATUS_KNOWN_DEATHS = 2
MIN_UNTRADED_DEATHS = 2
UNTRADED_DEATH_RATE_THRESHOLD = 0.60
MEDIUM_CONFIDENCE_CAVEAT = "Metric confidence is medium, so treat this as a bounded review signal."


@dataclass(frozen=True)
class InsightCard:
    problem: str
    evidence: tuple[dict[str, Any], ...]
    confidence: Literal["low", "medium", "high"]
    caveats: tuple[str, ...]
    recommended_focus: str
    schema_version: str = INSIGHT_CARD_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "problem": self.problem,
            "evidence": [dict(item) for item in self.evidence],
            "confidence": self.confidence,
            "caveats": list(self.caveats),
            "recommended_focus": self.recommended_focus,
        }


@dataclass(frozen=True)
class InsightCardValidationIssue:
    code: str
    message: str
    path: str


def validate_insight_cards(raw_cards: Any, *, path: str = "$.insight_cards") -> tuple[InsightCardValidationIssue, ...]:
    issues: list[InsightCardValidationIssue] = []
    if not isinstance(raw_cards, list):
        return (
            InsightCardValidationIssue(
                "invalid_insight_cards",
                "insight_cards must be a list.",
                path,
            ),
        )
    if not raw_cards:
        return (
            InsightCardValidationIssue(
                "missing_insight_cards",
                "At least one insight card is required.",
                path,
            ),
        )

    for index, card in enumerate(raw_cards):
        card_path = f"{path}[{index}]"
        if not isinstance(card, dict):
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_card",
                    "Insight card must be an object.",
                    card_path,
                )
            )
            continue
        for field in REQUIRED_INSIGHT_CARD_FIELDS:
            if field not in card:
                issues.append(
                    InsightCardValidationIssue(
                        "missing_insight_card_field",
                        f"Missing required insight card field: {field}.",
                        f"{card_path}.{field}",
                    )
                )
        _validate_non_empty_string(card, "problem", card_path, issues)
        _validate_non_empty_string(card, "recommended_focus", card_path, issues)
        confidence = card.get("confidence")
        if confidence not in VALID_INSIGHT_CONFIDENCE:
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_confidence",
                    "Insight card confidence must be one of: low, medium, high.",
                    f"{card_path}.confidence",
                )
            )
        evidence = card.get("evidence")
        caveats = _string_list(card.get("caveats"))
        if not isinstance(card.get("caveats"), list):
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_caveats",
                    "Insight card caveats must be a list.",
                    f"{card_path}.caveats",
                )
            )
        elif any(not isinstance(item, str) or not item.strip() for item in card.get("caveats") or []):
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_caveat",
                    "Insight card caveats must be non-empty strings.",
                    f"{card_path}.caveats",
                )
            )
        _validate_evidence(evidence, confidence, caveats, card_path, issues)
    return tuple(issues)


def serialize_insight_cards(raw_cards: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_cards, list):
        return []
    serialized: list[dict[str, Any]] = []
    for card in raw_cards:
        if not isinstance(card, dict):
            continue
        model = _insight_card_model(card)
        if model is not None:
            serialized.append(model.to_dict())
    return serialized


def no_data_insight_card(reason: str) -> dict[str, Any]:
    recommended_focus = "Use the dashboard and current accepted recommendation until validated insight data exists."
    return InsightCard(
        problem="No validated coach insight is available from the submitted AI output.",
        evidence=(),
        confidence="low",
        caveats=(reason,),
        recommended_focus=recommended_focus,
    ).to_dict()


def survival_opening_death_insight_from_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    metrics = _mapping(snapshot.get("metrics"))
    confidence_baseline = _mapping(snapshot.get("confidence_baseline"))
    metric_confidence = _mapping(confidence_baseline.get("metrics"))
    rounds = _number(metrics.get("rounds"))
    if rounds is None or rounds < MIN_SURVIVAL_OPENING_ROUNDS:
        return None

    opening = _opening_death_evidence(snapshot, metrics, metric_confidence, rounds)
    survival = _survival_evidence(snapshot, metrics, metric_confidence, rounds)
    evidence = [item for item in (opening, survival) if item is not None]
    if not evidence:
        return None

    confidence = _card_confidence(evidence)
    caveats = _survival_opening_caveats(snapshot, evidence, confidence)
    primary = evidence[0]
    if primary["metric_id"] == "opening_death_rate":
        problem = "Frequent opening deaths are the strongest evidence-backed survival problem in this match snapshot."
        recommended_focus = (
            "Review the first-contact rounds represented by this snapshot before changing broader coach goals."
        )
    else:
        problem = "Poor round survival is the strongest evidence-backed survival problem in this match snapshot."
        recommended_focus = (
            "Review the death rounds represented by this snapshot before changing broader coach goals."
        )
    return InsightCard(
        problem=problem,
        evidence=tuple(evidence),
        confidence=confidence,
        caveats=tuple(caveats),
        recommended_focus=recommended_focus,
    ).to_dict()


def survival_opening_death_insights_from_snapshots(
    snapshots: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates = [
        card
        for snapshot in snapshots
        for card in [survival_opening_death_insight_from_snapshot(snapshot)]
        if card is not None
    ]
    return sorted(candidates, key=_insight_sort_key)


def bad_fight_trade_insight_from_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    metrics = _mapping(snapshot.get("metrics"))
    confidence_baseline = _mapping(snapshot.get("confidence_baseline"))
    metric_confidence = _mapping(confidence_baseline.get("metrics"))

    trade_evidence = _untraded_death_evidence(snapshot, metrics, metric_confidence)
    if trade_evidence is None:
        return _ambiguous_trade_insight_from_snapshot(snapshot, metrics)

    rounds = _number(metrics.get("rounds"))
    opening_evidence = (
        _opening_death_evidence(snapshot, metrics, metric_confidence, rounds)
        if rounds is not None and rounds >= MIN_SURVIVAL_OPENING_ROUNDS
        else None
    )
    evidence = [item for item in (trade_evidence, opening_evidence) if item is not None]
    confidence = _card_confidence(evidence)
    caveats = _bad_fight_trade_caveats(snapshot, metrics, evidence, confidence)
    return InsightCard(
        problem="Untraded deaths show bad fight selection or poor trade spacing in this match snapshot.",
        evidence=tuple(evidence),
        confidence=confidence,
        caveats=tuple(caveats),
        recommended_focus=(
            "Review the listed death rounds as trade-spacing evidence before turning this into a broader goal."
        ),
    ).to_dict()


def bad_fight_trade_insights_from_snapshots(
    snapshots: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates = [
        card for snapshot in snapshots for card in [bad_fight_trade_insight_from_snapshot(snapshot)] if card is not None
    ]
    return sorted(candidates, key=_insight_sort_key)


def coach_insights_from_snapshots(snapshots: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        *bad_fight_trade_insights_from_snapshots(snapshots),
        *survival_opening_death_insights_from_snapshots(snapshots),
    ]
    return sorted(candidates, key=_insight_sort_key)


def _insight_card_model(card: dict[str, Any]) -> InsightCard | None:
    if validate_insight_cards([card]):
        return None
    evidence = tuple(dict(item) for item in card["evidence"] if isinstance(item, dict))
    return InsightCard(
        problem=card["problem"].strip(),
        evidence=evidence,
        confidence=card["confidence"],
        caveats=tuple(_string_list(card["caveats"])),
        recommended_focus=card["recommended_focus"].strip(),
    )


def _validate_non_empty_string(
    card: dict[str, Any],
    field: str,
    path: str,
    issues: list[InsightCardValidationIssue],
) -> None:
    if not isinstance(card.get(field), str) or not card.get(field, "").strip():
        issues.append(
            InsightCardValidationIssue(
                "invalid_insight_card_field",
                f"Insight card field must be a non-empty string: {field}.",
                f"{path}.{field}",
            )
        )


def _validate_evidence(
    evidence: Any,
    confidence: Any,
    caveats: list[str],
    path: str,
    issues: list[InsightCardValidationIssue],
) -> None:
    if not isinstance(evidence, list):
        issues.append(
            InsightCardValidationIssue(
                "invalid_insight_evidence",
                "Insight card evidence must be a list.",
                f"{path}.evidence",
            )
        )
        return
    if not evidence:
        if confidence != "low":
            issues.append(
                InsightCardValidationIssue(
                    "insight_no_evidence_requires_low_confidence",
                    "Insight cards without evidence must use low confidence.",
                    f"{path}.confidence",
                )
            )
        if not caveats:
            issues.append(
                InsightCardValidationIssue(
                    "insight_no_evidence_requires_caveat",
                    "Insight cards without evidence must include a caveat.",
                    f"{path}.caveats",
                )
            )
        return
    for evidence_index, item in enumerate(evidence):
        evidence_path = f"{path}.evidence[{evidence_index}]"
        if not isinstance(item, dict):
            issues.append(
                InsightCardValidationIssue(
                    "invalid_insight_evidence_item",
                    "Insight card evidence item must be an object.",
                    evidence_path,
                )
            )
            continue
        if not _has_evidence_content(item):
            issues.append(
                InsightCardValidationIssue(
                    "empty_insight_evidence_item",
                    "Insight card evidence item needs metric_id, description, match_ids, sample_count or value.",
                    evidence_path,
                )
            )


def _has_evidence_content(item: dict[str, Any]) -> bool:
    return any(
        key in item and item[key] not in (None, "", [])
        for key in ("metric_id", "description", "match_ids", "sample_count", "value")
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _opening_death_evidence(
    snapshot: Mapping[str, Any],
    metrics: Mapping[str, Any],
    metric_confidence: Mapping[str, Any],
    rounds: float,
) -> dict[str, Any] | None:
    opening_deaths = _number(metrics.get("opening_deaths"))
    opening_death_rate = _number(metrics.get("opening_death_rate"))
    confidence = _metric_confidence_level(metric_confidence.get("opening_death_rate"))
    if (
        opening_deaths is None
        or opening_death_rate is None
        or opening_deaths < MIN_OPENING_DEATHS
        or opening_death_rate < OPENING_DEATH_RATE_THRESHOLD
        or confidence not in USABLE_INSIGHT_CONFIDENCE
    ):
        return None
    return {
        "metric_id": "opening_death_rate",
        "value": round(opening_death_rate, 3),
        "threshold": OPENING_DEATH_RATE_THRESHOLD,
        "metric_confidence": confidence,
        "sample_count": int(rounds),
        "match_ids": _match_ids(snapshot),
        "source": snapshot.get("source"),
        "description": (
            f"Opening deaths are {int(opening_deaths)} over {int(rounds)} rounds "
            f"({opening_death_rate:.3f}), meeting the {OPENING_DEATH_RATE_THRESHOLD:.3f} insight threshold."
        ),
    }


def _survival_evidence(
    snapshot: Mapping[str, Any],
    metrics: Mapping[str, Any],
    metric_confidence: Mapping[str, Any],
    rounds: float,
) -> dict[str, Any] | None:
    survival_rate = _number(metrics.get("survival_rate"))
    survived_rounds = _number(metrics.get("survived_rounds"))
    confidence = _metric_confidence_level(metric_confidence.get("survival_rate"))
    if (
        survival_rate is None
        or survived_rounds is None
        or survival_rate > SURVIVAL_RATE_THRESHOLD
        or confidence not in USABLE_INSIGHT_CONFIDENCE
    ):
        return None
    deaths = int(rounds - survived_rounds)
    return {
        "metric_id": "survival_rate",
        "value": round(survival_rate, 3),
        "threshold": SURVIVAL_RATE_THRESHOLD,
        "metric_confidence": confidence,
        "sample_count": int(rounds),
        "match_ids": _match_ids(snapshot),
        "source": snapshot.get("source"),
        "description": (
            f"Survival rate is {survival_rate:.3f}: {int(survived_rounds)} survived rounds "
            f"and {deaths} death rounds over {int(rounds)} rounds, at or below the "
            f"{SURVIVAL_RATE_THRESHOLD:.3f} insight threshold."
        ),
    }


def _untraded_death_evidence(
    snapshot: Mapping[str, Any],
    metrics: Mapping[str, Any],
    metric_confidence: Mapping[str, Any],
) -> dict[str, Any] | None:
    untraded_deaths = _number(metrics.get("untraded_deaths"))
    untraded_rate = _number(metrics.get("untraded_death_rate"))
    known_deaths = _number(metrics.get("trade_status_known_deaths"))
    rounds = _number(metrics.get("rounds"))
    confidence = _metric_confidence_level(metric_confidence.get("untraded_death_rate"))
    if (
        untraded_deaths is None
        or untraded_rate is None
        or known_deaths is None
        or untraded_deaths < MIN_UNTRADED_DEATHS
        or known_deaths < MIN_TRADE_STATUS_KNOWN_DEATHS
        or untraded_rate < UNTRADED_DEATH_RATE_THRESHOLD
        or confidence not in USABLE_INSIGHT_CONFIDENCE
    ):
        return None
    evidence = {
        "metric_id": "untraded_death_rate",
        "value": round(untraded_rate, 3),
        "threshold": UNTRADED_DEATH_RATE_THRESHOLD,
        "metric_confidence": confidence,
        "sample_count": int(known_deaths),
        "match_ids": _match_ids(snapshot),
        "source": snapshot.get("source"),
        "count": int(untraded_deaths),
        "known_trade_status_deaths": int(known_deaths),
        "description": (
            f"Untraded deaths are {int(untraded_deaths)} of {int(known_deaths)} deaths with known trade status "
            f"({untraded_rate:.3f}), meeting the {UNTRADED_DEATH_RATE_THRESHOLD:.3f} insight threshold."
        ),
    }
    if rounds is not None:
        evidence["rounds"] = int(rounds)
    return evidence


def _ambiguous_trade_insight_from_snapshot(
    snapshot: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> dict[str, Any] | None:
    ambiguous_deaths = _number(metrics.get("ambiguous_traded_deaths"))
    known_deaths = _number(metrics.get("trade_status_known_deaths")) or 0
    if ambiguous_deaths is None or ambiguous_deaths <= 0:
        return None
    return InsightCard(
        problem="Trade behavior cannot be judged confidently from this match snapshot.",
        evidence=(
            {
                "metric_id": "ambiguous_traded_deaths",
                "value": int(ambiguous_deaths),
                "metric_confidence": "low",
                "sample_count": int(ambiguous_deaths + known_deaths),
                "match_ids": _match_ids(snapshot),
                "source": snapshot.get("source"),
                "description": (
                    f"{int(ambiguous_deaths)} death(s) have ambiguous trade status and were excluded "
                    "from traded/untraded death rates."
                ),
            },
        ),
        confidence="low",
        caveats=tuple(
            _ordered_unique(
                [
                    "Weak or ambiguous trade data cannot support a hard bad-fight or trade recommendation.",
                    "Parser trade evidence depends on side inference and trade-window timing.",
                    *_string_list(snapshot.get("caveats")),
                ]
            )
        ),
        recommended_focus="Collect clearer parser-derived trade-status evidence before coaching trade behavior.",
    ).to_dict()


def _bad_fight_trade_caveats(
    snapshot: Mapping[str, Any],
    metrics: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    confidence: str,
) -> list[str]:
    caveats = [
        "This card is generated only from parser-derived trade/opening metrics persisted in metric snapshots.",
        "Untraded death evidence depends on parser trade window and side inference.",
        "Do not infer exact playlist, mode, positioning, economy, or map-specific causes from this insight.",
    ]
    metric_ids = {str(item.get("metric_id")) for item in evidence}
    if "opening_death_rate" in metric_ids:
        caveats.append("Opening death evidence depends on parser opening duel event order.")
    if (_number(metrics.get("ambiguous_traded_deaths")) or 0) > 0:
        caveats.append("Ambiguous traded deaths were excluded from traded/untraded death rates.")
    if confidence == "medium":
        caveats.append(MEDIUM_CONFIDENCE_CAVEAT)
    caveats.extend(_string_list(snapshot.get("caveats")))
    return _ordered_unique(caveats)


def _survival_opening_caveats(
    snapshot: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    confidence: str,
) -> list[str]:
    caveats = [
        "This card is generated only from persisted metric snapshot values.",
        "Do not infer exact playlist, mode, or map-specific causes from this insight.",
    ]
    metric_ids = {str(item.get("metric_id")) for item in evidence}
    if "opening_death_rate" in metric_ids:
        caveats.append("Opening death evidence depends on parser opening duel event order.")
    if confidence == "medium":
        caveats.append(MEDIUM_CONFIDENCE_CAVEAT)
    caveats.extend(_string_list(snapshot.get("caveats")))
    return _ordered_unique(caveats)


def _card_confidence(evidence: Sequence[Mapping[str, Any]]) -> Literal["medium", "high"]:
    levels = {_metric_confidence_level(item.get("metric_confidence")) for item in evidence}
    return "medium" if "medium" in levels else "high"


def _insight_sort_key(card: Mapping[str, Any]) -> tuple[int, float, int]:
    evidence = card.get("evidence") if isinstance(card.get("evidence"), list) else []
    primary = evidence[0] if evidence and isinstance(evidence[0], Mapping) else {}
    metric_id = primary.get("metric_id")
    value = _number(primary.get("value")) or 0.0
    if metric_id == "untraded_death_rate":
        return (0, -value, -int(primary.get("sample_count") or 0))
    if metric_id == "opening_death_rate":
        return (1, -value, -int(primary.get("sample_count") or 0))
    if metric_id == "survival_rate":
        return (2, value, -int(primary.get("sample_count") or 0))
    if metric_id == "ambiguous_traded_deaths":
        return (3, -value, -int(primary.get("sample_count") or 0))
    return (4, 0.0, 0)


def _metric_confidence_level(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("level")
    if not isinstance(value, str):
        return None
    level = value.strip().lower()
    if level in {"exact", "trusted"}:
        return "high"
    if level in {"partial"}:
        return "medium"
    if level in VALID_INSIGHT_CONFIDENCE:
        return level
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _match_ids(snapshot: Mapping[str, Any]) -> list[int]:
    match_id = snapshot.get("match_id")
    return [match_id] if isinstance(match_id, int) else []


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered
