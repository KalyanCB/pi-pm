from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_stock_setup_research_service
from app.services.stock_setup_research_service import StockSetupResearchService

router = APIRouter()


@router.post("/runs/{ranking_run_id}/generate")
def generate_stock_setup_research(
    ranking_run_id: UUID,
    limit: int | None = Query(default=None, ge=1, le=500),
    nearest_n: int = Query(default=25, ge=1, le=200),
    min_similarity: float = Query(default=0.55, ge=0.0, le=1.0),
    service: StockSetupResearchService = Depends(get_stock_setup_research_service),
) -> dict:
    return service.run_for_ranking_run(
        ranking_run_id,
        limit=limit,
        nearest_n=nearest_n,
        min_similarity=min_similarity,
    )


@router.get("/runs/{ranking_run_id}")
def list_stock_setup_research(
    ranking_run_id: UUID,
    service: StockSetupResearchService = Depends(get_stock_setup_research_service),
) -> dict:
    rows = service.research_repo.list_for_ranking_run(ranking_run_id)
    return {
        "ranking_run_id": str(ranking_run_id),
        "count": len(rows),
        "rows": [service.to_payload(row) for row in rows],
    }
