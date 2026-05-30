from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import DataStatus
from app.models.stock import Stock
from app.providers.yahoo.models import YahooStockMetadata


class StockRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_stocks(self, data_status: str | None = None) -> list[Stock]:
        stmt = select(Stock).order_by(Stock.symbol)
        if data_status is not None:
            stmt = stmt.where(Stock.data_status == data_status)
        return list(self.db.scalars(stmt).all())

    def get_by_symbol(self, symbol: str) -> Stock | None:
        return self.db.scalar(select(Stock).where(Stock.symbol == symbol))

    def upsert_from_metadata(self, metadata: YahooStockMetadata) -> Stock:
        stock = self.get_by_symbol(metadata.symbol)
        if stock is None:
            stock = Stock(
                symbol=metadata.symbol,
                name=metadata.name,
                exchange=metadata.exchange,
                sector=metadata.sector,
                industry=metadata.industry,
                data_status=DataStatus.ACTIVE.value,
            )
            self.db.add(stock)
        else:
            stock.name = metadata.name
            stock.exchange = metadata.exchange
            stock.sector = metadata.sector
            stock.industry = metadata.industry
            if stock.data_status != DataStatus.INACTIVE.value:
                stock.data_status = DataStatus.ACTIVE.value
        self.db.flush()
        return stock

    def set_data_status(self, symbol: str, status: DataStatus) -> Stock | None:
        stock = self.get_by_symbol(symbol)
        if stock is None:
            return None
        stock.data_status = status.value
        self.db.flush()
        return stock

    def get_by_id(self, stock_id: UUID) -> Stock | None:
        return self.db.get(Stock, stock_id)
