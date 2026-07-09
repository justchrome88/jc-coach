from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DemoParseArtifact, Match, MetricSnapshot
from app.services.core_combat_metrics import CORE_COMBAT_SNAPSHOT_SOURCE, calculate_and_store_core_combat_metrics
from app.services.metric_snapshots import (
    list_metric_snapshots,
    metric_snapshot_payload,
    owner_player_metric_snapshot_scope,
    process_persisted_match_metric_snapshots_for_coach_loop,
)
from app.services.mission_domain import list_active_coach_missions
from app.services.parser_artifact_reader import ParserArtifactReaderError, normalized_events_from_parser_artifact
from app.services.utility_metrics import UTILITY_SNAPSHOT_SOURCE, calculate_and_store_utility_metrics

MATCH_PROCESSING_BOUNDARY = "owner_match_after_parser_artifact"
MATCH_PROCESSING_VERSION = "owner-match-processing-orchestrator-v1"
ACCEPTED_PARSER_ARTIFACT_STATUSES = {"completed", "accepted", "success"}


def process_owner_match_after_parser_artifact(
    db: Session,
    *,
    user_id: int,
    match_id: int,
    parser_artifact_id: int | None = None,
    evaluation_window_start: datetime | None = None,
    evaluation_window_end: datetime | None = None,
    source_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Process one owner match after parser handoff has produced an artifact."""
    owner_scope = owner_player_metric_snapshot_scope(db, user_id=user_id)
    if owner_scope.owner_user_id is None or not owner_scope.player_key:
        return _blocked_summary(
            user_id=user_id,
            match_id=match_id,
            issue="owner_scope_unavailable",
            caveat="Owner match processing requires a linked owner Steam account.",
        )

    match = db.get(Match, match_id)
    if match is None:
        return _blocked_summary(
            user_id=user_id,
            match_id=match_id,
            owner_steam_id=owner_scope.owner_steam_id,
            issue="match_not_found",
            caveat=f"Match does not exist: {match_id}",
        )

    artifact = _resolve_parser_artifact(db, match_id=match.id, parser_artifact_id=parser_artifact_id)
    if artifact is None:
        return _blocked_summary(
            user_id=user_id,
            match_id=match.id,
            owner_steam_id=owner_scope.owner_steam_id,
            issue="parser_artifact_missing",
            caveat="Accepted parser artifact data is required before match processing can run.",
        )
    if artifact.status not in ACCEPTED_PARSER_ARTIFACT_STATUSES:
        return _blocked_summary(
            user_id=user_id,
            match_id=match.id,
            owner_steam_id=owner_scope.owner_steam_id,
            parser_artifact=_parser_artifact_summary(artifact),
            issue="parser_artifact_not_accepted",
            caveat=f"Parser artifact status is not accepted for processing: {artifact.status}",
        )

    try:
        normalized_events = normalized_events_from_parser_artifact(artifact)
    except ParserArtifactReaderError as exc:
        return _blocked_summary(
            user_id=user_id,
            match_id=match.id,
            owner_steam_id=owner_scope.owner_steam_id,
            parser_artifact=_parser_artifact_summary(artifact),
            issue="parser_artifact_reader_failed",
            caveat=str(exc),
            reader_issues=exc.issues,
        )
    if not normalized_events:
        return _blocked_summary(
            user_id=user_id,
            match_id=match.id,
            owner_steam_id=owner_scope.owner_steam_id,
            parser_artifact=_parser_artifact_summary(artifact),
            status="insufficient_input",
            issue="normalized_events_empty",
            caveat="Parser artifact did not produce normalized events for metric snapshot generation.",
        )

    source_event_set_id = _source_event_set_id(artifact, normalized_events)
    metric_results = [
        _store_metric_source(
            db,
            match_id=match.id,
            source=CORE_COMBAT_SNAPSHOT_SOURCE,
            store=lambda: calculate_and_store_core_combat_metrics(
                db,
                match_id=match.id,
                normalized_events=normalized_events,
                source_parser_artifact_id=artifact.id,
                source_event_set_id=source_event_set_id,
            ),
        ),
        _store_metric_source(
            db,
            match_id=match.id,
            source=UTILITY_SNAPSHOT_SOURCE,
            store=lambda: calculate_and_store_utility_metrics(
                db,
                match_id=match.id,
                normalized_events=normalized_events,
                source_parser_artifact_id=artifact.id,
                source_event_set_id=source_event_set_id,
            ),
        ),
    ]
    persisted_snapshots = _ordered_unique_snapshots(
        snapshot for result in metric_results for snapshot in result["snapshots"]
    )
    active_mission_ids = [
        mission.id for mission in list_active_coach_missions(db, user_id=owner_scope.owner_user_id)
    ]
    coach_result = process_persisted_match_metric_snapshots_for_coach_loop(
        db,
        user_id=owner_scope.owner_user_id,
        match_id=match.id,
        metric_snapshots=persisted_snapshots,
        evaluation_window_start=evaluation_window_start,
        evaluation_window_end=evaluation_window_end,
    )
    analysis_run_id = coach_result.get("analysis_run_id")
    reused_analysis_run = bool((coach_result.get("idempotency") or {}).get("reused_analysis_run"))
    hypothesis_ids = _int_list(coach_result.get("coach_hypothesis_ids"))
    mission_statuses = [
        {
            "mission_id": summary.get("mission_id"),
            "evaluation_id": summary.get("evaluation_id"),
            "status": summary.get("status"),
        }
        for summary in coach_result.get("mission_status_summaries") or []
        if isinstance(summary, Mapping)
    ]

    all_snapshot_ids = _ordered_unique_ints(snapshot.id for snapshot in persisted_snapshots)
    created_snapshot_ids = _ordered_unique_ints(
        snapshot_id for result in metric_results for snapshot_id in result["created_snapshot_ids"]
    )
    reused_snapshot_ids = _ordered_unique_ints(
        snapshot_id for result in metric_results for snapshot_id in result["reused_snapshot_ids"]
    )
    return {
        "backend_boundary": MATCH_PROCESSING_BOUNDARY,
        "version": MATCH_PROCESSING_VERSION,
        "status": "processed",
        "user_id": owner_scope.owner_user_id,
        "owner_steam_id": owner_scope.owner_steam_id,
        "match_id": match.id,
        "parser_artifact": _parser_artifact_summary(artifact),
        "source_event_set_id": source_event_set_id,
        "normalized_event_count": len(normalized_events),
        "metric_snapshot_ids": {
            "all": all_snapshot_ids,
            "created": created_snapshot_ids,
            "reused": reused_snapshot_ids,
            "by_source": {
                result["source"]: {
                    "all": result["snapshot_ids"],
                    "created": result["created_snapshot_ids"],
                    "reused": result["reused_snapshot_ids"],
                }
                for result in metric_results
            },
        },
        "owner_selected_metric_snapshot_ids": _int_list(coach_result.get("selected_metric_snapshot_ids")),
        "analysis_run": {
            "id": analysis_run_id,
            "created": analysis_run_id if analysis_run_id is not None and not reused_analysis_run else None,
            "reused": analysis_run_id if analysis_run_id is not None and reused_analysis_run else None,
        },
        "coach_hypothesis_ids": {
            "all": hypothesis_ids,
            "created": [] if reused_analysis_run else hypothesis_ids,
            "reused": hypothesis_ids if reused_analysis_run else [],
        },
        "active_mission_ids": active_mission_ids,
        "mission_progress_evaluation_ids": _int_list(coach_result.get("mission_progress_evaluation_ids")),
        "mission_progress_statuses": mission_statuses,
        "mission_status_summaries": coach_result.get("mission_status_summaries") or [],
        "post_metrics_coach_loop": coach_result,
        "idempotency": {
            "source_event_set_id": source_event_set_id,
            "metric_snapshot_ids_created": created_snapshot_ids,
            "metric_snapshot_ids_reused": reused_snapshot_ids,
            "post_metrics_coach_loop": coach_result.get("idempotency") or {},
        },
        "caveats": _summary_caveats(persisted_snapshots),
        "source_metadata": dict(source_metadata or {}),
    }


def _resolve_parser_artifact(
    db: Session,
    *,
    match_id: int,
    parser_artifact_id: int | None,
) -> DemoParseArtifact | None:
    if parser_artifact_id is not None:
        artifact = db.get(DemoParseArtifact, parser_artifact_id)
        if artifact is None or artifact.match_id != match_id:
            return None
        return artifact
    return db.scalar(
        select(DemoParseArtifact)
        .where(DemoParseArtifact.match_id == match_id)
        .order_by(DemoParseArtifact.parsed_at.desc(), DemoParseArtifact.id.desc())
    )


def _store_metric_source(
    db: Session,
    *,
    match_id: int,
    source: str,
    store: Callable[[], Sequence[MetricSnapshot]],
) -> dict[str, Any]:
    existing_ids = {
        snapshot.id for snapshot in list_metric_snapshots(db, match_id=match_id, source=source, limit=10_000)
    }
    snapshots = list(store())
    snapshot_ids = _ordered_unique_ints(snapshot.id for snapshot in snapshots)
    return {
        "source": source,
        "snapshots": snapshots,
        "snapshot_ids": snapshot_ids,
        "created_snapshot_ids": [snapshot_id for snapshot_id in snapshot_ids if snapshot_id not in existing_ids],
        "reused_snapshot_ids": [snapshot_id for snapshot_id in snapshot_ids if snapshot_id in existing_ids],
    }


def _source_event_set_id(artifact: DemoParseArtifact, normalized_events: Sequence[Mapping[str, Any]]) -> str:
    event_hash = hashlib.sha256(
        json.dumps(list(normalized_events), ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return f"parser-artifact:{artifact.id}:events:{event_hash}"


def _parser_artifact_summary(artifact: DemoParseArtifact) -> dict[str, Any]:
    return {
        "id": artifact.id,
        "match_id": artifact.match_id,
        "status": artifact.status,
        "parser_name": artifact.parser_name,
        "parser_version": artifact.parser_version,
        "payload_version": artifact.payload_version,
        "source_demo_file": artifact.source_demo_file,
        "demo_sha1": artifact.demo_sha1,
    }


def _blocked_summary(
    *,
    user_id: int,
    match_id: int,
    issue: str,
    caveat: str,
    owner_steam_id: str | None = None,
    parser_artifact: Mapping[str, Any] | None = None,
    status: str = "blocked",
    reader_issues: Sequence[str] | None = None,
) -> dict[str, Any]:
    return {
        "backend_boundary": MATCH_PROCESSING_BOUNDARY,
        "version": MATCH_PROCESSING_VERSION,
        "status": status,
        "user_id": user_id,
        "owner_steam_id": owner_steam_id,
        "match_id": match_id,
        "parser_artifact": dict(parser_artifact) if parser_artifact else None,
        "issue": issue,
        "reader_issues": list(reader_issues or []),
        "metric_snapshot_ids": {"all": [], "created": [], "reused": [], "by_source": {}},
        "owner_selected_metric_snapshot_ids": [],
        "analysis_run": {"id": None, "created": None, "reused": None},
        "coach_hypothesis_ids": {"all": [], "created": [], "reused": []},
        "active_mission_ids": [],
        "mission_progress_evaluation_ids": [],
        "mission_progress_statuses": [],
        "mission_status_summaries": [],
        "caveats": [caveat],
    }


def _summary_caveats(snapshots: Sequence[MetricSnapshot]) -> list[str]:
    caveats = [
        caveat
        for snapshot in snapshots
        for caveat in metric_snapshot_payload(snapshot).get("caveats", [])
        if isinstance(caveat, str) and caveat.strip()
    ]
    return _ordered_unique_strings(caveats)


def _ordered_unique_snapshots(snapshots: Sequence[MetricSnapshot]) -> list[MetricSnapshot]:
    output: list[MetricSnapshot] = []
    seen: set[int] = set()
    for snapshot in snapshots:
        if snapshot.id in seen:
            continue
        seen.add(snapshot.id)
        output.append(snapshot)
    return output


def _ordered_unique_ints(values: Sequence[int | None]) -> list[int]:
    output: list[int] = []
    seen: set[int] = set()
    for value in values:
        if value is None:
            continue
        item = int(value)
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    output: list[int] = []
    for item in value:
        try:
            output.append(int(item))
        except (TypeError, ValueError):
            continue
    return output


def _ordered_unique_strings(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
