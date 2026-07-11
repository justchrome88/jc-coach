"""Owner-sync immutable contracts and constants."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.db.models import (
    DemoParseArtifact,
    Match,
    MetricSnapshot,
    SteamAccount,
    User,
)

OWNER_COACH_SYNC_RESULT_SCHEMA_VERSION = "owner-coach-sync-result-v1"

OWNER_COACH_SYNC_OPERATION = "owner_coach_sync"

OWNER_COACH_SYNC_LOCK_TTL = timedelta(minutes=30)

DEFAULT_MAX_NEW_MATCHES = 1

MAX_NEW_MATCHES = 50

MAX_NEW_DEMO_ACQUISITIONS_PER_SYNC = 1

MAX_RETRYABLE_ATTEMPTS = 2

RETRY_COOLDOWN = timedelta(minutes=15)

METRIC_SNAPSHOT_SOURCES = frozenset({"core_combat_metrics", "utility_metrics"})

INTERNAL_CLASSIFICATIONS = (
    "fresh_actionable",
    "incomplete_resumable",
    "already_complete",
    "legacy_stale_pending",
    "unavailable_retryable",
    "unavailable_terminal",
    "failed_retryable",
    "failed_terminal",
    "cross_owner_denied",
    "invalid_identity",
)

_DURABLE_ENTITY_KEYS = (
    "import_jobs",
    "matches",
    "parser_artifacts",
    "metric_snapshots",
    "analysis_runs",
    "hypotheses",
    "missions",
    "criteria",
    "progress_evaluations",
)

_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)

logger = logging.getLogger(__name__)

@dataclass
class _OwnerContext:
    user: User
    steam_account: SteamAccount

@dataclass
class _OwnerSyncLock:
    key: str
    token: str
    value: str
    acquired_at: datetime
    expires_at: datetime
    recovered_stale: bool = False

@dataclass
class _Candidate:
    source_match: Match
    demo_match: Match | None
    sharecode: str | None
    classification: str
    reason_code: str
    artifact: DemoParseArtifact | None
    snapshots: list[MetricSnapshot]
    internal_classification: str
    actionable: bool
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    next_eligible_at: datetime | None = None

@dataclass(frozen=True)
class _DiscoveryBoundary:
    source: str
    account_last_sync_at: datetime | None
    cursor: str | None
    accepted_positions: dict[str, int]
    latest_completed_position: int | None

class _MatchPhaseError(RuntimeError):
    def __init__(
        self,
        *,
        phase: str,
        reason_code: str,
        safe_message: str,
        retryable: bool,
        exception_class: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.phase = phase
        self.reason_code = reason_code
        self.safe_message = safe_message
        self.retryable = retryable
        self.exception_class = exception_class

__all__ = (
)
