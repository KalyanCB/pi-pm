from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.core.constants import (
    EXCLUSION_INSUFFICIENT_TRADED_VALUE,
    EXCLUSION_MIN_PRICE_FAILED,
    DataStatus,
)
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.market_data.cache import MarketDataCache
from app.models.market_data import MarketData
from app.models.stock import Stock
from app.models.stock_universe import StockUniverse
from app.models.universe_membership import UniverseMembership
from app.universe.filter_engine import UniverseFilterEngine
from app.universe.models import UniverseFilterConfig


def _seed_stock(db_session, symbol: str, price: float, volume: int, days: int, as_of: date):
    stock = Stock(
        symbol=symbol,
        name=symbol,
        exchange="NSE",
        data_status=DataStatus.ACTIVE.value,
        is_active=True,
    )
    db_session.add(stock)
    db_session.flush()

    for i in range(days):
        bar_date = as_of - timedelta(days=days - i - 1)
        db_session.add(
            MarketData(
                stock_id=stock.id,
                date=bar_date,
                close=price,
                adj_close=price,
                volume=volume,
                source="yahoo",
                ingested_at=datetime.now(UTC),
            )
        )
    return stock


def test_universe_filter_traded_value_and_price(db_session):
    as_of = date(2025, 1, 31)
    universe = StockUniverse(code="PI_PM_CORE", name="Core", is_active=True)
    db_session.add(universe)
    db_session.flush()

    good = _seed_stock(db_session, "GOOD.NS", price=200, volume=200_000, days=70, as_of=as_of)
    low_price = _seed_stock(db_session, "LOWP.NS", price=10, volume=500_000, days=70, as_of=as_of)
    low_liq = _seed_stock(db_session, "LOWL.NS", price=200, volume=100, days=70, as_of=as_of)

    for stock in (good, low_price, low_liq):
        db_session.add(
            UniverseMembership(universe_id=universe.id, stock_id=stock.id, removed_at=None)
        )
    db_session.commit()

    engine = UniverseFilterEngine(
        UniverseRepository(db_session),
        MarketDataCache(MarketDataRepository(db_session)),
    )
    config = UniverseFilterConfig(
        universe_code="PI_PM_CORE",
        min_history_days=63,
        min_avg_daily_traded_value=Decimal("10000000"),
        min_stock_price=Decimal("50"),
    )
    result = engine.build_tradable_universe(as_of, config)

    assert len(result.included) == 1
    assert result.included[0].symbol == "GOOD.NS"
    assert result.exclusion_summary[EXCLUSION_MIN_PRICE_FAILED] == 1
    assert result.exclusion_summary[EXCLUSION_INSUFFICIENT_TRADED_VALUE] == 1
