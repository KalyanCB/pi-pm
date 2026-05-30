from datetime import UTC, date, datetime, timedelta

from app.core.constants import DataStatus
from app.models.market_data import MarketData
from app.models.stock import Stock
from app.models.stock_universe import StockUniverse
from app.models.universe_membership import UniverseMembership
from tests.integration.api.test_rankings_api import seed_benchmark


def seed_multi_day_universe(db_session, start: date, days: int):
    """Seed universe with enough history for ranking on each day in [start, start+days)."""
    universe = StockUniverse(code="PI_PM_CORE", name="Core", is_active=True)
    db_session.add(universe)
    db_session.flush()

    as_of_end = start + timedelta(days=days - 1)
    history_start = start - timedelta(days=250)

    symbols = ["AAA.NS", "BBB.NS", "CCC.NS"]
    for idx, symbol in enumerate(symbols):
        stock = Stock(
            symbol=symbol,
            name=symbol,
            exchange="NSE",
            data_status=DataStatus.ACTIVE.value,
            is_active=True,
        )
        db_session.add(stock)
        db_session.flush()
        db_session.add(
            UniverseMembership(universe_id=universe.id, stock_id=stock.id, removed_at=None)
        )

        bar_date = history_start
        price = 100 + idx * 10
        while bar_date <= as_of_end:
            db_session.add(
                MarketData(
                    stock_id=stock.id,
                    date=bar_date,
                    close=price,
                    adj_close=price,
                    volume=1_000_000,
                    source="yahoo",
                    ingested_at=datetime.now(UTC),
                )
            )
            price += 1
            bar_date += timedelta(days=1)

    seed_benchmark(db_session, as_of_end)
    db_session.commit()


def test_generate_rankings_api(client, db_session):
    start = date(2025, 5, 1)
    seed_multi_day_universe(db_session, start, days=5)

    response = client.post(
        "/api/v1/backtest/generate-rankings",
        json={
            "universe_code": "PI_PM_CORE",
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=4)).isoformat(),
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
            "benchmark_symbol": "^NSEI",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["trading_days_total"] == 5
    assert body["runs_created"] == 5
    assert body["runs_reused"] == 0
    assert body["runs_failed"] == 0


def test_generate_rankings_idempotent(client, db_session):
    start = date(2025, 5, 10)
    seed_multi_day_universe(db_session, start, days=3)
    payload = {
        "universe_code": "PI_PM_CORE",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=2)).isoformat(),
        "strategy_name": "momentum_v1",
        "strategy_version": "1.0.0",
        "benchmark_symbol": "^NSEI",
    }

    first = client.post("/api/v1/backtest/generate-rankings", json=payload)
    second = client.post("/api/v1/backtest/generate-rankings", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["runs_created"] == 3
    assert second.json()["runs_created"] == 0
    assert second.json()["runs_reused"] == 3
