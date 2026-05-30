from __future__ import annotations

from datetime import date

from app.backtest.models import BacktestGenerationResult
from app.schemas.backtest import GenerateRankingsRequest
from app.schemas.ranking import RankingRunRequest
from app.services.ranking_service import RankingService


class RankingReplayer:
    """Generate historical ranking runs by replaying ranking logic per trading day."""

    def __init__(self, ranking_service: RankingService) -> None:
        self.ranking_service = ranking_service

    def generate(
        self,
        request: GenerateRankingsRequest,
        trading_days: list[date],
        *,
        universe_code: str,
        strategy_name: str,
        strategy_version: str,
        benchmark_symbol: str,
    ) -> BacktestGenerationResult:
        runs_created = 0
        runs_reused = 0
        runs_failed = 0
        failed_dates: list[date] = []

        for as_of_date in trading_days:
            payload = RankingRunRequest(
                universe_code=universe_code,
                as_of_date=as_of_date,
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                benchmark_symbol=benchmark_symbol,
                filter_config=request.filter_config,
            )
            try:
                outcome = self.ranking_service.run_ranking_with_outcome(payload)
                if outcome.reused:
                    runs_reused += 1
                else:
                    runs_created += 1
            except Exception:
                runs_failed += 1
                failed_dates.append(as_of_date)

        return BacktestGenerationResult(
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            benchmark_symbol=benchmark_symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            trading_days_total=len(trading_days),
            runs_created=runs_created,
            runs_reused=runs_reused,
            runs_failed=runs_failed,
            failed_dates=tuple(failed_dates),
        )
