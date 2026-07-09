from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Match, MetricSnapshot, SteamAccount
from app.services.demo_retention import ARTIFACT_CATEGORY_METRIC_SNAPSHOT, artifact_retention_metadata

MetricPayload = Mapping[str, Any]
AnalysisScopeSource = Literal["steam", "faceit", "unknown"]
AnalysisScopeMode = Literal["personal", "admin_debug_all_snapshots"]


@dataclass(frozen=True)
class MetricSnapshotAnalysisScope:
    match_ids: tuple[int, ...] = ()
    window: Mapping[str, Any] | None = None
    source: AnalysisScopeSource = "unknown"
    owner_user_id: int | None = None
    owner_steam_id: str | None = None
    player_key: str | None = None
    player_name: str | None = None
    player_steamid: str | None = None
    selected_metric_snapshot_ids: tuple[int, ...] = ()
    mode: AnalysisScopeMode = "personal"

    def to_dict(self, *, resolved_metric_snapshot_ids: Sequence[int] | None = None) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "match_ids": list(self.match_ids),
            "window": dict(self.window) if isinstance(self.window, Mapping) else None,
            "source": self.source,
            "owner_user_id": self.owner_user_id,
            "owner_steam_id": self.owner_steam_id,
            "player_identity": {
                "player_key": self.player_key,
                "player_name": self.player_name,
                "player_steamid": self.player_steamid,
            },
            "selected_metric_snapshot_ids": list(self.selected_metric_snapshot_ids),
            "resolved_metric_snapshot_ids": list(resolved_metric_snapshot_ids or ()),
        }


def admin_debug_all_metric_snapshots_scope(
    *,
    match_ids: Sequence[int] | None = None,
    source: AnalysisScopeSource = "unknown",
) -> MetricSnapshotAnalysisScope:
    return MetricSnapshotAnalysisScope(
        match_ids=_int_tuple(match_ids),
        source=_analysis_scope_source(source),
        mode="admin_debug_all_snapshots",
    )


def owner_player_metric_snapshot_scope(db: Session, *, user_id: int | None = None) -> MetricSnapshotAnalysisScope:
    stmt = select(SteamAccount).order_by(SteamAccount.user_id.asc().nulls_last(), SteamAccount.id.asc())
    if user_id is not None:
        stmt = stmt.where(SteamAccount.user_id == user_id)
    account = db.scalar(stmt)
    if account is None:
        return MetricSnapshotAnalysisScope(source="unknown", owner_user_id=user_id)
    return MetricSnapshotAnalysisScope(
        source="steam",
        owner_user_id=account.user_id,
        owner_steam_id=account.steam_id,
        player_key=f"steam:{account.steam_id}",
        player_steamid=account.steam_id,
    )


def default_owner_player_metric_snapshot_scope(db: Session) -> MetricSnapshotAnalysisScope:
    return owner_player_metric_snapshot_scope(db)


def select_metric_snapshots_for_analysis_scope(
    db: Session,
    scope: MetricSnapshotAnalysisScope,
    *,
    limit: int = 100,
) -> list[MetricSnapshot]:
    if limit <= 0:
        return []
    _validate_analysis_scope(scope)
    stmt = select(MetricSnapshot).order_by(MetricSnapshot.created_at.desc(), MetricSnapshot.id.desc()).limit(limit)
    if scope.match_ids:
        stmt = stmt.where(MetricSnapshot.match_id.in_(scope.match_ids))
    if scope.selected_metric_snapshot_ids:
        stmt = stmt.where(MetricSnapshot.id.in_(scope.selected_metric_snapshot_ids))
    if scope.mode == "personal":
        identity_filters = []
        if scope.player_key:
            identity_filters.append(MetricSnapshot.player_key == scope.player_key)
        if scope.player_steamid:
            identity_filters.append(MetricSnapshot.player_steamid == scope.player_steamid)
        if scope.player_name:
            identity_filters.append(MetricSnapshot.player_name == scope.player_name)
        if not identity_filters:
            return []
        stmt = stmt.where(*identity_filters)
    return list(db.scalars(stmt).all())


def create_metric_snapshot(
    db: Session,
    *,
    match_id: int,
    player_key: str,
    source: str,
    metrics: MetricPayload,
    confidence_baseline: MetricPayload,
    player_name: str | None = None,
    player_steamid: str | None = None,
    source_parser_artifact_id: int | None = None,
    source_event_set_id: str | None = None,
    caveats: Sequence[str] | None = None,
    metadata: MetricPayload | None = None,
) -> MetricSnapshot:
    _validate_match(db, match_id)
    snapshot = MetricSnapshot(
        match_id=match_id,
        player_key=_required_text(player_key, "player_key"),
        player_name=_optional_text(player_name),
        player_steamid=_optional_text(player_steamid),
        source=_required_text(source, "source"),
        source_parser_artifact_id=source_parser_artifact_id,
        source_event_set_id=_optional_text(source_event_set_id),
        metrics_json=_dumps_dict(metrics, "metrics"),
        confidence_baseline_json=_dumps_dict(confidence_baseline, "confidence_baseline"),
        caveats_json=_dumps_list(caveats or []),
        metadata_json=_dumps_dict(_metadata_with_retention(metadata), "metadata"),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_metric_snapshot(db: Session, snapshot_id: int) -> MetricSnapshot | None:
    return db.get(MetricSnapshot, snapshot_id)


def find_metric_snapshot(db: Session, *, match_id: int, player_key: str, source: str) -> MetricSnapshot | None:
    return db.scalar(
        select(MetricSnapshot)
        .where(MetricSnapshot.match_id == match_id)
        .where(MetricSnapshot.player_key == player_key)
        .where(MetricSnapshot.source == source)
    )


def list_metric_snapshots(
    db: Session,
    *,
    match_id: int | None = None,
    player_key: str | None = None,
    source: str | None = None,
    limit: int = 100,
) -> list[MetricSnapshot]:
    stmt = select(MetricSnapshot).order_by(MetricSnapshot.created_at.desc(), MetricSnapshot.id.desc()).limit(limit)
    if match_id is not None:
        stmt = stmt.where(MetricSnapshot.match_id == match_id)
    if player_key is not None:
        stmt = stmt.where(MetricSnapshot.player_key == player_key)
    if source is not None:
        stmt = stmt.where(MetricSnapshot.source == source)
    return list(db.scalars(stmt).all())


def update_metric_snapshot(
    db: Session,
    snapshot: MetricSnapshot,
    *,
    metrics: MetricPayload | None = None,
    confidence_baseline: MetricPayload | None = None,
    source_parser_artifact_id: int | None = None,
    source_event_set_id: str | None = None,
    caveats: Sequence[str] | None = None,
    metadata: MetricPayload | None = None,
) -> MetricSnapshot:
    if metrics is not None:
        snapshot.metrics_json = _dumps_dict(metrics, "metrics")
    if confidence_baseline is not None:
        snapshot.confidence_baseline_json = _dumps_dict(confidence_baseline, "confidence_baseline")
    if source_parser_artifact_id is not None:
        snapshot.source_parser_artifact_id = source_parser_artifact_id
    if source_event_set_id is not None:
        snapshot.source_event_set_id = _optional_text(source_event_set_id)
    if caveats is not None:
        snapshot.caveats_json = _dumps_list(caveats)
    if metadata is not None:
        snapshot.metadata_json = _dumps_dict(_metadata_with_retention(metadata), "metadata")
    snapshot.updated_at = _now()
    db.commit()
    db.refresh(snapshot)
    return snapshot


def upsert_metric_snapshot(
    db: Session,
    *,
    match_id: int,
    player_key: str,
    source: str,
    metrics: MetricPayload,
    confidence_baseline: MetricPayload,
    player_name: str | None = None,
    player_steamid: str | None = None,
    source_parser_artifact_id: int | None = None,
    source_event_set_id: str | None = None,
    caveats: Sequence[str] | None = None,
    metadata: MetricPayload | None = None,
) -> MetricSnapshot:
    existing = find_metric_snapshot(db, match_id=match_id, player_key=player_key, source=source)
    if existing is None:
        return create_metric_snapshot(
            db,
            match_id=match_id,
            player_key=player_key,
            source=source,
            metrics=metrics,
            confidence_baseline=confidence_baseline,
            player_name=player_name,
            player_steamid=player_steamid,
            source_parser_artifact_id=source_parser_artifact_id,
            source_event_set_id=source_event_set_id,
            caveats=caveats,
            metadata=metadata,
        )
    existing.player_name = _optional_text(player_name) if player_name is not None else existing.player_name
    existing.player_steamid = _optional_text(player_steamid) if player_steamid is not None else existing.player_steamid
    return update_metric_snapshot(
        db,
        existing,
        metrics=metrics,
        confidence_baseline=confidence_baseline,
        source_parser_artifact_id=source_parser_artifact_id,
        source_event_set_id=source_event_set_id,
        caveats=caveats,
        metadata=metadata,
    )


def process_persisted_match_metric_snapshots_for_coach_loop(
    db: Session,
    *,
    user_id: int,
    match_id: int,
    metric_snapshots: Sequence[MetricSnapshot],
    evaluation_window_start: datetime | None = None,
    evaluation_window_end: datetime | None = None,
) -> dict[str, Any]:
    mismatched = [snapshot.id for snapshot in metric_snapshots if snapshot.match_id != match_id]
    if mismatched:
        raise ValueError("Post-metrics coach loop received snapshots for a different match.")
    metric_snapshot_ids = [snapshot.id for snapshot in metric_snapshots]
    from app.services.ai_coach import process_owner_match_metric_snapshots_for_coach_loop

    return process_owner_match_metric_snapshots_for_coach_loop(
        db,
        user_id=user_id,
        match_id=match_id,
        metric_snapshot_ids=metric_snapshot_ids,
        evaluation_window_start=evaluation_window_start,
        evaluation_window_end=evaluation_window_end,
    )


def metric_snapshot_payload(snapshot: MetricSnapshot) -> dict[str, Any]:
    return {
        "id": snapshot.id,
        "match_id": snapshot.match_id,
        "player_key": snapshot.player_key,
        "player_name": snapshot.player_name,
        "player_steamid": snapshot.player_steamid,
        "source": snapshot.source,
        "source_parser_artifact_id": snapshot.source_parser_artifact_id,
        "source_event_set_id": snapshot.source_event_set_id,
        "metrics": _loads(snapshot.metrics_json, fallback={}),
        "confidence_baseline": _loads(snapshot.confidence_baseline_json, fallback={}),
        "caveats": _loads(snapshot.caveats_json, fallback=[]),
        "metadata": _loads(snapshot.metadata_json, fallback={}),
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
    }


def _validate_analysis_scope(scope: MetricSnapshotAnalysisScope) -> None:
    if scope.source not in {"steam", "faceit", "unknown"}:
        raise ValueError("analysis scope source must be steam, faceit or unknown")
    if scope.mode not in {"personal", "admin_debug_all_snapshots"}:
        raise ValueError("analysis scope mode is invalid")


def _analysis_scope_source(source: str) -> AnalysisScopeSource:
    normalized = str(source).strip().lower()
    if normalized not in {"steam", "faceit", "unknown"}:
        raise ValueError("analysis scope source must be steam, faceit or unknown")
    return cast(AnalysisScopeSource, normalized)


def _int_tuple(values: Sequence[int] | None) -> tuple[int, ...]:
    return tuple(int(value) for value in (values or ()))


def _validate_match(db: Session, match_id: int) -> None:
    if db.get(Match, match_id) is None:
        raise ValueError(f"Metric snapshot match_id does not exist: {match_id}")


def _required_text(value: str, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dumps_dict(value: MetricPayload, field: str) -> str:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, default=str)


def _metadata_with_retention(metadata: MetricPayload | None) -> dict[str, Any]:
    value = dict(metadata or {})
    value.setdefault("artifact_retention", artifact_retention_metadata(ARTIFACT_CATEGORY_METRIC_SNAPSHOT))
    return value


def _dumps_list(value: Sequence[str]) -> str:
    if isinstance(value, str):
        raise ValueError("caveats must be a sequence of strings")
    return json.dumps([str(item) for item in value], ensure_ascii=False, sort_keys=True, default=str)


def _loads(value: str, *, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
