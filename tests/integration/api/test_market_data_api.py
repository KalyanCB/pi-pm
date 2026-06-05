from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from app.providers.yahoo.models import YahooOHLCVBar, YahooStockMetadata


def _bars():
    bar_date = datetime.now(UTC).date() - timedelta(days=1)
    return [
        YahooOHLCVBar(
            date=bar_date,
            open=Decimal("2500"),
            high=Decimal("2520"),
            low=Decimal("2490"),
            close=Decimal("2510"),
            volume=1000000,
            adj_close=Decimal("2510"),
        )
    ]


def _benchmark_bars(count: int = 220):
    start = datetime.now(UTC).date() - timedelta(days=count - 1)
    bars: list[YahooOHLCVBar] = []
    for i in range(count):
        bar_date = start + timedelta(days=i)
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
    return bars


def test_ingest_and_read_flow(client, mock_provider):
    metadata = {
        "RELIANCE.NS": YahooStockMetadata(
            symbol="RELIANCE.NS",
            name="Reliance Industries Ltd",
            exchange="NSE",
            sector="Energy",
            industry="Oil & Gas",
        ),
        "TCS.NS": YahooStockMetadata(
            symbol="TCS.NS",
            name="Tata Consultancy Services",
            exchange="NSE",
            sector="Technology",
            industry="IT Services",
        ),
    }

    def fetch_metadata(symbol: str):
        return metadata[symbol]

    with (
        patch.object(mock_provider, "fetch_metadata", side_effect=fetch_metadata),
        patch.object(mock_provider, "fetch_history", return_value=_bars()),
    ):
        response = client.post(
            "/api/v1/market-data/ingest",
            json={"symbols": ["RELIANCE.NS", "TCS.NS"], "period": "1y"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["symbols_processed"] == 2
    assert body["rows_inserted"] == 2

    stock_response = client.get("/api/v1/stocks/RELIANCE.NS")
    assert stock_response.status_code == 200
    assert stock_response.json()["symbol"] == "RELIANCE.NS"

    md_response = client.get("/api/v1/stocks/RELIANCE.NS/market-data")
    assert md_response.status_code == 200
    assert len(md_response.json()) == 1


def test_reingest_no_duplicates(client, mock_provider):
    metadata = YahooStockMetadata(
        symbol="RELIANCE.NS",
        name="Reliance Industries Ltd",
        exchange="NSE",
        sector="Energy",
        industry="Oil & Gas",
    )

    with (
        patch.object(mock_provider, "fetch_metadata", return_value=metadata),
        patch.object(mock_provider, "fetch_history", return_value=_bars()),
    ):
        first = client.post(
            "/api/v1/market-data/ingest",
            json={"symbols": ["RELIANCE.NS"], "period": "1y"},
        )
        second = client.post(
            "/api/v1/market-data/ingest",
            json={"symbols": ["RELIANCE.NS"], "period": "1y"},
        )

    assert first.json()["rows_inserted"] == 1
    assert second.json()["rows_inserted"] == 0
    assert second.json()["rows_updated"] == 1

    md_response = client.get("/api/v1/stocks/RELIANCE.NS/market-data")
    assert len(md_response.json()) == 1


def test_unhealthy_batch_returns_207(client, mock_provider):
    from app.core.exceptions import InvalidSymbolError

    with patch.object(
        mock_provider,
        "fetch_metadata",
        side_effect=InvalidSymbolError("bad symbol"),
    ):
        response = client.post(
            "/api/v1/market-data/ingest",
            json={"symbols": ["BAD1.NS", "BAD2.NS", "BAD3.NS"], "period": "1y"},
        )

    assert response.status_code == 207
    body = response.json()
    assert body["status"] == "partial_success"
    assert body["symbols_failed"] == 3


def test_list_stocks(client, mock_provider):
    metadata = YahooStockMetadata(
        symbol="BEL.NS",
        name="Bharat Electronics",
        exchange="NSE",
        sector="Industrials",
        industry="Defense",
    )

    with (
        patch.object(mock_provider, "fetch_metadata", return_value=metadata),
        patch.object(mock_provider, "fetch_history", return_value=_bars()),
    ):
        client.post(
            "/api/v1/market-data/ingest",
            json={"symbols": ["BEL.NS"], "period": "1y"},
        )

    response = client.get("/api/v1/stocks")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_ingest_benchmark_index_symbol(client, mock_provider):
    metadata = YahooStockMetadata(
        symbol="^NSEI",
        name="NIFTY 50",
        exchange="NSE",
        sector=None,
        industry=None,
    )

    with (
        patch.object(mock_provider, "fetch_metadata", return_value=metadata),
        patch.object(mock_provider, "fetch_history", return_value=_benchmark_bars()),
    ):
        response = client.post(
            "/api/v1/market-data/ingest",
            json={"symbols": ["^NSEI"], "period": "5y"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["symbols_processed"] == 1
    assert body["symbols_failed"] == 0
    assert body["rows_inserted"] == 220

    stocks = client.get("/api/v1/stocks")
    assert stocks.status_code == 200
    assert any(stock["symbol"] == "^NSEI" for stock in stocks.json())


def test_ingest_rejects_invalid_index_symbol(client):
    response = client.post(
        "/api/v1/market-data/ingest",
        json={"symbols": ["^"], "period": "5y"},
    )
    assert response.status_code == 422
