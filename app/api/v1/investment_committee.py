"""Investment Committee API (M3.1) — investor-facing routes.

These routes expose the same underlying ARGS/research functionality with
investor-friendly terminology. Internal batch phase remains RESEARCH (ADR-023).

Old routes at /research/* are preserved as deprecated aliases.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth_deps import OwnerUser
from app.api.deps import get_args_explainability_service, get_args_research_run_service
from app.core.exceptions import NotFoundError
from app.schemas.args import ResearchRunRequest
from app.services.args_explainability_service import ArgsExplainabilityService
from app.services.args_research_run_service import ArgsResearchRunService
from app.workspace_args.constants import COMMITTEE_DISPLAY_NAMES, CommitteeAdvisoryAction

router = APIRouter()


@router.post("/review", status_code=201)
def start_committee_review(
    payload: ResearchRunRequest,
    _owner: OwnerUser,
    service: ArgsResearchRunService = Depends(get_args_research_run_service),
) -> dict:
    """Start an Investment Committee review for the top-N ranked stocks.

    Equivalent to POST /research/run — investor-facing terminology.
    Internal: triggers ARGS research run with 5 committees + CRO.
    Advisory outputs are display-only (R-ARGS-04).
    """
    return service.run(
        ranking_run_id=payload.ranking_run_id,
        top_n=payload.top_n,
        committee_codes=payload.committee_codes,
        trigger_mode=payload.trigger_mode,
        require_completed_validation=payload.require_completed_validation,
        dry_run=payload.dry_run,
        universe_code=payload.universe_code,
        strategy_name=payload.strategy_name,
        strategy_version=payload.strategy_version,
    )


@router.get("/latest")
def latest_committee_review(
    universe_code: str = Query(default="NIFTY_500"),
    strategy_name: str | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    service: ArgsResearchRunService = Depends(get_args_research_run_service),
) -> dict:
    """Get the latest Investment Committee review.

    When ``strategy_name`` is provided, returns the latest review for that
    strategy so committee data aligns with the regime-selected strategy on the
    client. ``as_of_date`` pins the review to a specific session (for the
    committee date picker). Both omitted → latest review (back-compat).
    """
    result = service.get_latest(
        universe_code=universe_code,
        strategy_name=strategy_name,
        as_of_date=as_of_date,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No committee review found")
    return result


@router.get("/{review_id}")
def get_committee_review(
    review_id: UUID,
    service: ArgsResearchRunService = Depends(get_args_research_run_service),
) -> dict:
    """Get a specific Investment Committee review by ID."""
    try:
        return service.get_run(review_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{review_id}/packets")
def get_committee_packets(
    review_id: UUID,
    symbol: str | None = Query(default=None),
    service: ArgsResearchRunService = Depends(get_args_research_run_service),
) -> list[dict]:
    """Get all advisory packets for a committee review.

    Each packet contains:
    - recommendation block (deterministic — from Recommendation Engine)
    - committee_advisory block (advisory only — from Investment Committee)
    Equivalent to GET /research/{run_id}/packet.
    """
    return service.get_packet_for_run(review_id, symbol=symbol)


@router.get("/{review_id}/report")
def get_committee_report(
    review_id: UUID,
    service: ArgsResearchRunService = Depends(get_args_research_run_service),
) -> dict:
    """Get the Investment Committee Chair (CRO) report for a review.

    Includes HIGH_CONCERN escalations, advisory actions per committee,
    and the Chair's synthesis narrative.
    Equivalent to GET /research/{run_id}/governance-report.
    """
    try:
        run = service.get_run(review_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Get governance reports for this run
    from app.db.repositories.governance_research_report_repository import (
        GovernanceResearchReportRepository,
    )

    report_repo = GovernanceResearchReportRepository(service.db)
    reports = report_repo.list_for_run(UUID(run["id"]))
    return {
        "committee_review_id": run["id"],
        "status": run.get("status"),
        "reports": [
            {
                "symbol": r.symbol,
                "as_of_date": r.as_of_date.isoformat() if r.as_of_date else None,
                "summary": r.summary,
                "narrative": r.narrative_md,
                "confidence": float(r.confidence) if r.confidence else None,
            }
            for r in reports
        ],
    }


@router.get("/{review_id}/explain")
def explain_committee_review(
    review_id: UUID,
    service: ArgsExplainabilityService = Depends(get_args_explainability_service),
) -> dict:
    """Explain the Investment Committee review — evidence, reasoning, advisory actions."""
    try:
        return service.explain_run(review_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/committees/members")
def list_committee_members() -> dict:
    """List all Investment Committee members with their display names and roles."""
    return {
        "committees": [
            {"code": code, "display_name": name, "role": "Advisory member"}
            for code, name in COMMITTEE_DISPLAY_NAMES.items()
            if code != "CRO"
        ],
        "chair": {
            "code": "CRO",
            "display_name": COMMITTEE_DISPLAY_NAMES["CRO"],
            "role": "Investment Committee Chair — aggregates and synthesises",
        },
        "advisory_actions": [a.value for a in CommitteeAdvisoryAction],
        "escalation_rule": (
            "HIGH_CONCERN from any single committee overrides majority vote. "
            "Risk is not democratic."
        ),
        "note": (
            "All advisory actions are display-only. "
            "No committee output can change recommendation.action or conviction_score."
        ),
    }
