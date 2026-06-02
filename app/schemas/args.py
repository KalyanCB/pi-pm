from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.workspace_args.constants import DEFAULT_COMMITTEE_CODES


class ResearchRunRequest(BaseModel):
    ranking_run_id: UUID
    top_n: int = Field(default=20, ge=1, le=100)
    committee_codes: list[str] | None = None
    trigger_mode: str = "on_demand"
    require_completed_validation: bool = True
    dry_run: bool = False
    universe_code: str | None = None
    strategy_name: str | None = None
    strategy_version: str | None = None


class ResearchRunResponse(BaseModel):
    run_id: str
    status: str
    as_of_date: str
    candidates_reviewed: int
    governance_reports_issued: int = 0
    token_usage_total: int = 0
    dry_run: bool = False
    duration_seconds: float | None = None


class ResearchLatestQuery(BaseModel):
    universe_code: str | None = None
    strategy_name: str | None = None
    as_of_date: date | None = None


def default_committee_codes() -> list[str]:
    return list(DEFAULT_COMMITTEE_CODES)
