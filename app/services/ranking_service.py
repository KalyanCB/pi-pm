from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import NotFoundError, RankingError
from app.core.structured_logging import log_event
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.market_data.cache import GlobalBarStore, MarketDataCache
from app.models.ranking_run import RankingRun
from app.ranking.engine import RankingEngine
from app.ranking.loader import MarketDataLoader
from app.ranking.registry import RankingStrategyRegistry
from app.ranking.weight_hashing import hash_weight_config
from app.schemas.ranking import RankingRunRequest, UniverseFilterConfigSchema
from app.services.traceability_service import TraceabilityService
from app.services.universe_filter_service import UniverseFilterService
from app.universe.models import UniverseFilterConfig
from app.validation.regimes import classify_regime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RankingRunOutcome:
    run: RankingRun
    reused: bool


class RankingService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        universe_filter_service: UniverseFilterService,
        ranking_run_repo: RankingRunRepository,
        ranking_result_repo: RankingResultRepository,
        ranking_performance_repo: RankingPerformanceRepository,
        stock_repo: StockRepository,
        universe_repo: UniverseRepository,
        strategy_registry: RankingStrategyRegistry,
        traceability_service: TraceabilityService,
    ) -> None:
        self.db = db
        self.settings = settings
        self.universe_filter_service = universe_filter_service
        self.ranking_run_repo = ranking_run_repo
        self.ranking_result_repo = ranking_result_repo
        self.ranking_performance_repo = ranking_performance_repo
        self.stock_repo = stock_repo
        self.universe_repo = universe_repo
        self.strategy_registry = strategy_registry
        self.traceability_service = traceability_service
        self.global_bar_store: GlobalBarStore | None = None

    def run_ranking(self, payload: RankingRunRequest) -> RankingRun:
        return self.run_ranking_with_outcome(payload).run

    def run_ranking_with_outcome(self, payload: RankingRunRequest) -> RankingRunOutcome:
        started = time.perf_counter()
        universe_code = payload.universe_code or self.settings.ranking_default_universe_code
        strategy_name = payload.strategy_name or self.settings.ranking_default_strategy
        strategy_version = (
            payload.strategy_version or self.settings.ranking_default_strategy_version
        )

        universe = self.universe_repo.get_by_code(universe_code)
        if universe is None:
            raise NotFoundError(f"Universe not found: {universe_code}")

        as_of_date = payload.as_of_date or date.today()
        filter_config = self._build_filter_config(payload, universe_code)
        strategy = self.strategy_registry.get(strategy_name, strategy_version)
        benchmark_symbol = (
            payload.benchmark_symbol or self.settings.ranking_default_benchmark
        ).upper()

        # Pre-flight dedup: return existing completed run for this date/strategy/universe
        # before running the engine. Prevents duplicate runs when two batch jobs overlap.
        if not payload.force_regenerate:
            pre_existing = self.ranking_run_repo.find_completed_by_date(
                as_of_date=as_of_date,
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                universe_code=universe_code,
            )
            if pre_existing is not None:
                self.traceability_service.ensure_ranking_traceability(pre_existing)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                log_event(
                    logger,
                    "ranking_completed",
                    ranking_run_id=pre_existing.id,
                    reused=True,
                    reused_reason="date_dedup",
                    ranked_stock_count=pre_existing.ranked_stock_count,
                    execution_duration_ms=elapsed_ms,
                )
                return RankingRunOutcome(pre_existing, True)

        log_event(
            logger,
            "ranking_started",
            universe_code=universe_code,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            as_of_date=as_of_date.isoformat(),
            benchmark=benchmark_symbol,
        )

        if self.global_bar_store is not None:
            market_data_cache = self.global_bar_store.as_cache(self.universe_filter_service.market_data_repo)
        else:
            market_data_cache = MarketDataCache(self.universe_filter_service.market_data_repo)

        # Bulk-preload all universe stocks in one query instead of N+1 per stock
        universe_stocks = self.universe_repo.list_stocks_in_universe(universe_code)
        all_stock_ids = [s.id for s in universe_stocks]
        market_data_cache.bulk_preload(
            all_stock_ids, as_of_date, source=filter_config.market_data_source
        )

        tradable_universe = self.universe_filter_service.build_tradable_universe(
            as_of_date, filter_config, market_data_cache
        )

        benchmark_stock = self.stock_repo.get_by_symbol(benchmark_symbol)
        benchmark_stock_id = benchmark_stock.id if benchmark_stock else None

        regime_label = self._resolve_regime_label(benchmark_stock_id, as_of_date, market_data_cache)

        engine = RankingEngine(MarketDataLoader(market_data_cache))
        output = engine.run(
            tradable_universe=tradable_universe,
            strategy=strategy,
            benchmark_symbol=benchmark_symbol,
            benchmark_stock_id=benchmark_stock_id,
            as_of_date=as_of_date,
        )

        existing = (
            None
            if payload.force_regenerate
            else self.ranking_run_repo.find_completed_by_inputs_hash(output.inputs_hash)
        )
        if existing is not None:
            self.traceability_service.ensure_ranking_traceability(existing)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                logger,
                "ranking_completed",
                ranking_run_id=existing.id,
                reused=True,
                ranked_stock_count=output.metadata.get("ranked_stock_count"),
                execution_duration_ms=elapsed_ms,
            )
            return RankingRunOutcome(existing, True)

        run = self.ranking_run_repo.create_pending(
            strategy_name=strategy.name,
            strategy_version=strategy.version,
            as_of_date=as_of_date,
            universe_code=universe_code,
            benchmark_symbol=benchmark_symbol,
            filter_config_hash=tradable_universe.filter_config_hash,
            normalization_method="percentile",
        )

        try:
            self.ranking_result_repo.save_results(run.id, output.ranked_stocks)
            self.ranking_performance_repo.create_placeholder_snapshots(
                run.id,
                [item.stock_id for item in output.ranked_stocks],
            )
            metadata = {
                **output.metadata,
                "exclusion_summary": output.exclusion_summary,
            }
            self.ranking_run_repo.complete(run, output.inputs_hash, metadata)

            effective_weights = output.metadata.get("effective_weights") or {}
            weight_hash = hash_weight_config(effective_weights) if effective_weights else None
            ranked_count = int(
                output.metadata.get("ranked_stock_count") or len(output.ranked_stocks)
            )
            universe_count = int(output.metadata.get("universe_stock_count") or 0)
            excluded_count = max(universe_count - ranked_count, 0)
            elapsed_ms = int((time.perf_counter() - started) * 1000)

            self.traceability_service.record_ranking_traceability(
                run,
                weight_config_hash=weight_hash,
                regime_label=regime_label,
                ranked_stock_count=ranked_count,
                excluded_stock_count=excluded_count,
                execution_duration_ms=elapsed_ms,
            )
            self.db.commit()
            reloaded = self.ranking_run_repo.get_by_id(run.id)
            assert reloaded is not None
            log_event(
                logger,
                "ranking_completed",
                ranking_run_id=reloaded.id,
                reused=False,
                ranked_stock_count=ranked_count,
                excluded_stock_count=excluded_count,
                execution_duration_ms=elapsed_ms,
            )
            return RankingRunOutcome(reloaded, False)
        except RankingError:
            raise
        except Exception as exc:
            self.ranking_run_repo.fail(run, str(exc))
            self.db.commit()
            raise RankingError(str(exc)) from exc

    def get_run(self, run_id: UUID) -> RankingRun:
        run = self.ranking_run_repo.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"Ranking run not found: {run_id}")
        return run

    def get_latest(
        self,
        universe_code: str | None = None,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
    ) -> RankingRun:
        run = self.ranking_run_repo.get_latest(universe_code, strategy_name, strategy_version)
        if run is None:
            raise NotFoundError("No completed ranking runs found")
        return run

    def get_top(self, run_id: UUID, limit: int = 10) -> tuple[RankingRun, list]:
        run = self.get_run(run_id)
        top = self.ranking_result_repo.list_top(run.id, limit)
        return run, top

    def _resolve_regime_label(
        self,
        benchmark_stock_id: UUID | None,
        as_of_date: date,
        cache: MarketDataCache,
    ) -> str | None:
        if benchmark_stock_id is None:
            return None
        bars = cache.load_extended_series(benchmark_stock_id, as_of_date)
        high_vol_threshold = Decimal(str(self.settings.validation_high_vol_threshold))
        regime = classify_regime(bars, as_of_date, high_vol_threshold)
        return regime.regime_label if regime else None

    def _build_filter_config(
        self, payload: RankingRunRequest, universe_code: str
    ) -> UniverseFilterConfig:
        schema: UniverseFilterConfigSchema = payload.filter_config or UniverseFilterConfigSchema(
            min_history_days=self.settings.ranking_min_history_days,
            min_avg_daily_traded_value=Decimal(
                str(self.settings.ranking_min_avg_daily_traded_value)
            ),
            min_stock_price=Decimal(str(self.settings.ranking_min_stock_price)),
            market_data_source=self.settings.ranking_market_data_source,
        )
        return UniverseFilterConfig(
            universe_code=universe_code,
            min_history_days=schema.min_history_days,
            min_avg_daily_traded_value=schema.min_avg_daily_traded_value,
            min_stock_price=schema.min_stock_price,
            require_data_status_active=schema.require_data_status_active,
            require_stock_active=schema.require_stock_active,
            market_data_source=schema.market_data_source,
        )
