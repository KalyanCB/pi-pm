from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.core.constants import DataStatus, IngestBatchStatus, IngestPeriod
from app.core.exceptions import InvalidSymbolError, NotFoundError
from app.providers.yahoo.models import YahooOHLCVBar, YahooStockMetadata


@pytest.fixture
def metadata_reliance() -> YahooStockMetadata:
    return YahooStockMetadata(
        symbol="RELIANCE.NS",
        name="Reliance Industries Ltd",
        exchange="NSE",
        sector="Energy",
        industry="Oil & Gas",
    )


@pytest.fixture
def metadata_tcs() -> YahooStockMetadata:
    return YahooStockMetadata(
        symbol="TCS.NS",
        name="Tata Consultancy Services",
        exchange="NSE",
        sector="Technology",
        industry="IT Services",
    )


def _bars(symbol_date: date | None = None) -> list[YahooOHLCVBar]:
    bar_date = symbol_date or (datetime.now(UTC).date() - timedelta(days=1))
    return [
        YahooOHLCVBar(
            date=bar_date,
            open=Decimal("100"),
            high=Decimal("105"),
            low=Decimal("99"),
            close=Decimal("102"),
            volume=1000,
            adj_close=Decimal("102"),
        )
    ]


def test_ingest_persists_stock_and_market_data(
    market_data_service, stock_repo, market_data_repo, metadata_reliance
):
    with patch.object(
        market_data_service.provider,
        "fetch_metadata",
        return_value=metadata_reliance,
    ), patch.object(
        market_data_service.provider,
        "fetch_history",
        return_value=_bars(),
    ):
        result = market_data_service.ingest(["RELIANCE.NS"], IngestPeriod.ONE_YEAR)

    assert result.status == IngestBatchStatus.SUCCESS
    assert result.symbols_processed == 1
    assert result.rows_inserted == 1

    stock = stock_repo.get_by_symbol("RELIANCE.NS")
    assert stock is not None
    assert stock.data_status == DataStatus.ACTIVE.value

    latest = market_data_repo.get_latest_market_data(stock.id)
    assert latest is not None
    assert float(latest.close) == 102.0


def test_ingest_is_idempotent(market_data_service, metadata_reliance):
    with patch.object(
        market_data_service.provider,
        "fetch_metadata",
        return_value=metadata_reliance,
    ), patch.object(
        market_data_service.provider,
        "fetch_history",
        return_value=_bars(),
    ):
        first = market_data_service.ingest(["RELIANCE.NS"], IngestPeriod.ONE_YEAR)
        second = market_data_service.ingest(["RELIANCE.NS"], IngestPeriod.ONE_YEAR)

    assert first.rows_inserted == 1
    assert second.rows_inserted == 0
    assert second.rows_updated == 1


def test_ingest_skips_future_dates(market_data_service, metadata_reliance):
    future = datetime.now(UTC).date() + timedelta(days=5)
    with patch.object(
        market_data_service.provider,
        "fetch_metadata",
        return_value=metadata_reliance,
    ), patch.object(
        market_data_service.provider,
        "fetch_history",
        return_value=_bars(future),
    ):
        result = market_data_service.ingest(["RELIANCE.NS"], IngestPeriod.ONE_YEAR)

    assert result.symbols_failed == 1
    assert result.runs[0].status == "FAILED"


def test_multi_symbol_partial_failure(
    market_data_service, metadata_reliance, metadata_tcs
):
    def metadata_side_effect(symbol: str):
        if symbol == "RELIANCE.NS":
            return metadata_reliance
        raise InvalidSymbolError(f"No metadata found for symbol: {symbol}")

    with patch.object(
        market_data_service.provider,
        "fetch_metadata",
        side_effect=metadata_side_effect,
    ), patch.object(
        market_data_service.provider,
        "fetch_history",
        return_value=_bars(),
    ):
        result = market_data_service.ingest(
            ["RELIANCE.NS", "INVALID.NS"],
            IngestPeriod.ONE_YEAR,
        )

    assert result.symbols_processed == 1
    assert result.symbols_failed == 1
    assert result.status == IngestBatchStatus.PARTIAL_SUCCESS


def test_unhealthy_batch_failure_rate(market_data_service):
    with patch.object(
        market_data_service.provider,
        "fetch_metadata",
        side_effect=InvalidSymbolError("bad"),
    ):
        result = market_data_service.ingest(
            ["BAD1.NS", "BAD2.NS", "BAD3.NS"],
            IngestPeriod.ONE_YEAR,
        )

    assert result.symbols_failed == 3
    assert result.is_unhealthy_batch is True


def test_get_market_data_not_found(market_data_service):
    with pytest.raises(NotFoundError):
        market_data_service.get_market_data("UNKNOWN.NS")


def test_get_latest_market_data(market_data_service, stock_repo, metadata_reliance):
    with patch.object(
        market_data_service.provider,
        "fetch_metadata",
        return_value=metadata_reliance,
    ), patch.object(
        market_data_service.provider,
        "fetch_history",
        return_value=_bars(),
    ):
        market_data_service.ingest(["RELIANCE.NS"], IngestPeriod.ONE_YEAR)

    stock = stock_repo.get_by_symbol("RELIANCE.NS")
    latest = market_data_service.market_data_repo.get_latest_market_data(stock.id)
    assert latest is not None
