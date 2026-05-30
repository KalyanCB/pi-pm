import pytest

from app.core.constants import DataStatus
from app.core.exceptions import NotFoundError
from app.providers.yahoo.models import YahooStockMetadata


def test_list_and_get_stock(stock_service, stock_repo):
    stock_repo.upsert_from_metadata(
        YahooStockMetadata(
            symbol="TCS.NS",
            name="Tata Consultancy Services",
            exchange="NSE",
            sector="Technology",
            industry="IT Services",
        )
    )
    stock_repo.db.commit()

    stocks = stock_service.list_stocks()
    assert len(stocks) == 1
    assert stocks[0].symbol == "TCS.NS"

    fetched = stock_service.get_stock("tcs.ns")
    assert fetched.name.startswith("Tata")

    with pytest.raises(NotFoundError):
        stock_service.get_stock("UNKNOWN.NS")


def test_upsert_preserves_inactive_status(stock_repo):
    stock = stock_repo.upsert_from_metadata(
        YahooStockMetadata(
            symbol="BEL.NS",
            name="Bharat Electronics",
            exchange="NSE",
            sector="Industrials",
            industry="Defense",
        )
    )
    stock.data_status = DataStatus.INACTIVE.value
    stock_repo.db.commit()

    updated = stock_repo.upsert_from_metadata(
        YahooStockMetadata(
            symbol="BEL.NS",
            name="Bharat Electronics Limited",
            exchange="NSE",
            sector="Industrials",
            industry="Defense",
        )
    )
    assert updated.data_status == DataStatus.INACTIVE.value


def test_set_data_status_error(stock_repo):
    stock_repo.upsert_from_metadata(
        YahooStockMetadata(
            symbol="HAL.NS",
            name="Hindustan Aeronautics",
            exchange="NSE",
            sector=None,
            industry=None,
        )
    )
    stock_repo.db.commit()

    stock_repo.set_data_status("HAL.NS", DataStatus.ERROR)
    stock_repo.db.commit()

    stock = stock_repo.get_by_symbol("HAL.NS")
    assert stock is not None
    assert stock.data_status == DataStatus.ERROR.value
