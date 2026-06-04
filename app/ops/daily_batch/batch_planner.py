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
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.factor_analytics.constants import DEFAULT_HOLDOUT_START_DATE
from app.ops.daily_batch.evidence_windows import (
    DEFAULT_FACTOR_IC_LOOKBACK_DAYS,
    list_completed_validation_dates,
    resolve_quant_evidence_window,
)
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
        holdout_start_date: date = DEFAULT_HOLDOUT_START_DATE,
    ) -> None:
        self.db = db
        self.universe_code = universe_code
        self.benchmark_symbol = benchmark_symbol
        self.strategies = strategies
        self.holdout_start_date = holdout_start_date
        self.universe_repo = UniverseRepository(db)
        self.stock_repo = StockRepository(db)
        self.market_data_repo = MarketDataRepository(db)
        self.ranking_run_repo = RankingRunRepository(db)
        self.validation_repo = RankingValidationRepository(db)
        self.validation_metrics_repo = ValidationMetricsRepository(db)
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

        lookback_start = max(
            self.holdout_start_date,
            target - timedelta(days=DEFAULT_FACTOR_IC_LOOKBACK_DAYS),
        )
        completed_dates: list[date] = []
        for spec in self.strategies:
            completed_dates.extend(
                list_completed_validation_dates(
                    self.db,
                    universe_code=self.universe_code,
                    strategy_name=spec.strategy_name,
                    strategy_version=spec.strategy_version,
                    start_date=lookback_start,
                    end_date=target,
                )
            )
        completed_dates = sorted(set(completed_dates))

        evidence_window = resolve_quant_evidence_window(
            plan_from_date=window_start,
            target_trading_day=target,
            holdout_start_date=self.holdout_start_date,
            completed_validation_dates=completed_dates,
        )
        factor_ic_window_start = evidence_window[0] if evidence_window else None
        factor_ic_window_end = evidence_window[1] if evidence_window else None

        # Factor IC / research intelligence require completed-validation evidence windows.
        factor_ic_needed = evidence_window is not None or force_from_date
        if force_from_date:
            factor_ic_window_start = max(self.holdout_start_date, window_start)
            factor_ic_window_end = target
        regime_history_needed = (
            validation_gap > 0
            or force_from_date
            or self._regime_history_gap(
                benchmark_symbol=self.benchmark_symbol,
                window_start=window_start,
                target=target,
            )
        )
        regime_performance_needed = (
            self._has_horizon_metrics() or validation_gap > 0 or force_from_date
        )
        research_intelligence_needed = evidence_window is not None or force_from_date
        exit_research_needed = factor_ic_needed

        already_current = (
            not needs_ingest
            and all(len(v) == 0 for v in ranking_gaps.values())
            and validation_gap == 0
            and evidence_window is None
            and not force_from_date
        )

        return DailyBatchPlan(
            target_trading_day=target,
            from_date=window_start,
            needs_ingest=needs_ingest,
            ranking_gaps=ranking_gaps,
            validation_gap_count=validation_gap,
            factor_ic_needed=factor_ic_needed,
            regime_history_needed=regime_history_needed,
            regime_performance_needed=regime_performance_needed,
            exit_research_needed=exit_research_needed,
            research_intelligence_needed=research_intelligence_needed,
            factor_ic_window_start=factor_ic_window_start,
            factor_ic_window_end=factor_ic_window_end,
            already_current=already_current,
        )

    def _has_horizon_metrics(self) -> bool:
        for spec in self.strategies:
            if self.validation_metrics_repo.count_for_strategy(
                spec.strategy_name,
                spec.strategy_version,
            ):
                return True
        return False

    def _regime_history_gap(
        self,
        *,
        benchmark_symbol: str,
        window_start: date,
        target: date,
    ) -> bool:
        from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository

        repo = RegimeAnalyticsRepository(self.db)
        benchmark = self.stock_repo.get_by_symbol(benchmark_symbol)
        if benchmark is None:
            return True
        expected = self.calendar.trading_days_in_range(
            window_start,
            target,
            universe_stock_ids=[],
            benchmark_stock_id=benchmark.id,
            source=MARKET_DATA_SOURCE_YAHOO,
        )
        if not expected:
            return False
        existing = repo.count_regime_history(
            benchmark_symbol=benchmark_symbol.upper(),
            start_date=window_start,
            end_date=target,
        )
        return existing < len(expected)
