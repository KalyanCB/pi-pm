from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.repositories.experiment_run_repository import ExperimentRunRepository
from app.db.repositories.full_universe_validation_repository import (
    FullUniverseValidationRepository,
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
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.db.session import get_db as _get_db
from app.providers.yahoo.client import YahooFinanceProvider
from app.ranking.registry import RankingStrategyRegistry
from app.services.backtest_service import BacktestService
from app.services.experiment_service import ExperimentService
from app.services.full_universe_validation_service import FullUniverseValidationService
from app.services.market_data_service import MarketDataService
from app.services.observability_service import ObservabilityService
from app.services.ranking_service import RankingService
from app.services.regime_analytics_service import RegimeAnalyticsService
from app.services.signal_validation_service import SignalValidationService
from app.services.stock_service import StockService
from app.services.traceability_service import TraceabilityService
from app.services.universe_filter_service import UniverseFilterService


def get_settings_dep() -> Settings:
    return get_settings()


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


def get_stock_repository(db: Session = Depends(get_db)) -> StockRepository:
    return StockRepository(db)


def get_market_data_repository(db: Session = Depends(get_db)) -> MarketDataRepository:
    return MarketDataRepository(db)


def get_ingestion_run_repository(db: Session = Depends(get_db)) -> IngestionRunRepository:
    return IngestionRunRepository(db)


def get_ingestion_batch_repository(db: Session = Depends(get_db)) -> IngestionBatchRepository:
    return IngestionBatchRepository(db)


def get_run_lineage_repository(db: Session = Depends(get_db)) -> RunLineageRepository:
    return RunLineageRepository(db)


def get_ranking_factor_contribution_repository(
    db: Session = Depends(get_db),
) -> RankingFactorContributionRepository:
    return RankingFactorContributionRepository(db)


def get_validation_metrics_repository(
    db: Session = Depends(get_db),
) -> ValidationMetricsRepository:
    return ValidationMetricsRepository(db)


def get_experiment_run_repository(db: Session = Depends(get_db)) -> ExperimentRunRepository:
    return ExperimentRunRepository(db)


def get_regime_analytics_repository(db: Session = Depends(get_db)) -> RegimeAnalyticsRepository:
    return RegimeAnalyticsRepository(db)


def get_universe_repository(db: Session = Depends(get_db)) -> UniverseRepository:
    return UniverseRepository(db)


def get_yahoo_provider(settings: Settings = Depends(get_settings_dep)) -> YahooFinanceProvider:
    return YahooFinanceProvider(timeout_seconds=settings.yahoo_request_timeout_seconds)


def get_stock_service(stock_repo: StockRepository = Depends(get_stock_repository)) -> StockService:
    return StockService(stock_repo)


def get_market_data_service(
    db: Session = Depends(get_db),
    stock_repo: StockRepository = Depends(get_stock_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
    ingestion_run_repo: IngestionRunRepository = Depends(get_ingestion_run_repository),
    ingestion_batch_repo: IngestionBatchRepository = Depends(get_ingestion_batch_repository),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
    provider: YahooFinanceProvider = Depends(get_yahoo_provider),
) -> MarketDataService:
    return MarketDataService(
        db,
        stock_repo,
        market_data_repo,
        ingestion_run_repo,
        ingestion_batch_repo,
        lineage_repo,
        provider,
    )


def get_universe_filter_service(
    universe_repo: UniverseRepository = Depends(get_universe_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
) -> UniverseFilterService:
    return UniverseFilterService(universe_repo, market_data_repo)


def get_ranking_strategy_registry() -> RankingStrategyRegistry:
    return RankingStrategyRegistry()


def get_ranking_run_repository(db: Session = Depends(get_db)) -> RankingRunRepository:
    return RankingRunRepository(db)


def get_ranking_result_repository(db: Session = Depends(get_db)) -> RankingResultRepository:
    return RankingResultRepository(db)


def get_ranking_performance_repository(
    db: Session = Depends(get_db),
) -> RankingPerformanceRepository:
    return RankingPerformanceRepository(db)


def get_traceability_service(
    db: Session = Depends(get_db),
    factor_contribution_repo: RankingFactorContributionRepository = Depends(
        get_ranking_factor_contribution_repository
    ),
    validation_metrics_repo: ValidationMetricsRepository = Depends(get_validation_metrics_repository),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
    ingestion_run_repo: IngestionRunRepository = Depends(get_ingestion_run_repository),
) -> TraceabilityService:
    return TraceabilityService(
        db,
        factor_contribution_repo,
        validation_metrics_repo,
        lineage_repo,
        ingestion_run_repo,
    )


def get_ranking_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    universe_filter_service: UniverseFilterService = Depends(get_universe_filter_service),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    ranking_result_repo: RankingResultRepository = Depends(get_ranking_result_repository),
    ranking_performance_repo: RankingPerformanceRepository = Depends(
        get_ranking_performance_repository
    ),
    stock_repo: StockRepository = Depends(get_stock_repository),
    universe_repo: UniverseRepository = Depends(get_universe_repository),
    strategy_registry: RankingStrategyRegistry = Depends(get_ranking_strategy_registry),
    traceability_service: TraceabilityService = Depends(get_traceability_service),
) -> RankingService:
    return RankingService(
        db,
        settings,
        universe_filter_service,
        ranking_run_repo,
        ranking_result_repo,
        ranking_performance_repo,
        stock_repo,
        universe_repo,
        strategy_registry,
        traceability_service,
    )


def get_ranking_validation_repository(
    db: Session = Depends(get_db),
) -> RankingValidationRepository:
    return RankingValidationRepository(db)


def get_signal_validation_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    ranking_result_repo: RankingResultRepository = Depends(get_ranking_result_repository),
    ranking_performance_repo: RankingPerformanceRepository = Depends(
        get_ranking_performance_repository
    ),
    validation_repo: RankingValidationRepository = Depends(get_ranking_validation_repository),
    stock_repo: StockRepository = Depends(get_stock_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
    traceability_service: TraceabilityService = Depends(get_traceability_service),
) -> SignalValidationService:
    return SignalValidationService(
        db,
        settings,
        ranking_run_repo,
        ranking_result_repo,
        ranking_performance_repo,
        validation_repo,
        stock_repo,
        market_data_repo,
        traceability_service,
    )


def get_observability_service(
    db: Session = Depends(get_db),
    ingestion_batch_repo: IngestionBatchRepository = Depends(get_ingestion_batch_repository),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    experiment_run_repo: ExperimentRunRepository = Depends(get_experiment_run_repository),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
) -> ObservabilityService:
    return ObservabilityService(
        db,
        ingestion_batch_repo,
        ranking_run_repo,
        experiment_run_repo,
        lineage_repo,
    )


def get_experiment_service(
    db: Session = Depends(get_db),
    experiment_run_repo: ExperimentRunRepository = Depends(get_experiment_run_repository),
) -> ExperimentService:
    return ExperimentService(db, experiment_run_repo)


def get_regime_analytics_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    regime_repo: RegimeAnalyticsRepository = Depends(get_regime_analytics_repository),
    stock_repo: StockRepository = Depends(get_stock_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
) -> RegimeAnalyticsService:
    return RegimeAnalyticsService(db, settings, regime_repo, stock_repo, market_data_repo)


def get_backtest_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    ranking_service: RankingService = Depends(get_ranking_service),
    universe_repo: UniverseRepository = Depends(get_universe_repository),
    stock_repo: StockRepository = Depends(get_stock_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
) -> BacktestService:
    return BacktestService(
        db,
        settings,
        ranking_service,
        universe_repo,
        stock_repo,
        market_data_repo,
    )


def get_full_universe_validation_repository(
    db: Session = Depends(get_db),
) -> FullUniverseValidationRepository:
    return FullUniverseValidationRepository(db)


def get_full_universe_validation_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    campaign_repo: FullUniverseValidationRepository = Depends(
        get_full_universe_validation_repository
    ),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    backtest_service: BacktestService = Depends(get_backtest_service),
    signal_validation_service: SignalValidationService = Depends(get_signal_validation_service),
) -> FullUniverseValidationService:
    return FullUniverseValidationService(
        db,
        settings,
        campaign_repo,
        ranking_run_repo,
        backtest_service,
        signal_validation_service,
    )
