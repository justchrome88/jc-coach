"""Mission contracts, immutable primitives, and lifecycle constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MISSION_PROGRESS_STATUSES = {
    "improving",
    "unchanged",
    "regressing",
    "insufficient_data",
    "not_following",
}

INSIGHT_CONFIDENCE_SCORES = {
    "low": 0.25,
    "medium": 0.6,
    "high": 0.9,
}

MISSION_STATUSES = {"draft", "active", "completed", "failed", "paused", "cancelled", "expired"}

ACTIVE_MISSION_STATUSES = {"active"}

TERMINAL_MISSION_STATUSES = {"completed", "failed", "cancelled", "expired"}

MISSION_TRANSITIONS = {
    "draft": {"active", "cancelled"},
    "active": {"paused", "completed", "failed", "cancelled", "expired"},
    "paused": {"active", "cancelled", "expired"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
    "expired": set(),
}

MISSION_DUPLICATE_POLICIES = {"reject", "replace", "allow"}

CRITERIA_ROLES = {"primary", "secondary", "guardrail"}

CRITERIA_DIRECTIONS = {
    "higher_is_better",
    "lower_is_better",
    "stay_above",
    "stay_below",
    "not_drop_more_than",
    "improve_or_same",
}

MISSION_ELIGIBLE_CONFIDENCE_LEVELS = {"medium", "high"}

MISSION_PAYLOAD_SCHEMA_VERSION = "coach-mission-payload-v1"

REQUIRED_MISSION_PAYLOAD_FIELDS = ("title", "goal", "rules", "duration", "success_metric", "failure_condition")

SURVIVAL_OPENING_MISSION_METRICS = {"opening_death_rate", "survival_rate"}

BAD_FIGHT_TRADE_MISSION_METRICS = {"untraded_death_rate"}

EFFECTIVE_UTILITY_METRIC = "effective_enemy_utility_damage"

UTILITY_VALUE_MISSION_METRICS = {
    EFFECTIVE_UTILITY_METRIC,
    "utility_damage_per_round",
    "enemy_he_damage",
    "enemy_fire_damage",
    "effective_enemy_flash_duration",
}

UTILITY_NEGATIVE_TREND_MATERIALITY = 0.10

MAX_UTILITY_TREND_SUPPORTED_MATCHES = 30

MIN_UTILITY_TREND_SUPPORTED_MATCHES = 10

MIN_UTILITY_TREND_SEGMENT_MATCHES = 5

ROLLING_MISSION_WINDOW_TYPES = {"last_30", "last_60", "custom_match_set"}

ROLLING_MISSION_METRICS = {
    "adr",
    "deaths",
    "kast",
    "kills_per_round",
    "survival_rate",
    "opening_death_rate",
    "opening_duel_win_rate",
    "untraded_death_rate",
    "traded_death_rate",
    EFFECTIVE_UTILITY_METRIC,
}

MIN_ROLLING_WINDOW_MATCHES = 3

MIN_ROLLING_WINDOW_ROUNDS = 8

CORE_COMBAT_SNAPSHOT_SOURCE = "coach_metric_performance"

UTILITY_SNAPSHOT_SOURCE = "coach_metric_utility"

UTILITY_SNAPSHOT_METRICS = {
    "enemies_effectively_flashed",
    "effective_enemy_flash_duration",
    "flash_assists",
    "flash_detonations",
    "enemy_he_damage",
    "he_detonations",
    "enemy_fire_damage",
    "fire_grenade_detonations",
    "smoke_detonations",
    "smokes_used",
    EFFECTIVE_UTILITY_METRIC,
    "utility_damage_per_round",
}

@dataclass(frozen=True)
class MissionPayload:
    title: str
    goal: str
    rules: tuple[str, ...]
    duration: dict[str, Any]
    success_metric: dict[str, Any]
    failure_condition: dict[str, Any]
    linked_insight: dict[str, Any]
    schema_version: str = MISSION_PAYLOAD_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "goal": self.goal,
            "rules": list(self.rules),
            "duration": dict(self.duration),
            "success_metric": dict(self.success_metric),
            "failure_condition": dict(self.failure_condition),
            "linked_insight": dict(self.linked_insight),
        }

@dataclass(frozen=True)
class MissionPayloadValidationIssue:
    code: str
    message: str
    path: str

@dataclass(frozen=True)
class UtilityTrendEvidence:
    evidence_available: bool
    deficiency_detected: bool
    mission_ready: bool
    supported_match_ids: tuple[int, ...]
    supported_snapshot_ids: tuple[int, ...]
    ignored_oldest_match_ids: tuple[int, ...]
    baseline_match_ids: tuple[int, ...]
    recent_match_ids: tuple[int, ...]
    baseline_snapshot_ids: tuple[int, ...]
    recent_snapshot_ids: tuple[int, ...]
    baseline_value: float | None
    recent_value: float | None
    absolute_change: float | None
    absolute_gap: float
    relative_change: float | None
    relative_drop: float
    severity: float
    confidence: str
    source: str
    caveats: tuple[str, ...]
    materiality_threshold: float
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_available": self.evidence_available,
            "deficiency_detected": self.deficiency_detected,
            "mission_ready": self.mission_ready,
            "supported_match_ids": list(self.supported_match_ids),
            "supported_snapshot_ids": list(self.supported_snapshot_ids),
            "supported_match_count": len(self.supported_match_ids),
            "ignored_oldest_match_ids": list(self.ignored_oldest_match_ids),
            "baseline_match_ids": list(self.baseline_match_ids),
            "recent_match_ids": list(self.recent_match_ids),
            "baseline_snapshot_ids": list(self.baseline_snapshot_ids),
            "recent_snapshot_ids": list(self.recent_snapshot_ids),
            "baseline_value": self.baseline_value,
            "recent_value": self.recent_value,
            "absolute_change": self.absolute_change,
            "absolute_gap": self.absolute_gap,
            "relative_change": self.relative_change,
            "relative_drop": self.relative_drop,
            "severity": self.severity,
            "confidence": self.confidence,
            "source": self.source,
            "caveats": list(self.caveats),
            "materiality_threshold": self.materiality_threshold,
            "reason_codes": list(self.reason_codes),
        }

@dataclass(frozen=True)
class RollingMissionWindow:
    user_id: int
    owner_steam_id: str
    window_type: str
    source: str
    match_ids: tuple[int, ...]
    metric_snapshot_ids: tuple[int, ...]
    metrics: dict[str, float]
    metric_samples: dict[str, dict[str, Any]]
    sample_matches: int
    sample_rounds: int
    confidence: str
    confidence_score: float
    caveats: tuple[str, ...]
    utility_trend: UtilityTrendEvidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "owner_steam_id": self.owner_steam_id,
            "window_type": self.window_type,
            "source": self.source,
            "match_ids": list(self.match_ids),
            "metric_snapshot_ids": list(self.metric_snapshot_ids),
            "metrics": dict(self.metrics),
            "metric_samples": {key: dict(value) for key, value in self.metric_samples.items()},
            "sample_matches": self.sample_matches,
            "sample_rounds": self.sample_rounds,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "caveats": list(self.caveats),
            "utility_trend": self.utility_trend.to_dict(),
        }

@dataclass(frozen=True)
class RollingMissionCandidate:
    rank: int
    candidate_id: str
    family: str
    primary_metric: str
    severity: float
    confidence_score: float
    sample_size: int
    suppressed_by_active_mission: bool
    suppression_reason: str | None
    explanation: str
    insight_card: dict[str, Any]
    mission_payload: dict[str, Any]
    window_evidence: dict[str, Any]
    suppression_key: dict[str, Any]
    suppression_reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "candidate_id": self.candidate_id,
            "family": self.family,
            "primary_metric": self.primary_metric,
            "severity": self.severity,
            "confidence_score": self.confidence_score,
            "sample_size": self.sample_size,
            "suppressed_by_active_mission": self.suppressed_by_active_mission,
            "suppression_reason": self.suppression_reason,
            "explanation": self.explanation,
            "insight_card": dict(self.insight_card),
            "mission_payload": dict(self.mission_payload),
            "window_evidence": dict(self.window_evidence),
            "suppression_key": dict(self.suppression_key),
            "suppression_reason_codes": list(self.suppression_reason_codes),
        }

@dataclass(frozen=True)
class MissionSuppressionDecision:
    suppressed: bool
    reason: str | None
    reason_codes: tuple[str, ...]
    active_mission_id: int | None
    active_mission_title: str | None
    active_mission_status: str | None
    active_mission_progress_status: str | None
    key: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "suppressed": self.suppressed,
            "reason": self.reason,
            "reason_codes": list(self.reason_codes),
            "active_mission_id": self.active_mission_id,
            "active_mission_title": self.active_mission_title,
            "active_mission_status": self.active_mission_status,
            "active_mission_progress_status": self.active_mission_progress_status,
            "key": dict(self.key),
        }

__all__ = (
    'ACTIVE_MISSION_STATUSES',
    'BAD_FIGHT_TRADE_MISSION_METRICS',
    'CORE_COMBAT_SNAPSHOT_SOURCE',
    'CRITERIA_DIRECTIONS',
    'CRITERIA_ROLES',
    'EFFECTIVE_UTILITY_METRIC',
    'INSIGHT_CONFIDENCE_SCORES',
    'MAX_UTILITY_TREND_SUPPORTED_MATCHES',
    'MIN_ROLLING_WINDOW_MATCHES',
    'MIN_ROLLING_WINDOW_ROUNDS',
    'MIN_UTILITY_TREND_SEGMENT_MATCHES',
    'MIN_UTILITY_TREND_SUPPORTED_MATCHES',
    'MISSION_DUPLICATE_POLICIES',
    'MISSION_ELIGIBLE_CONFIDENCE_LEVELS',
    'MISSION_PAYLOAD_SCHEMA_VERSION',
    'MISSION_PROGRESS_STATUSES',
    'MISSION_STATUSES',
    'MISSION_TRANSITIONS',
    'REQUIRED_MISSION_PAYLOAD_FIELDS',
    'ROLLING_MISSION_METRICS',
    'ROLLING_MISSION_WINDOW_TYPES',
    'SURVIVAL_OPENING_MISSION_METRICS',
    'TERMINAL_MISSION_STATUSES',
    'UTILITY_NEGATIVE_TREND_MATERIALITY',
    'UTILITY_SNAPSHOT_METRICS',
    'UTILITY_SNAPSHOT_SOURCE',
    'UTILITY_VALUE_MISSION_METRICS',
    'MissionPayload',
    'MissionPayloadValidationIssue',
    'MissionSuppressionDecision',
    'RollingMissionCandidate',
    'RollingMissionWindow',
    'UtilityTrendEvidence',
)
