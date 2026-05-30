from __future__ import annotations

from uuid import UUID

from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.schemas.ranking import RankingResultRead, RankingRunRead, RankingTopRead


def _result_read(result: RankingResult, symbol: str | None = None) -> RankingResultRead:
    return RankingResultRead(
        id=str(result.id),
        stock_id=str(result.stock_id),
        symbol=symbol,
        rank=result.rank,
        score=float(result.score),
        score_components=result.score_components,
    )


def run_to_read(run: RankingRun, symbol_map: dict[UUID, str] | None = None) -> RankingRunRead:
    symbol_map = symbol_map or {}
    results = [
        _result_read(result, symbol_map.get(result.stock_id))
        for result in sorted(run.results, key=lambda r: r.rank)
    ]
    return RankingRunRead(
        id=str(run.id),
        universe_code=run.universe_code,
        as_of_date=run.as_of_date,
        strategy_name=run.strategy_name,
        strategy_version=run.strategy_version,
        benchmark_symbol=run.benchmark_symbol,
        inputs_hash=run.inputs_hash,
        filter_config_hash=run.filter_config_hash,
        normalization_method=run.normalization_method,
        status=run.status,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        error_message=run.error_message,
        metadata=run.metadata_,
        results_count=len(results),
        results=results,
    )


def top_to_read(
    run: RankingRun, top: list[RankingResult], symbol_map: dict[UUID, str]
) -> RankingTopRead:
    return RankingTopRead(
        run_id=str(run.id),
        as_of_date=run.as_of_date,
        strategy_name=run.strategy_name,
        strategy_version=run.strategy_version,
        top=[_result_read(result, symbol_map.get(result.stock_id)) for result in top],
    )
