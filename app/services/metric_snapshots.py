from __future__ import annotations

import hashlib
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
VALIDATION_STATES = {"pending", "validated", "rejected", "quarantined", "superseded", "legacy_unverified"}
TRUSTED_VALIDATION_STATES = {"validated"}
ACCEPTED_SEMANTIC_VERSIONS = ("3.0.0",)


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
    semantic_versions: tuple[str, ...] = ()
    validation_statuses: tuple[str, ...] = ("validated",)

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
            "semantic_versions": list(self.semantic_versions),
            "validation_statuses": list(self.validation_statuses),
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
        validation_statuses=(),
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
        semantic_versions=ACCEPTED_SEMANTIC_VERSIONS,
        validation_statuses=("validated",),
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
    if scope.semantic_versions:
        stmt = stmt.where(MetricSnapshot.semantic_version.in_(scope.semantic_versions))
    if scope.validation_statuses:
        stmt = stmt.where(MetricSnapshot.validation_status.in_(scope.validation_statuses))
    if scope.mode == "personal":
        if scope.owner_user_id is None:
            return []
        stmt = stmt.where(MetricSnapshot.owner_user_id == scope.owner_user_id)
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
    owner_user_id: int | None = None,
    metric_domain: str | None = None,
    semantic_version: str = "1.0.0",
    scope: str = "player_match",
    validation_status: str = "legacy_unverified",
    implementation_version: str | None = None,
    input_event_hash: str | None = None,
) -> MetricSnapshot:
    match = _validate_match(db, match_id)
    resolved_owner_user_id = owner_user_id if owner_user_id is not None else match.user_id
    _validate_snapshot_contract(
        owner_user_id=resolved_owner_user_id,
        semantic_version=semantic_version,
        validation_status=validation_status,
        source_event_set_id=source_event_set_id,
    )
    input_hash = _optional_text(input_event_hash) or deterministic_input_hash(metrics)
    contract_metadata = _metadata_with_contract_provenance(
        metadata,
        owner_user_id=resolved_owner_user_id,
        match_id=match_id,
        player_key=player_key,
        source_parser_artifact_id=source_parser_artifact_id,
        source_event_set_id=source_event_set_id,
        metric_domain=metric_domain or source,
        semantic_version=semantic_version,
        scope=scope,
        implementation_version=implementation_version,
        input_event_hash=input_hash,
        metrics=metrics,
        validation_status=validation_status,
    )
    snapshot = MetricSnapshot(
        owner_user_id=resolved_owner_user_id,
        match_id=match_id,
        player_key=_required_text(player_key, "player_key"),
        player_name=_optional_text(player_name),
        player_steamid=_optional_text(player_steamid),
        source=_required_text(source, "source"),
        metric_domain=_required_text(metric_domain or source, "metric_domain"),
        semantic_version=_required_text(semantic_version, "semantic_version"),
        scope=_required_text(scope, "scope"),
        validation_status=validation_status,
        implementation_version=_optional_text(implementation_version),
        input_event_hash=input_hash,
        source_parser_artifact_id=source_parser_artifact_id,
        source_event_set_id=_optional_text(source_event_set_id),
        metrics_json=_dumps_dict(metrics, "metrics"),
        confidence_baseline_json=_dumps_dict(confidence_baseline, "confidence_baseline"),
        caveats_json=_dumps_list(caveats or []),
        metadata_json=_dumps_dict(contract_metadata, "metadata"),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_metric_snapshot(db: Session, snapshot_id: int) -> MetricSnapshot | None:
    return db.get(MetricSnapshot, snapshot_id)


def find_metric_snapshot(
    db: Session,
    *,
    match_id: int,
    player_key: str,
    source: str,
    semantic_version: str = "1.0.0",
    metric_domain: str | None = None,
    source_event_set_id: str | None = None,
) -> MetricSnapshot | None:
    stmt = (
        select(MetricSnapshot)
        .where(MetricSnapshot.match_id == match_id)
        .where(MetricSnapshot.player_key == player_key)
        .where(MetricSnapshot.source == source)
        .where(MetricSnapshot.semantic_version == semantic_version)
    )
    if metric_domain is not None:
        stmt = stmt.where(MetricSnapshot.metric_domain == metric_domain)
    if source_event_set_id is not None:
        stmt = stmt.where(MetricSnapshot.source_event_set_id == source_event_set_id)
    return db.scalar(
        stmt.order_by(MetricSnapshot.created_at.desc(), MetricSnapshot.id.desc())
    )


def list_metric_snapshots(
    db: Session,
    *,
    match_id: int | None = None,
    player_key: str | None = None,
    source: str | None = None,
    semantic_version: str | None = None,
    validation_status: str | None = None,
    limit: int = 100,
) -> list[MetricSnapshot]:
    stmt = select(MetricSnapshot).order_by(MetricSnapshot.created_at.desc(), MetricSnapshot.id.desc()).limit(limit)
    if match_id is not None:
        stmt = stmt.where(MetricSnapshot.match_id == match_id)
    if player_key is not None:
        stmt = stmt.where(MetricSnapshot.player_key == player_key)
    if source is not None:
        stmt = stmt.where(MetricSnapshot.source == source)
    if semantic_version is not None:
        stmt = stmt.where(MetricSnapshot.semantic_version == semantic_version)
    if validation_status is not None:
        stmt = stmt.where(MetricSnapshot.validation_status == validation_status)
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
    owner_user_id: int | None = None,
    metric_domain: str | None = None,
    semantic_version: str = "1.0.0",
    scope: str = "player_match",
    validation_status: str = "legacy_unverified",
    implementation_version: str | None = None,
    input_event_hash: str | None = None,
) -> MetricSnapshot:
    existing = find_metric_snapshot(
        db,
        match_id=match_id,
        player_key=player_key,
        source=source,
        semantic_version=semantic_version,
        metric_domain=metric_domain or source,
        source_event_set_id=source_event_set_id,
    )
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
            owner_user_id=owner_user_id,
            metric_domain=metric_domain,
            semantic_version=semantic_version,
            scope=scope,
            validation_status=validation_status,
            implementation_version=implementation_version,
            input_event_hash=input_event_hash,
        )
    incoming_hash = _optional_text(input_event_hash) or deterministic_input_hash(metrics)
    if existing.input_event_hash == incoming_hash and _loads(existing.metrics_json, fallback={}) == dict(metrics):
        return existing
    raise ValueError(
        "metric snapshot semantic identity collision; increment semantic_version or source_event_set_id"
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
    owner_scope = owner_player_metric_snapshot_scope(db, user_id=user_id)
    metric_snapshot_ids = [
        snapshot.id
        for snapshot in metric_snapshots
        if snapshot.validation_status in TRUSTED_VALIDATION_STATES
        and snapshot.owner_user_id == user_id
        and snapshot.semantic_version in ACCEPTED_SEMANTIC_VERSIONS
        and snapshot.player_key == owner_scope.player_key
    ]
    from app.services.ai_coach import process_owner_match_metric_snapshots_for_coach_loop

    return process_owner_match_metric_snapshots_for_coach_loop(
        db,
        user_id=user_id,
        match_id=match_id,
        metric_snapshot_ids=metric_snapshot_ids,
        evaluation_window_start=evaluation_window_start,
        evaluation_window_end=evaluation_window_end,
    )


def metric_snapshot_payload(snapshot: MetricSnapshot, *, trusted_only: bool = False) -> dict[str, Any]:
    metrics = _loads(snapshot.metrics_json, fallback={})
    metadata = _loads(snapshot.metadata_json, fallback={})
    validation = metadata.get("metric_validation") if isinstance(metadata, Mapping) else None
    if trusted_only:
        if snapshot.validation_status not in TRUSTED_VALIDATION_STATES:
            metrics = {}
        elif isinstance(validation, Mapping):
            metrics = {
                key: value
                for key, value in metrics.items()
                if isinstance(validation.get(key), Mapping) and validation[key].get("status") == "validated"
            }
    return {
        "id": snapshot.id,
        "owner_user_id": snapshot.owner_user_id,
        "match_id": snapshot.match_id,
        "player_key": snapshot.player_key,
        "player_name": snapshot.player_name,
        "player_steamid": snapshot.player_steamid,
        "source": snapshot.source,
        "metric_domain": snapshot.metric_domain,
        "semantic_version": snapshot.semantic_version,
        "scope": snapshot.scope,
        "validation_status": snapshot.validation_status,
        "implementation_version": snapshot.implementation_version,
        "input_event_hash": snapshot.input_event_hash,
        "source_parser_artifact_id": snapshot.source_parser_artifact_id,
        "source_event_set_id": snapshot.source_event_set_id,
        "metrics": metrics,
        "confidence_baseline": _loads(snapshot.confidence_baseline_json, fallback={}),
        "caveats": _loads(snapshot.caveats_json, fallback=[]),
        "metadata": metadata,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
    }


def _validate_analysis_scope(scope: MetricSnapshotAnalysisScope) -> None:
    if scope.source not in {"steam", "faceit", "unknown"}:
        raise ValueError("analysis scope source must be steam, faceit or unknown")
    if scope.mode not in {"personal", "admin_debug_all_snapshots"}:
        raise ValueError("analysis scope mode is invalid")
    if not set(scope.validation_statuses).issubset(VALIDATION_STATES):
        raise ValueError("analysis scope validation status is invalid")


def _analysis_scope_source(source: str) -> AnalysisScopeSource:
    normalized = str(source).strip().lower()
    if normalized not in {"steam", "faceit", "unknown"}:
        raise ValueError("analysis scope source must be steam, faceit or unknown")
    return cast(AnalysisScopeSource, normalized)


def _int_tuple(values: Sequence[int] | None) -> tuple[int, ...]:
    return tuple(int(value) for value in (values or ()))


def _validate_match(db: Session, match_id: int) -> Match:
    match = db.get(Match, match_id)
    if match is None:
        raise ValueError(f"Metric snapshot match_id does not exist: {match_id}")
    return match


def _validate_snapshot_contract(
    *,
    owner_user_id: int | None,
    semantic_version: str,
    validation_status: str,
    source_event_set_id: str | None,
) -> None:
    if validation_status not in VALIDATION_STATES:
        raise ValueError("validation_status is invalid")
    if validation_status == "validated":
        if owner_user_id is None:
            raise ValueError("validated snapshots require owner_user_id")
        if not source_event_set_id:
            raise ValueError("validated snapshots require source_event_set_id")
    parts = semantic_version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("semantic_version must be x.y.z")


def deterministic_input_hash(value: MetricPayload | Sequence[Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


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


def _metadata_with_contract_provenance(
    metadata: MetricPayload | None,
    **identity: Any,
) -> dict[str, Any]:
    value = _metadata_with_retention(metadata)
    metrics = identity.pop("metrics")
    accepted_phase = value.get("accepted_phase") if isinstance(value.get("accepted_phase"), Mapping) else {}
    metric_validation = value.get("metric_validation") if isinstance(value.get("metric_validation"), Mapping) else {}
    reason_codes = sorted(
        {
            str(code)
            for record in metric_validation.values()
            if isinstance(record, Mapping)
            for code in record.get("reason_codes", [])
        }
    )
    value["provenance"] = {
        **identity,
        "metric_keys": sorted(str(key) for key in metrics),
        "sample_matches": 1,
        "sample_rounds": len(accepted_phase.get("round_numbers", [])),
        "input_event_count": value.get("event_count"),
        "numerators": _metric_numerators(metrics),
        "denominators": _metric_denominators(metrics),
        "reason_codes": reason_codes,
    }
    return value


def _metric_numerators(metrics: MetricPayload) -> dict[str, Any]:
    numerators = {str(key): item for key, item in metrics.items()}
    derived = {
        "kd_ratio": metrics.get("kills"),
        "headshot_kill_rate": metrics.get("headshot_kills"),
        "survival_rate": metrics.get("survived_rounds"),
        "kills_per_round": metrics.get("kills"),
        "adr": metrics.get("effective_enemy_damage"),
        "opening_duel_win_rate": metrics.get("opening_duel_wins"),
        "opening_death_rate": metrics.get("opening_deaths"),
        "traded_death_rate": metrics.get("traded_deaths"),
        "untraded_death_rate": metrics.get("untraded_deaths"),
        "trade_success_rate": metrics.get("trade_kills"),
        "utility_damage_per_round": metrics.get("effective_enemy_utility_damage"),
        "shot_accuracy": metrics.get("accepted_hits"),
        "hit_based_headshot_rate": metrics.get("head_hits"),
        "first_bullet_accuracy": metrics.get("first_shot_hits"),
    }
    numerators.update({key: item for key, item in derived.items() if key in metrics and item is not None})
    return numerators


def _metric_denominators(metrics: MetricPayload) -> dict[str, Any]:
    candidates = {
        "kd_ratio": metrics.get("deaths"),
        "headshot_kill_rate": metrics.get("kills"),
        "survival_rate": metrics.get("rounds_played"),
        "kills_per_round": metrics.get("rounds_played"),
        "adr": metrics.get("rounds_played"),
        "kast": metrics.get("rounds_played"),
        "opening_duel_win_rate": metrics.get("opening_duel_attempts"),
        "opening_death_rate": metrics.get("rounds_played"),
        "utility_damage_per_round": metrics.get("rounds_played"),
        "shot_accuracy": metrics.get("accepted_shots"),
        "hit_based_headshot_rate": metrics.get("accepted_hits"),
        "first_bullet_accuracy": metrics.get("first_shots"),
        "traded_death_rate": metrics.get("deaths"),
        "untraded_death_rate": metrics.get("deaths"),
        "trade_success_rate": metrics.get("trade_opportunities"),
    }
    return {key: item for key, item in candidates.items() if key in metrics and item is not None}


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
