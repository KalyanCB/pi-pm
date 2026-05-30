from datetime import date

from app.backtest.trading_calendar import TradingCalendar
from app.db.repositories.market_data_repository import MarketDataRepository


def test_trading_calendar_benchmark_anchored(db_session):
    repo = MarketDataRepository(db_session)
    benchmark = _stock("BENCH.NS")
    other = _stock("OTHER.NS")
    db_session.add_all([benchmark, other])
    db_session.flush()

    for day in (date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)):
        db_session.add(_bar(benchmark.id, day, 100))
    db_session.add(_bar(other.id, date(2025, 1, 7), 100))
    db_session.commit()

    calendar = TradingCalendar(repo)
    days = calendar.trading_days_in_range(
        date(2025, 1, 1),
        date(2025, 1, 31),
        universe_stock_ids=[other.id],
        benchmark_stock_id=benchmark.id,
    )

    assert days == [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)]


def test_trading_calendar_universe_fallback(db_session):
    repo = MarketDataRepository(db_session)
    stock_a = _stock("A.NS")
    stock_b = _stock("B.NS")
    db_session.add_all([stock_a, stock_b])
    db_session.flush()

    db_session.add(_bar(stock_a.id, date(2025, 2, 3), 100))
    db_session.add(_bar(stock_b.id, date(2025, 2, 4), 100))
    db_session.commit()

    calendar = TradingCalendar(repo)
    days = calendar.trading_days_in_range(
        date(2025, 2, 1),
        date(2025, 2, 28),
        universe_stock_ids=[stock_a.id, stock_b.id],
        benchmark_stock_id=None,
    )

    assert days == [date(2025, 2, 3), date(2025, 2, 4)]


def _bar(stock_id, bar_date, close):
    from datetime import UTC, datetime

    from app.models.market_data import MarketData

    return MarketData(
        stock_id=stock_id,
        date=bar_date,
        close=close,
        adj_close=close,
        volume=1_000_000,
        source="yahoo",
        ingested_at=datetime.now(UTC),
    )


def _stock(symbol: str):
    from app.core.constants import DataStatus
    from app.models.stock import Stock

    return Stock(
        symbol=symbol,
        name=symbol,
        exchange="NSE",
        data_status=DataStatus.ACTIVE.value,
        is_active=True,
    )
