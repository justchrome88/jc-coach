"""Match and analytics read routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.routes.base import router
from app.api.routes.serializers import (
    serialize_match,
)
from app.db.models import Match
from app.db.session import get_db
from app.services.metrics.aim import get_aim_profile
from app.services.metrics.analytics import compare_periods, get_map_stats, get_summary
from app.services.shared.match_queries import playable_match_select


@router.get("/matches")
def list_matches(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    matches = db.scalars(playable_match_select().order_by(Match.played_at.desc().nulls_last(), Match.id.desc())).all()
    return [serialize_match(match) for match in matches]

@router.get("/analytics/summary")
def analytics_summary(db: Annotated[Session, Depends(get_db)]) -> dict:
    matches = db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    summary = get_summary(matches)
    comparison = compare_periods(matches)
    map_stats = get_map_stats(matches)
    return {"summary": summary, "comparison": comparison, "map_stats": map_stats}

@router.get("/analytics/aim")
def analytics_aim_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    matches = db.scalars(playable_match_select().order_by(Match.played_at.asc().nulls_last(), Match.id.asc())).all()
    return get_aim_profile(matches)

__all__ = (
    'analytics_aim_endpoint',
    'analytics_summary',
    'list_matches',
)
