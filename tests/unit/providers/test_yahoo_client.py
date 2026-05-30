from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.core.constants import IngestPeriod
from app.core.exceptions import InvalidSymbolError, ProviderError
from app.providers.yahoo.client import YahooFinanceProvider
from app.providers.yahoo.models import YahooOHLCVBar, YahooStockMetadata


@pytest.fixture
def sample_metadata() -> YahooStockMetadata:
    return YahooStockMetadata(
        symbol="RELIANCE.NS",
        name="Reliance Industries Ltd",
        exchange="NSE",
        sector="Energy",
        industry="Oil & Gas",
    )


@pytest.fixture
def sample_bars() -> list[YahooOHLCVBar]:
    return [
        YahooOHLCVBar(
            date=date(2024, 1, 2),
            open=Decimal("2500"),
            high=Decimal("2520"),
            low=Decimal("2490"),
            close=Decimal("2510"),
            volume=1000000,
            adj_close=Decimal("2510"),
        )
    ]


def test_fetch_metadata_success(sample_metadata):
    provider = YahooFinanceProvider()
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "longName": sample_metadata.name,
        "exchange": "NSI",
        "sector": sample_metadata.sector,
        "industry": sample_metadata.industry,
    }

    with patch("app.providers.yahoo.client.yf.Ticker", return_value=mock_ticker):
        result = provider.fetch_metadata("RELIANCE.NS")

    assert result.symbol == "RELIANCE.NS"
    assert result.name == sample_metadata.name


def test_fetch_metadata_invalid_symbol():
    provider = YahooFinanceProvider()
    mock_ticker = MagicMock()
    mock_ticker.info = {}

    with patch("app.providers.yahoo.client.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(InvalidSymbolError):
            provider.fetch_metadata("INVALID.NS")


def test_fetch_metadata_provider_error():
    provider = YahooFinanceProvider()

    with patch("app.providers.yahoo.client.yf.Ticker", side_effect=RuntimeError("network")):
        with pytest.raises(ProviderError):
            provider.fetch_metadata("RELIANCE.NS")


def test_fetch_history_success():
    provider = YahooFinanceProvider()
    frame = pd.DataFrame(
        {
            "Open": [2500.0],
            "High": [2520.0],
            "Low": [2490.0],
            "Close": [2510.0],
            "Volume": [1000000.0],
            "Adj Close": [2510.0],
        },
        index=pd.to_datetime(["2024-01-02"]),
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = frame

    with patch("app.providers.yahoo.client.yf.Ticker", return_value=mock_ticker):
        bars = provider.fetch_history("RELIANCE.NS", IngestPeriod.ONE_YEAR)

    assert len(bars) == 1
    assert bars[0].close == Decimal("2510.0")


def test_fetch_history_empty():
    provider = YahooFinanceProvider()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    with patch("app.providers.yahoo.client.yf.Ticker", return_value=mock_ticker):
        bars = provider.fetch_history("RELIANCE.NS", IngestPeriod.ONE_YEAR)

    assert bars == []
