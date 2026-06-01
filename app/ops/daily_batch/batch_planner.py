from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.backtest.trading_calendar import TradingCalendar
from app.core.constants import MARKET_DATA_SOURCE_YAHOO
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.ops.daily_batch.models import DailyBatchPlan, TradingDayResolution

_BACKFILL_REUSE = frozenset({"completed", "insufficient_data"})


@dataclass(frozen=True)
class StrategySpec:
    strategy_name: str
    strategy_version: str


class DailyBatchPlanner:
    def __init__(
        self,
        db: Session,
        *,
        universe_code: str,
        benchmark_symbol: str,
        strategies: list[StrategySpec],
    ) -> None:
        self.db = db
        self.universe_code = universe_code
        self.benchmark_symbol = benchmark_symbol
        self.strategies = strategies
        self.universe_repo = UniverseRepository(db)
        self.stock_repo = StockRepository(db)
        self.market_data_repo = MarketDataRepository(db)
        self.ranking_run_repo = RankingRunRepository(db)
        self.validation_repo = RankingValidationRepository(db)
        self.calendar = TradingCalendar(self.market_data_repo)

    def build_plan(
        self,
        resolution: TradingDayResolution,
        *,
        from_date: date | None = None,
        force_from_date: bool = False,
    ) -> DailyBatchPlan:
        target = resolution.target_trading_day
        data_through = resolution.latest_benchmark_date

        if from_date is not None:
            window_start = from_date
        elif data_through is not None and not force_from_date:
            window_start = data_through + timedelta(days=1)
        elif data_through is not None:
            window_start = data_through
        else:
            window_start = target

        if window_start > target:
            window_start = target

        needs_ingest = data_through is None or data_through < target or force_from_date

        universe_stocks = self.universe_repo.list_stocks_in_universe(self.universe_code)
        stock_ids = [s.id for s in universe_stocks]
        benchmark = self.stock_repo.get_by_symbol(self.benchmark_symbol)
        benchmark_id = benchmark.id if benchmark else None

        expected_days = self.calendar.trading_days_in_range(
            window_start, target, stock_ids, benchmark_id, source=MARKET_DATA_SOURCE_YAHOO
        )

        ranking_gaps: dict[str, list[date]] = {}
        for spec in self.strategies:
            key = f"{spec.strategy_name}:{spec.strategy_version}"
            existing = {
                r.as_of_date
                for r in self.ranking_run_repo.list_completed_in_range(
                    window_start,
                    target,
                    universe_code=self.universe_code,
                    strategy_name=spec.strategy_name,
                    strategy_version=spec.strategy_version,
                )
            }
            if force_from_date:
                missing = list(expected_days)
            else:
                missing = sorted(d for d in expected_days if d not in existing)
            ranking_gaps[key] = missing

        validation_gap = 0
        if expected_days:
            runs = self.ranking_run_repo.list_completed_in_range(
                window_start,
                target,
                universe_code=self.universe_code,
            )
            for run in runs:
                report = self.validation_repo.get_by_ranking_run_id(run.id)
                if report is None or report.status not in _BACKFILL_REUSE:
                    validation_gap += 1

        factor_ic_needed = force_from_date or window_start <= target
        exit_research_needed = factor_ic_needed

        already_current = (
            not needs_ingest
            and all(len(v) == 0 for v in ranking_gaps.values())
            and validation_gap == 0
            and not force_from_date
        )

        return DailyBatchPlan(
            target_trading_day=target,
            from_date=window_start,
            needs_ingest=needs_ingest,
            ranking_gaps=ranking_gaps,
            validation_gap_count=validation_gap,
            factor_ic_needed=factor_ic_needed,
            exit_research_needed=exit_research_needed,
            already_current=already_current,
        )
