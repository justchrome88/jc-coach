from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DownstreamDisposition:
    object_type: str
    object_id: int
    current_state: str
    m03_state: str
    dependency_snapshot_ids: tuple[int, ...]
    action: str
    idempotency_key: str


MATCH_124_DISPOSITIONS = (
    DownstreamDisposition(
        "metric_snapshot", 1138, "legacy_unverified", "superseded", (),
        "append core 2.0.0", "snapshot:124:core:2.0.0",
    ),
    DownstreamDisposition(
        "metric_snapshot", 1149, "legacy_unverified", "superseded", (),
        "append utility 2.0.0", "snapshot:124:utility:2.0.0",
    ),
    DownstreamDisposition(
        "analysis_run", 59, "accepted_historical", "superseded", (1138, 1149),
        "recompute from accepted snapshots", "analysis:124:metric-contract:2.0.0",
    ),
    DownstreamDisposition(
        "coach_hypothesis", 110, "candidate", "quarantined", (1138,),
        "recompute only after participation evidence", "hypothesis:110:metric-contract:2.0.0",
    ),
    DownstreamDisposition(
        "coach_hypothesis", 111, "candidate", "superseded", (1149,),
        "recompute after utility relation validation", "hypothesis:111:metric-contract:2.0.0",
    ),
    DownstreamDisposition(
        "coach_mission", 3, "active", "quarantined", (1149,),
        "retain; prevent duplicate active mission", "mission:3:metric-contract:2.0.0",
    ),
    DownstreamDisposition(
        "mission_progress_evaluation", 9, "insufficient_data", "superseded", (1138, 1149),
        "append affected reevaluation only", "progress:9:metric-contract:2.0.0",
    ),
)


def match_124_downstream_plan() -> list[dict[str, Any]]:
    return [asdict(item) for item in MATCH_124_DISPOSITIONS]


def stale_evidence_marker(payload: Mapping[str, Any], disposition: DownstreamDisposition) -> dict[str, Any]:
    marked = dict(payload)
    marked["metric_assurance"] = {
        "state": disposition.m03_state,
        "dependency_snapshot_ids": list(disposition.dependency_snapshot_ids),
        "action": disposition.action,
        "idempotency_key": disposition.idempotency_key,
    }
    return marked
