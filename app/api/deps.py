from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.db.session import get_db as _get_db
from app.providers.yahoo.client import YahooFinanceProvider
from app.services.market_data_service import MarketDataService
from app.services.stock_service import StockService


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
