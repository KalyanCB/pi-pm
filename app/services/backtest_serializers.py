from __future__ import annotations

from app.backtest.models import BacktestGenerationResult
from app.schemas.backtest import GenerateRankingsResponse


def backtest_result_to_read(result: BacktestGenerationResult) -> GenerateRankingsResponse:
    return GenerateRankingsResponse(
        universe_code=result.universe_code,
        strategy_name=result.strategy_name,
        strategy_version=result.strategy_version,
        benchmark_symbol=result.benchmark_symbol,
        start_date=result.start_date,
        end_date=result.end_date,
        trading_days_total=result.trading_days_total,
        runs_created=result.runs_created,
        runs_reused=result.runs_reused,
        runs_failed=result.runs_failed,
        failed_dates=list(result.failed_dates),
    )
