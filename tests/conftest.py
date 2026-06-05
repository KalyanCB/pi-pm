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
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.main import create_app
from app.auth.constants import UserRole
from app.auth.password import hash_password
from app.db.repositories.auth_repository import (
    PortfolioRepository,
    UserPortfolioRepository,
    UserPreferenceRepository,
    UserRepository,
)
from app.models.auth import User, UserPortfolioMembership, Portfolio  # noqa: F401
from app.models.stock_setup_research import (  # noqa: F401
    StockSetupResearch,
    StockSetupResearchMetric,
)
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


@pytest.fixture(autouse=True)
def auth_bypass(monkeypatch):
    """Disable JWT enforcement for existing test suite."""
    monkeypatch.setenv("AUTH_BYPASS_FOR_TESTS", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def user_a(db_session: Session) -> User:
    users = UserRepository(db_session)
    portfolios = PortfolioRepository(db_session)
    memberships = UserPortfolioRepository(db_session)
    prefs = UserPreferenceRepository(db_session)

    user = users.create(
        email="alice@example.com",
        password_hash=hash_password("password123"),
        display_name="Alice",
    )
    prefs.create_default(user.id)
    portfolio = portfolios.create(name="Alice Portfolio", slug="alice-portfolio")
    memberships.create_membership(user_id=user.id, portfolio_id=portfolio.id, role=UserRole.OWNER)
    db_session.commit()
    user._test_portfolio_id = portfolio.id  # type: ignore[attr-defined]
    return user


@pytest.fixture
def user_b(db_session: Session) -> User:
    users = UserRepository(db_session)
    portfolios = PortfolioRepository(db_session)
    memberships = UserPortfolioRepository(db_session)
    prefs = UserPreferenceRepository(db_session)

    user = users.create(
        email="bob@example.com",
        password_hash=hash_password("password123"),
        display_name="Bob",
    )
    prefs.create_default(user.id)
    portfolio = portfolios.create(name="Bob Portfolio", slug="bob-portfolio")
    memberships.create_membership(user_id=user.id, portfolio_id=portfolio.id, role=UserRole.OWNER)
    db_session.commit()
    user._test_portfolio_id = portfolio.id  # type: ignore[attr-defined]
    return user


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
