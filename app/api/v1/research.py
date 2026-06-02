from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_args_explainability_service, get_args_research_run_service
from app.schemas.args import ResearchRunRequest
from app.services.args_explainability_service import ArgsExplainabilityService
from app.services.args_research_run_service import ArgsResearchRunService

router = APIRouter()


@router.post("/run", status_code=201)
def start_research_run(
    payload: ResearchRunRequest,
    service: ArgsResearchRunService = Depends(get_args_research_run_service),
) -> dict:
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
def latest_research_run(
    universe_code: str | None = Query(None),
    strategy_name: str | None = Query(None),
    as_of_date: date | None = Query(None),
    service: ArgsResearchRunService = Depends(get_args_research_run_service),
) -> dict:
    result = service.get_latest(
        universe_code=universe_code,
        strategy_name=strategy_name,
        as_of_date=as_of_date,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No completed research run found")
    return result


@router.get("/{run_id}")
def get_research_run(
    run_id: UUID,
    service: ArgsResearchRunService = Depends(get_args_research_run_service),
) -> dict:
    return service.get_run(run_id)


@router.get("/{run_id}/packet")
def get_research_packets(
    run_id: UUID,
    symbol: str | None = Query(None),
    service: ArgsResearchRunService = Depends(get_args_research_run_service),
) -> dict:
    packets = service.get_packet_for_run(run_id, symbol=symbol)
    return {"research_run_id": str(run_id), "packets": packets}


@router.get("/{run_id}/explain")
def explain_research_run(
    run_id: UUID,
    explain_service: ArgsExplainabilityService = Depends(get_args_explainability_service),
) -> dict:
    return explain_service.explain_run(run_id)


@router.get("/{run_id}/lineage")
def research_run_lineage(
    run_id: UUID,
    explain_service: ArgsExplainabilityService = Depends(get_args_explainability_service),
) -> dict:
    return explain_service.lineage_for_run(run_id)
