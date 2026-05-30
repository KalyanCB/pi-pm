from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_ranking_service, get_stock_repository
from app.db.repositories.stock_repository import StockRepository
from app.schemas.ranking import RankingRunRead, RankingRunRequest, RankingTopRead
from app.services.ranking_serializers import run_to_read, top_to_read
from app.services.ranking_service import RankingService

router = APIRouter()


def _symbol_map(stock_repo: StockRepository, stock_ids: list[UUID]) -> dict[UUID, str]:
    mapping: dict[UUID, str] = {}
    for stock_id in stock_ids:
        stock = stock_repo.get_by_id(stock_id)
        if stock:
            mapping[stock_id] = stock.symbol
    return mapping


@router.post("/run", response_model=RankingRunRead, status_code=201)
def run_ranking(
    payload: RankingRunRequest,
    service: RankingService = Depends(get_ranking_service),
    stock_repo: StockRepository = Depends(get_stock_repository),
) -> RankingRunRead:
    run = service.run_ranking(payload)
    stock_ids = [result.stock_id for result in run.results]
    return run_to_read(run, _symbol_map(stock_repo, stock_ids))


@router.get("/latest", response_model=RankingRunRead)
def get_latest_ranking(
    universe_code: str | None = Query(default=None),
    strategy_name: str | None = Query(default=None),
    strategy_version: str | None = Query(default=None),
    service: RankingService = Depends(get_ranking_service),
    stock_repo: StockRepository = Depends(get_stock_repository),
) -> RankingRunRead:
    run = service.get_latest(universe_code, strategy_name, strategy_version)
    stock_ids = [result.stock_id for result in run.results]
    return run_to_read(run, _symbol_map(stock_repo, stock_ids))


@router.get("/{run_id}", response_model=RankingRunRead)
def get_ranking_run(
    run_id: UUID,
    service: RankingService = Depends(get_ranking_service),
    stock_repo: StockRepository = Depends(get_stock_repository),
) -> RankingRunRead:
    run = service.get_run(run_id)
    stock_ids = [result.stock_id for result in run.results]
    return run_to_read(run, _symbol_map(stock_repo, stock_ids))


@router.get("/{run_id}/top", response_model=RankingTopRead)
def get_ranking_top(
    run_id: UUID,
    n: int = Query(default=10, ge=1, le=100),
    service: RankingService = Depends(get_ranking_service),
    stock_repo: StockRepository = Depends(get_stock_repository),
) -> RankingTopRead:
    run, top = service.get_top(run_id, n)
    stock_ids = [result.stock_id for result in top]
    return top_to_read(run, top, _symbol_map(stock_repo, stock_ids))
