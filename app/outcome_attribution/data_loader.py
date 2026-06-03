from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import RankingRunStatus
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.market_data.cache import MarketDataCache
from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.outcome_attribution.constants import ATTRIBUTION_HORIZONS
from app.outcome_attribution.models import OutcomeAttributionConfig, RunBenchmark, StockObservation
from app.validation.constants import MAX_FORWARD_TRADING_DAYS
from app.validation.forward_returns import compute_forward_returns


class OutcomeAttributionDataLoader:
    def __init__(
        self,
        db: Session,
        stock_repo: StockRepository,
        market_data_repo: MarketDataRepository,
    ) -> None:
        self.db = db
        self.stock_repo = stock_repo
        self.market_data_repo = market_data_repo

    def load(
        self,
        config: OutcomeAttributionConfig,
    ) -> tuple[list[StockObservation], list[RunBenchmark]]:
        runs = self._list_runs(config)
        if not runs:
            return [], []

        run_ids = [run.id for run in runs]
        results_by_run = self._load_results(run_ids)
        snapshots_by_run = self._load_snapshots(run_ids)
        regime_by_run = self._load_regime_labels(run_ids)

        cache = MarketDataCache(self.market_data_repo)
        benchmark_cache: dict[tuple[str, date], dict[int, float | None]] = {}

        observations: list[StockObservation] = []
        benchmarks: list[RunBenchmark] = []

        for run in runs:
            regime = regime_by_run.get(run.id) or run.regime_label
            bench_key = (run.benchmark_symbol, run.as_of_date)
            if bench_key not in benchmark_cache:
                benchmark_cache[bench_key] = self._benchmark_returns(
                    cache, run.benchmark_symbol, run.as_of_date
                )
            bench_returns = benchmark_cache[bench_key]
            benchmarks.append(
                RunBenchmark(
                    run_id=run.id,
                    as_of_date=run.as_of_date,
                    benchmark_symbol=run.benchmark_symbol,
                    returns=bench_returns,
                )
            )

            snapshot_by_stock = {
                snap.stock_id: snap for snap in snapshots_by_run.get(run.id, [])
            }
            for result in results_by_run.get(run.id, []):
                returns = self._returns_from_snapshot(snapshot_by_stock.get(result.stock_id))
                observations.append(
                    StockObservation(
                        run_id=run.id,
                        as_of_date=run.as_of_date,
                        strategy_name=run.strategy_name,
                        regime_label=regime,
                        rank=result.rank,
                        returns=returns,
                    )
                )

        return observations, benchmarks

    def _list_runs(self, config: OutcomeAttributionConfig) -> list[RankingRun]:
        stmt = (
            select(RankingRun)
            .where(
                RankingRun.status == RankingRunStatus.COMPLETED.value,
                RankingRun.universe_code == config.universe_code,
                RankingRun.as_of_date >= config.start_date,
                RankingRun.as_of_date <= config.end_date,
                RankingRun.strategy_name.in_(config.strategy_names),
            )
            .order_by(RankingRun.as_of_date, RankingRun.strategy_name)
        )
        if config.strategy_version:
            stmt = stmt.where(RankingRun.strategy_version == config.strategy_version)
        return list(self.db.scalars(stmt).all())

    def _load_results(self, run_ids: list[UUID]) -> dict[UUID, list[RankingResult]]:
        rows = list(
            self.db.scalars(
                select(RankingResult)
                .where(RankingResult.ranking_run_id.in_(run_ids))
                .order_by(RankingResult.ranking_run_id, RankingResult.rank)
            ).all()
        )
        grouped: dict[UUID, list[RankingResult]] = {}
        for row in rows:
            grouped.setdefault(row.ranking_run_id, []).append(row)
        return grouped

    def _load_snapshots(self, run_ids: list[UUID]) -> dict[UUID, list[RankingPerformanceSnapshot]]:
        rows = list(
            self.db.scalars(
                select(RankingPerformanceSnapshot).where(
                    RankingPerformanceSnapshot.ranking_run_id.in_(run_ids)
                )
            ).all()
        )
        grouped: dict[UUID, list[RankingPerformanceSnapshot]] = {}
        for row in rows:
            grouped.setdefault(row.ranking_run_id, []).append(row)
        return grouped

    def _load_regime_labels(self, run_ids: list[UUID]) -> dict[UUID, str | None]:
        rows = list(
            self.db.scalars(
                select(RankingValidationReport).where(
                    RankingValidationReport.ranking_run_id.in_(run_ids)
                )
            ).all()
        )
        return {row.ranking_run_id: row.regime_label for row in rows}

    def _returns_from_snapshot(
        self, snapshot: RankingPerformanceSnapshot | None
    ) -> dict[int, float | None]:
        if snapshot is None:
            return {horizon: None for horizon in ATTRIBUTION_HORIZONS}
        return {
            5: float(snapshot.return_5d) if snapshot.return_5d is not None else None,
            10: float(snapshot.return_10d) if snapshot.return_10d is not None else None,
            20: float(snapshot.return_20d) if snapshot.return_20d is not None else None,
            60: float(snapshot.return_60d) if snapshot.return_60d is not None else None,
        }

    def _benchmark_returns(
        self,
        cache: MarketDataCache,
        benchmark_symbol: str,
        as_of_date: date,
    ) -> dict[int, float | None]:
        stock = self.stock_repo.get_by_symbol(benchmark_symbol)
        if stock is None:
            return {horizon: None for horizon in ATTRIBUTION_HORIZONS}
        through_date = as_of_date + timedelta(days=MAX_FORWARD_TRADING_DAYS * 3)
        bars = cache.load_extended_series(stock.id, through_date)
        raw = compute_forward_returns(bars, as_of_date, ATTRIBUTION_HORIZONS)
        return {
            horizon: float(value) if value is not None else None
            for horizon, value in raw.items()
        }
