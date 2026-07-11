"""Coach evidence, domain, and provider routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.routes.base import router
from app.db.session import get_db
from app.services.coach.ai import (
    build_ai_coach_payload,
    latest_ai_coach_report,
    latest_ai_handoff,
    list_ai_coach_reports,
    personal_ai_coach_analysis_scope,
    save_ai_coach_result,
    serialize_ai_coach_report,
)
from app.services.coach.domain_analysis import coach_domain_slots_payload
from app.services.coach.provider import (
    ai_provider_health,
    generate_ai_coach_with_provider,
    prepare_ai_coach_handoff,
)
from app.services.owner.auth import current_user_from_session


@router.get("/coach/ai/payload")
def ai_coach_payload_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    return build_ai_coach_payload(db, analysis_scope=personal_ai_coach_analysis_scope(db))

@router.get("/coach/domains")
def coach_domain_slots_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    owner_user_id: int | None = None,
    technical_provenance: bool = False,
) -> dict:
    current = current_user_from_session(request, db)
    if current is None:
        raise HTTPException(status_code=401, detail="Authenticated owner session is required")
    if owner_user_id is not None and owner_user_id != current.id:
        raise HTTPException(status_code=403, detail="Cross-owner coach domain access denied")
    return coach_domain_slots_payload(db, owner_user_id=current.id, include_provenance=technical_provenance)

@router.post("/coach/ai/handoff")
def ai_coach_handoff_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"ok": True, **prepare_ai_coach_handoff(db, analysis_scope=personal_ai_coach_analysis_scope(db))}

@router.get("/coach/ai/handoff/latest")
def latest_ai_coach_handoff_endpoint() -> dict:
    handoff = latest_ai_handoff()
    if handoff is None:
        raise HTTPException(status_code=404, detail="No AI coach handoff generated yet")
    return handoff

@router.get("/coach/ai/provider/health")
def ai_provider_health_endpoint() -> dict:
    return ai_provider_health()

@router.post("/coach/ai/generate")
def generate_ai_coach_with_provider_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    try:
        report = generate_ai_coach_with_provider(db, analysis_scope=personal_ai_coach_analysis_scope(db))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "id": report.id, "created_at": report.created_at, "source_ref": report.source_ref}

@router.post("/coach/ai/result")
def save_ai_coach_result_endpoint(
    db: Annotated[Session, Depends(get_db)],
    report_markdown: str,
    source_ref: str | None = None,
) -> dict:
    try:
        report = save_ai_coach_result(
            db,
            report_markdown,
            source_ref=source_ref,
            analysis_scope=personal_ai_coach_analysis_scope(db),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "id": report.id, "created_at": report.created_at}

@router.get("/coach/ai/result/latest")
def latest_ai_coach_result_endpoint(db: Annotated[Session, Depends(get_db)]) -> dict:
    report = latest_ai_coach_report(db)
    if report is None:
        raise HTTPException(status_code=404, detail="No AI coach report saved yet")
    return serialize_ai_coach_report(report)

@router.get("/coach/ai/results")
def ai_coach_results_endpoint(db: Annotated[Session, Depends(get_db)], limit: int = 10) -> list[dict]:
    return [serialize_ai_coach_report(report) for report in list_ai_coach_reports(db, limit=max(1, min(limit, 50)))]

__all__ = (
    'ai_coach_handoff_endpoint',
    'ai_coach_payload_endpoint',
    'ai_coach_results_endpoint',
    'ai_provider_health_endpoint',
    'coach_domain_slots_endpoint',
    'generate_ai_coach_with_provider_endpoint',
    'latest_ai_coach_handoff_endpoint',
    'latest_ai_coach_result_endpoint',
    'save_ai_coach_result_endpoint',
)
