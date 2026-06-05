from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.core.constants import RankingRunStatus
from app.market_data.cache import MarketDataCache
from app.models.ranking_run import RankingRun
from app.outcome_attribution.constants import ATTRIBUTION_HORIZONS
from app.outcome_attribution.data_loader import OutcomeAttributionDataLoader
from app.outcome_attribution.models import OutcomeAttributionConfig, RunBenchmark
from app.ranking_research.models import EnrichedStockObservation, RankingResearchConfig
from app.validation.constants import MAX_FORWARD_TRADING_DAYS
from app.validation.forward_returns import compute_forward_returns


class RankingResearchDataLoader(OutcomeAttributionDataLoader):
    """Read-only loader: ranking runs, results, snapshots, validation regime."""

    def load_enriched(
        self,
        config: RankingResearchConfig,
    ) -> tuple[list[EnrichedStockObservation], list[RunBenchmark]]:
        runs = self._list_runs(config)
        if not runs:
            return [], []

        run_ids = [run.id for run in runs]
        results_by_run = self._load_results(run_ids)
        snapshots_by_run = self._load_snapshots(run_ids)
        regime_by_run = self._load_regime_labels(run_ids)

        cache = MarketDataCache(self.market_data_repo)
        benchmark_cache: dict[tuple[str, date], dict[int, float | None]] = {}

        observations: list[EnrichedStockObservation] = []
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

            snapshot_by_stock = {snap.stock_id: snap for snap in snapshots_by_run.get(run.id, [])}
            for result in results_by_run.get(run.id, []):
                returns = self._returns_from_snapshot(snapshot_by_stock.get(result.stock_id))
                observations.append(
                    EnrichedStockObservation(
                        run_id=run.id,
                        as_of_date=run.as_of_date,
                        strategy_name=run.strategy_name,
                        regime_label=regime,
                        stock_id=result.stock_id,
                        rank=result.rank,
                        score=float(result.score),
                        score_components=result.score_components,
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
            horizon: float(value) if value is not None else None for horizon, value in raw.items()
        }
