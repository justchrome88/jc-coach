"""Coach report routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes.base import router
from app.db.session import get_db
from app.services.coach.reports import generate_report, latest_report


@router.post("/reports/generate")
def generate_report_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    report = generate_report(db)
    return {"ok": True, "id": report.id, "matches_count": report.matches_count, "created_at": report.created_at}

@router.get("/reports/latest")
def latest_report_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    report = latest_report(db)
    if report is None:
        raise HTTPException(status_code=404, detail="No reports generated yet")
    return {
        "id": report.id,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "matches_count": report.matches_count,
        "report_markdown": report.report_markdown,
        "created_at": report.created_at,
    }

__all__ = (
    'generate_report_endpoint',
    'latest_report_endpoint',
)
