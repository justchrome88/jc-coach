from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CoachReport, DemoParseArtifact, ImportJob, Match, MetricSnapshot, SteamAccount


def resolve_owner_ids(
    db: Session,
    *,
    user_id: int | None = None,
    steam_account_id: int | None = None,
) -> tuple[int | None, int | None]:
    if steam_account_id is None:
        return user_id, None
    account = db.get(SteamAccount, steam_account_id)
    if account is None:
        raise ValueError(f"Steam account does not exist: {steam_account_id}")
    if user_id is not None and account.user_id is not None and account.user_id != user_id:
        raise PermissionError("Steam account belongs to a different user.")
    return user_id if user_id is not None else account.user_id, account.id


def attach_match_owner_from_import_job(db: Session, match: Match, job: ImportJob) -> Match:
    user_id, steam_account_id = resolve_owner_ids(
        db,
        user_id=job.user_id,
        steam_account_id=job.steam_account_id,
    )
    _ensure_match_owner(match, user_id=user_id, steam_account_id=steam_account_id)
    match.import_job_id = job.id
    return match


def assert_match_owner(match: Match, *, user_id: int | None) -> None:
    if user_id is not None and match.user_id is not None and match.user_id != user_id:
        raise PermissionError("Match belongs to a different user.")


def owned_match_select(user_id: int):
    return select(Match).where(Match.user_id == user_id)


def get_owned_match(db: Session, *, user_id: int, match_id: int) -> Match | None:
    return db.scalar(owned_match_select(user_id).where(Match.id == match_id))


def get_owned_import_job(db: Session, *, user_id: int, job_id: int) -> ImportJob | None:
    return db.scalar(select(ImportJob).where(ImportJob.id == job_id).where(ImportJob.user_id == user_id))


def get_owned_parse_artifact(db: Session, *, user_id: int, artifact_id: int) -> DemoParseArtifact | None:
    return db.scalar(
        select(DemoParseArtifact)
        .join(Match, Match.id == DemoParseArtifact.match_id)
        .where(DemoParseArtifact.id == artifact_id)
        .where(Match.user_id == user_id)
    )


def get_owned_metric_snapshot(db: Session, *, user_id: int, snapshot_id: int) -> MetricSnapshot | None:
    return db.scalar(
        select(MetricSnapshot)
        .join(Match, Match.id == MetricSnapshot.match_id)
        .where(MetricSnapshot.id == snapshot_id)
        .where(Match.user_id == user_id)
    )


def list_owned_metric_snapshots(db: Session, *, user_id: int, match_id: int | None = None) -> list[MetricSnapshot]:
    stmt = (
        select(MetricSnapshot)
        .join(Match, Match.id == MetricSnapshot.match_id)
        .where(Match.user_id == user_id)
        .order_by(MetricSnapshot.created_at.desc(), MetricSnapshot.id.desc())
    )
    if match_id is not None:
        stmt = stmt.where(MetricSnapshot.match_id == match_id)
    return list(db.scalars(stmt).all())


def get_owned_coach_report(db: Session, *, user_id: int, report_id: int) -> CoachReport | None:
    return db.scalar(select(CoachReport).where(CoachReport.id == report_id).where(CoachReport.user_id == user_id))


def _ensure_match_owner(match: Match, *, user_id: int | None, steam_account_id: int | None) -> None:
    if user_id is not None:
        assert_match_owner(match, user_id=user_id)
        match.user_id = user_id
    if steam_account_id is not None:
        if match.steam_account_id is not None and match.steam_account_id != steam_account_id:
            raise PermissionError("Match belongs to a different Steam account.")
        match.steam_account_id = steam_account_id
