from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.db.session import get_db as _get_db
from app.providers.yahoo.client import YahooFinanceProvider
from app.ranking.registry import RankingStrategyRegistry
from app.services.backtest_service import BacktestService
from app.services.market_data_service import MarketDataService
from app.services.ranking_service import RankingService
from app.services.signal_validation_service import SignalValidationService
from app.services.stock_service import StockService
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
    provider: YahooFinanceProvider = Depends(get_yahoo_provider),
) -> MarketDataService:
    return MarketDataService(db, stock_repo, market_data_repo, ingestion_run_repo, provider)


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
    )


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
