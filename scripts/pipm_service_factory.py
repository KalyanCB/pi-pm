"""Shared service wiring for CLI scripts and batch orchestration."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.constants import DEFAULT_BENCHMARK_SYMBOL
from app.db.repositories.exit_research_metric_repository import ExitResearchMetricRepository
from app.db.repositories.exit_research_run_repository import ExitResearchRunRepository
from app.db.repositories.factor_performance_metric_repository import (
    FactorPerformanceMetricRepository,
)
from app.db.repositories.ingestion_batch_repository import IngestionBatchRepository
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_factor_contribution_repository import (
    RankingFactorContributionRepository,
)
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.db.session import Session
from app.providers.yahoo.client import YahooFinanceProvider
from app.ranking.registry import RankingStrategyRegistry
from app.services.backtest_service import BacktestService
from app.services.exit_research_service import ExitResearchService
from app.services.factor_predictive_power_service import FactorPredictivePowerService
from app.services.market_data_service import MarketDataService
from app.services.ranking_service import RankingService
from app.services.signal_validation_service import SignalValidationService
from app.services.traceability_service import TraceabilityService
from app.services.universe_filter_service import UniverseFilterService


def build_pipm_services(db: Session) -> dict:
    settings = get_settings()
    stock_repo = StockRepository(db)
    market_data_repo = MarketDataRepository(db)
    ingestion_run_repo = IngestionRunRepository(db)
    universe_repo = UniverseRepository(db)
    provider = YahooFinanceProvider(timeout_seconds=settings.yahoo_request_timeout_seconds)
    lineage_repo = RunLineageRepository(db)
    market_data_service = MarketDataService(
        db,
        stock_repo,
        market_data_repo,
        ingestion_run_repo,
        IngestionBatchRepository(db),
        lineage_repo,
        provider,
    )
    traceability_service = TraceabilityService(
        db,
        RankingFactorContributionRepository(db),
        ValidationMetricsRepository(db),
        lineage_repo,
        ingestion_run_repo,
    )
    universe_filter_service = UniverseFilterService(universe_repo, market_data_repo)
    strategy_registry = RankingStrategyRegistry()
    ranking_service = RankingService(
        db,
        settings,
        universe_filter_service,
        RankingRunRepository(db),
        RankingResultRepository(db),
        RankingPerformanceRepository(db),
        stock_repo,
        universe_repo,
        strategy_registry,
        traceability_service,
    )
    backtest_service = BacktestService(
        db,
        settings,
        ranking_service,
        universe_repo,
        stock_repo,
        market_data_repo,
    )
    validation_service = SignalValidationService(
        db,
        settings,
        RankingRunRepository(db),
        RankingResultRepository(db),
        RankingPerformanceRepository(db),
        RankingValidationRepository(db),
        stock_repo,
        market_data_repo,
        traceability_service,
    )
    factor_metric_repo = FactorPerformanceMetricRepository(db)
    factor_service = FactorPredictivePowerService(
        db,
        factor_metric_repo,
        RankingRunRepository(db),
        RankingResultRepository(db),
        RankingValidationRepository(db),
        traceability_service,
    )
    exit_service = ExitResearchService(
        db,
        ExitResearchRunRepository(db),
        ExitResearchMetricRepository(db),
    )
    return {
        "db": db,
        "settings": settings,
        "stock_repo": stock_repo,
        "universe_repo": universe_repo,
        "market_data_service": market_data_service,
        "ranking_service": ranking_service,
        "backtest_service": backtest_service,
        "validation_service": validation_service,
        "factor_service": factor_service,
        "exit_service": exit_service,
        "default_benchmark": DEFAULT_BENCHMARK_SYMBOL,
    }
