import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
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
from app.main import create_app
from app.providers.yahoo.client import YahooFinanceProvider
from app.services.market_data_service import MarketDataService
from app.services.stock_service import StockService
from app.services.traceability_service import TraceabilityService


@pytest.fixture
def traceability_service(db_session: Session) -> TraceabilityService:
    return TraceabilityService(
        db_session,
        RankingFactorContributionRepository(db_session),
        ValidationMetricsRepository(db_session),
        RunLineageRepository(db_session),
        IngestionRunRepository(db_session),
    )


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(PGUUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "CHAR(36)"


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    session_factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def stock_repo(db_session: Session) -> StockRepository:
    return StockRepository(db_session)


@pytest.fixture
def universe_repo(db_session: Session) -> UniverseRepository:
    return UniverseRepository(db_session)


@pytest.fixture
def market_data_repo(db_session: Session) -> MarketDataRepository:
    return MarketDataRepository(db_session)


@pytest.fixture
def ingestion_run_repo(db_session: Session) -> IngestionRunRepository:
    return IngestionRunRepository(db_session)


@pytest.fixture
def stock_service(stock_repo: StockRepository) -> StockService:
    return StockService(stock_repo)


@pytest.fixture
def mock_provider():
    return YahooFinanceProvider()


@pytest.fixture
def market_data_service(
    db_session: Session,
    stock_repo: StockRepository,
    market_data_repo: MarketDataRepository,
    ingestion_run_repo: IngestionRunRepository,
    mock_provider: YahooFinanceProvider,
) -> MarketDataService:
    return MarketDataService(
        db_session,
        stock_repo,
        market_data_repo,
        ingestion_run_repo,
        IngestionBatchRepository(db_session),
        RunLineageRepository(db_session),
        mock_provider,
    )


@pytest.fixture
def client(db_session: Session, mock_provider: YahooFinanceProvider):
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_provider():
        return mock_provider

    from app.api import deps

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_yahoo_provider] = override_provider

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
