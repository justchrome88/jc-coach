"""Legacy recommendation routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes.base import router
from app.db.session import get_db
from app.services.metrics.recommendations import (
    extend_recommendation_target,
    get_active_recommendation_progress,
    get_all_recommendation_progress,
    list_recommendation_history,
    recommendation_category_summary,
    restart_recommendation_category,
    update_recommendation_status,
)


@router.get("/recommendations/active")
def active_recommendation(db: Annotated[Session, Depends(get_db)]) -> dict:
    progress = get_active_recommendation_progress(db)
    if not progress:
        raise HTTPException(status_code=404, detail="No active recommendation yet")
    recommendation = progress["recommendation"]
    return {
        "id": recommendation.id,
        "title": recommendation.title,
        "status": recommendation.status,
        "health": progress["health"],
        "baseline": progress["baseline"],
        "target": progress["target"],
        "counts": progress["counts"],
        "progress_score": progress["progress_score"],
        "completed_matches": progress["completed_matches"],
        "target_matches": progress["target_matches"],
        "summary": progress["summary"],
    }

@router.get("/recommendations")
def all_recommendations(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    progress_items = get_all_recommendation_progress(db)
    return [
        {
            "id": item["recommendation"].id,
            "title": item["recommendation"].title,
            "category": item["recommendation"].category,
            "status": item["recommendation"].status,
            "health": item["health"],
            "baseline": item["baseline"],
            "target": item["target"],
            "counts": item["counts"],
            "progress_score": item["progress_score"],
            "completed_matches": item["completed_matches"],
            "target_matches": item["target_matches"],
            "summary": item["summary"],
        }
        for item in progress_items
    ]

@router.get("/recommendations/history")
def recommendation_history_endpoint(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    return [
        {
            "id": item.id,
            "category": item.category,
            "title": item.title,
            "status": item.status,
            "priority": item.priority,
            "started_at": item.started_at,
            "ended_at": item.ended_at,
            "target_period_matches": item.target_period_matches,
            "baseline_period_matches": item.baseline_period_matches,
        }
        for item in list_recommendation_history(db)
    ]

@router.get("/recommendations/categories")
def recommendation_categories_endpoint(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    return recommendation_category_summary(db)

@router.post("/recommendations/{recommendation_id}/status")
def update_recommendation_status_endpoint(
    db: Annotated[Session, Depends(get_db)],
    recommendation_id: int,
    status: str,
) -> dict:
    try:
        recommendation = update_recommendation_status(db, recommendation_id, status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "id": recommendation.id, "status": recommendation.status}

@router.post("/recommendations/{recommendation_id}/extend")
def extend_recommendation_endpoint(
    db: Annotated[Session, Depends(get_db)],
    recommendation_id: int,
    additional_matches: int = 5,
) -> dict:
    try:
        recommendation = extend_recommendation_target(db, recommendation_id, additional_matches)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "id": recommendation.id,
        "target_period_matches": recommendation.target_period_matches,
    }

@router.post("/recommendations/categories/{category}/restart")
def restart_recommendation_category_endpoint(db: Annotated[Session, Depends(get_db)], category: str) -> dict:
    try:
        recommendation = restart_recommendation_category(db, category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "id": recommendation.id, "category": recommendation.category, "status": recommendation.status}

__all__ = (
    'active_recommendation',
    'all_recommendations',
    'extend_recommendation_endpoint',
    'recommendation_categories_endpoint',
    'recommendation_history_endpoint',
    'restart_recommendation_category_endpoint',
    'update_recommendation_status_endpoint',
)
