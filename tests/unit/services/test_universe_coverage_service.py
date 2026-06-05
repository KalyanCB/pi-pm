from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.constants import DataStatus
from app.models.market_data import MarketData
from app.models.stock import Stock
from app.models.stock_universe import StockUniverse
from app.models.universe_membership import UniverseMembership
from app.services.universe_coverage_service import UniverseCoverageService


@pytest.fixture
def coverage_universe(db_session, universe_repo):
    universe = StockUniverse(code="NIFTY_500", name="NIFTY 500", is_active=True)
    db_session.add(universe)
    db_session.flush()

    stock = Stock(
        symbol="RELIANCE.NS",
        name="Reliance",
        exchange="NSE",
        data_status=DataStatus.ACTIVE.value,
    )
    db_session.add(stock)
    db_session.flush()
    db_session.add(UniverseMembership(universe_id=universe.id, stock_id=stock.id))
    db_session.flush()
    return universe


def test_coverage_counts_breakout_history(
    db_session,
    stock_repo,
    universe_repo,
    market_data_repo,
    coverage_universe,
) -> None:
    stock = stock_repo.get_by_symbol("RELIANCE.NS")
    assert stock is not None
    for offset in range(260):
        db_session.add(
            MarketData(
                stock_id=stock.id,
                date=date(2024, 1, 1) + timedelta(days=offset),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0 + offset * 0.01,
                volume=1_000_000,
                source="yahoo",
                ingested_at=datetime.now(UTC),
            )
        )
    db_session.flush()

    service = UniverseCoverageService(stock_repo, universe_repo, market_data_repo)
    report = service.build_report("NIFTY_500", date(2024, 12, 31))

    assert report.membership_count == 1
    assert report.stocks_with_breakout_history == 1
    assert report.stocks_with_filter_history == 1
