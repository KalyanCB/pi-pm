from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from app.core.constants import DataStatus
from app.models.market_data import MarketData
from app.models.stock import Stock
from app.models.stock_universe import StockUniverse
from app.models.universe_membership import UniverseMembership
from app.providers.yahoo.models import YahooOHLCVBar, YahooStockMetadata


def seed_ranking_universe(db_session, as_of: date):
    universe = StockUniverse(code="PI_PM_CORE", name="Core", is_active=True)
    db_session.add(universe)
    db_session.flush()

    symbols = ["AAA.NS", "BBB.NS", "CCC.NS"]
    stocks = []
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
        for i in range(220):
            bar_date = as_of - timedelta(days=219 - i)
            close = 100 + idx * 10 + (i * 2)
            db_session.add(
                MarketData(
                    stock_id=stock.id,
                    date=bar_date,
                    close=close,
                    adj_close=close,
                    volume=1_000_000 + i * 1000,
                    source="yahoo",
                    ingested_at=datetime.now(UTC),
                )
            )
        stocks.append(stock)
    db_session.commit()
    return stocks


def seed_benchmark(db_session, as_of: date, symbol: str = "^NSEI"):
    stock = Stock(
        symbol=symbol,
        name=symbol,
        exchange="NSE",
        data_status=DataStatus.ACTIVE.value,
        is_active=True,
    )
    db_session.add(stock)
    db_session.flush()

    for i in range(220):
        bar_date = as_of - timedelta(days=219 - i)
        close = 100 + i
        db_session.add(
            MarketData(
                stock_id=stock.id,
                date=bar_date,
                close=close,
                adj_close=close,
                volume=500_000 + i * 500,
                source="yahoo",
                ingested_at=datetime.now(UTC),
            )
        )
    db_session.commit()
    return stock


def test_ranking_api_flow(client, db_session):
    as_of = date(2025, 6, 1)
    seed_ranking_universe(db_session, as_of)

    response = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["results_count"] == 3
    assert body["metadata"] is not None
    assert "exclusion_summary" in body["metadata"]

    run_id = body["id"]
    latest = client.get("/api/v1/rankings/latest?universe_code=PI_PM_CORE")
    assert latest.status_code == 200

    top = client.get(f"/api/v1/rankings/{run_id}/top?n=2")
    assert top.status_code == 200
    assert len(top.json()["top"]) == 2

    rerun = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
        },
    )
    assert rerun.status_code == 201
    assert rerun.json()["inputs_hash"] == body["inputs_hash"]


def test_ranking_with_benchmark_present(client, db_session):
    as_of = date(2025, 6, 1)
    seed_ranking_universe(db_session, as_of)
    seed_benchmark(db_session, as_of)

    response = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
            "benchmark_symbol": "^NSEI",
        },
    )
    assert response.status_code == 201
    body = response.json()
    metadata = body["metadata"]

    assert metadata["benchmark_available"] is True
    assert metadata.get("weight_adjustment_reason") is None
    assert metadata["effective_weights"] == {
        "volatility_adjusted_momentum": "0.40000000",
        "volume_expansion": "0.25000000",
        "trend_quality": "0.20000000",
        "relative_strength": "0.15000000",
    }
    assert body["results_count"] == 3
    for result in body["results"]:
        assert "relative_strength" in result["score_components"]


def test_ranking_with_ingested_benchmark(client, db_session, mock_provider):
    as_of = date(2025, 6, 1)
    seed_ranking_universe(db_session, as_of)

    metadata = YahooStockMetadata(
        symbol="^NSEI",
        name="NIFTY 50",
        exchange="NSE",
        sector=None,
        industry=None,
    )
    bars = []
    for i in range(220):
        bar_date = as_of - timedelta(days=219 - i)
        close = Decimal("100") + Decimal(i)
        bars.append(
            YahooOHLCVBar(
                date=bar_date,
                open=close,
                high=close + Decimal("1"),
                low=close - Decimal("1"),
                close=close,
                volume=500_000 + i,
                adj_close=close,
            )
        )

    with patch.object(mock_provider, "fetch_metadata", return_value=metadata), patch.object(
        mock_provider, "fetch_history", return_value=bars
    ):
        ingest = client.post(
            "/api/v1/market-data/ingest",
            json={"symbols": ["^NSEI"], "period": "5y"},
        )
    assert ingest.status_code == 200

    response = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
            "benchmark_symbol": "^NSEI",
        },
    )
    assert response.status_code == 201
    body = response.json()
    metadata_out = body["metadata"]

    assert metadata_out["benchmark_available"] is True
    assert metadata_out.get("weight_adjustment_reason") is None
    for result in body["results"]:
        assert "relative_strength" in result["score_components"]


def test_empty_universe_ranking(client, db_session):
    as_of = date(2025, 6, 1)
    universe = StockUniverse(code="PI_PM_CORE", name="Core", is_active=True)
    db_session.add(universe)
    db_session.commit()

    response = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "momentum_v1",
            "strategy_version": "1.0.0",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["results_count"] == 0
    assert body["results"] == []
    assert body["metadata"]["ranked_stock_count"] == 0


def test_ranking_with_default_config(client, db_session):
    as_of = date(2025, 6, 1)
    seed_ranking_universe(db_session, as_of)

    response = client.post(
        "/api/v1/rankings/run",
        json={"as_of_date": as_of.isoformat()},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["universe_code"] == "PI_PM_CORE"
    assert body["strategy_name"] == "momentum_v1"


def test_breakout_v1_ranking_api_flow(client, db_session):
    as_of = date(2025, 6, 1)
    from app.core.constants import DataStatus
    from app.models.market_data import MarketData
    from app.models.stock import Stock
    from app.models.stock_universe import StockUniverse
    from app.models.universe_membership import UniverseMembership
    from datetime import UTC, datetime, timedelta

    universe = StockUniverse(code="PI_PM_CORE", name="Core", is_active=True)
    db_session.add(universe)
    db_session.flush()

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
        for i in range(280):
            bar_date = as_of - timedelta(days=279 - i)
            close = 100 + idx * 10 + (i * 0.5)
            db_session.add(
                MarketData(
                    stock_id=stock.id,
                    date=bar_date,
                    close=close,
                    adj_close=close,
                    volume=1_000_000 + i * 1000,
                    source="yahoo",
                    ingested_at=datetime.now(UTC),
                )
            )
    benchmark = Stock(
        symbol="^NSEI",
        name="^NSEI",
        exchange="NSE",
        data_status=DataStatus.ACTIVE.value,
        is_active=True,
    )
    db_session.add(benchmark)
    db_session.flush()
    for i in range(280):
        bar_date = as_of - timedelta(days=279 - i)
        close = 100 + i * 0.5
        db_session.add(
            MarketData(
                stock_id=benchmark.id,
                date=bar_date,
                close=close,
                adj_close=close,
                volume=500_000 + i * 500,
                source="yahoo",
                ingested_at=datetime.now(UTC),
            )
        )
    db_session.commit()

    response = client.post(
        "/api/v1/rankings/run",
        json={
            "universe_code": "PI_PM_CORE",
            "as_of_date": as_of.isoformat(),
            "strategy_name": "breakout_v1",
            "strategy_version": "1.0.0",
            "benchmark_symbol": "^NSEI",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["strategy_name"] == "breakout_v1"
    assert body["results_count"] == 3
    assert body["metadata"]["benchmark_available"] is True
    factor_names = {
        name
        for result in body["results"]
        for name in (result.get("score_components") or {})
    }
    assert "high_proximity" in factor_names
    assert "consolidation_breakout" in factor_names
