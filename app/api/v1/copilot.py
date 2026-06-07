"""Copilot — grounded Q&A over Pi-PM data."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth_deps import CurrentUser, OwnerUser
from app.api.deps import get_db
from app.auth.constants import UserRole
from app.core.config import Settings, get_settings
from app.services.copilot_service import CopilotService

router = APIRouter()


def get_copilot_service(db: Session = Depends(get_db)) -> CopilotService:
    return CopilotService(db)


# ── Schemas ───────────────────────────────────────────────────────────────────


class AskRequest(BaseModel):
    question: str
    session_id: UUID | None = None


class CitationRead(BaseModel):
    ref: str
    source_table: str | None
    source_field: str | None
    source_value: str | None


class LineageSummary(BaseModel):
    recommendation_run_ids: list[str] = []
    recommendation_ids: list[str] = []
    portfolio_position_ids: list[str] = []
    committee_review_ids: list[str] = []


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationRead]
    uncited_claims: list[str] = []
    intent: str
    refused: bool
    model: str | None = None
    latency_ms: int | None = None
    query_log_id: str
    lineage: LineageSummary | None = None


class AuditLogRead(BaseModel):
    id: UUID
    question: str
    intent: str
    refused: bool
    answer: str | None
    model: str | None
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    user: CurrentUser,
    settings: Settings = Depends(get_settings),
    service: CopilotService = Depends(get_copilot_service),
) -> AskResponse:
    """Ask a question about Pi-PM data — rankings, conviction, validation, ARGS, ops."""
    # Dev auth bypass uses a synthetic user id that is not persisted in `users`.
    audit_user_id = user.user_id if settings.auth_enabled else None
    result = service.ask(
        payload.question,
        session_id=payload.session_id,
        user_id=audit_user_id,
    )
    lineage_raw = result.get("lineage")
    lineage = LineageSummary(**lineage_raw) if lineage_raw else None
    return AskResponse(
        answer=result["answer"] or "",
        citations=[CitationRead(**c) for c in result["citations"]],
        uncited_claims=result.get("uncited_claims", []),
        intent=result["intent"],
        refused=result["refused"],
        model=result.get("model"),
        latency_ms=result.get("latency_ms"),
        query_log_id=result["query_log_id"],
        lineage=lineage,
    )


@router.get("/audit", response_model=list[AuditLogRead])
def get_audit(
    user: OwnerUser,
    limit: int = Query(default=50, ge=1, le=500),
    service: CopilotService = Depends(get_copilot_service),
) -> list[AuditLogRead]:
    """Export audit log of copilot queries for the authenticated user."""
    filter_user_id = None if user.has_role(UserRole.ADMIN) else user.user_id
    return service.get_audit_logs(limit=limit, user_id=filter_user_id)  # type: ignore[return-value]
