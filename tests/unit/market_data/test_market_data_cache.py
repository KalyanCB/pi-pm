from datetime import UTC, date, datetime, timedelta

from app.core.constants import DataStatus
from app.db.repositories.market_data_repository import MarketDataRepository
from app.market_data.cache import MarketDataCache
from app.models.market_data import MarketData
from app.models.stock import Stock


def test_market_data_cache_reuses_loaded_bars(db_session):
    as_of = date(2025, 1, 31)
    stock = Stock(
        symbol="CACHE.NS",
        name="Cache",
        exchange="NSE",
        data_status=DataStatus.ACTIVE.value,
        is_active=True,
    )
    db_session.add(stock)
    db_session.flush()

    for i in range(5):
        db_session.add(
            MarketData(
                stock_id=stock.id,
                date=as_of - timedelta(days=4 - i),
                close=100 + i,
                adj_close=100 + i,
                volume=1_000_000,
                source="yahoo",
                ingested_at=datetime.now(UTC),
            )
        )
    db_session.commit()

    repo = MarketDataRepository(db_session)
    cache = MarketDataCache(repo)

    first = cache.load_series(stock.id, as_of)
    second = cache.load_series(stock.id, as_of)

    assert first == second
    assert len(first) == 5
    assert len(cache._bars) == 1
