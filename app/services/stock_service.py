from app.core.exceptions import NotFoundError
from app.db.repositories.stock_repository import StockRepository
from app.models.stock import Stock


class StockService:
    def __init__(self, stock_repo: StockRepository) -> None:
        self.stock_repo = stock_repo

    def list_stocks(self, data_status: str | None = None) -> list[Stock]:
        return self.stock_repo.list_stocks(data_status=data_status)

    def get_stock(self, symbol: str) -> Stock:
        stock = self.stock_repo.get_by_symbol(symbol.strip().upper())
        if stock is None:
            raise NotFoundError(f"Stock not found: {symbol}")
        return stock
