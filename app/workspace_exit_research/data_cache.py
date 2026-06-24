from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market_data import MarketData
from app.models.platform_traceability import RegimeHistory
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.ranking.math_utils import PriceBar


def market_data_to_bars(rows: list[MarketData]) -> list[PriceBar]:
    sorted_rows = sorted(rows, key=lambda row: row.date)
    return [
        PriceBar(
            date=row.date,
            close=float(row.close),
            volume=int(row.volume) if row.volume is not None else None,
        )
        for row in sorted_rows
    ]


class ResearchBarCache:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._bars: dict[UUID, list[PriceBar]] = {}

    def load_for_stocks(
        self,
        stock_ids: set[UUID],
        *,
        start_date: date,
        end_date: date,
    ) -> None:
        if not stock_ids:
            return
        rows = self.db.scalars(
            select(MarketData).where(
                MarketData.stock_id.in_(stock_ids),
                MarketData.date >= start_date - timedelta(days=400),
                MarketData.date <= end_date + timedelta(days=120),
            )
        ).all()
        grouped: dict[UUID, list[MarketData]] = {}
        for row in rows:
            grouped.setdefault(row.stock_id, []).append(row)
        for stock_id, stock_rows in grouped.items():
            self._bars[stock_id] = market_data_to_bars(stock_rows)

    def get(self, stock_id: UUID) -> list[PriceBar]:
        return self._bars.get(stock_id, [])


class RankPathCache:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._by_stock: dict[UUID, list[tuple[date, int]]] = {}

    def load(
        self,
        *,
        strategy_name: str,
        strategy_version: str,
        universe_code: str,
        stock_ids: set[UUID],
        start_date: date,
        end_date: date,
    ) -> None:
        if not stock_ids:
            return
        rows = self.db.execute(
            select(
                RankingResult.stock_id,
                RankingResult.rank,
                RankingRun.as_of_date,
            )
            .join(RankingRun, RankingRun.id == RankingResult.ranking_run_id)
            .where(RankingRun.strategy_name == strategy_name)
            .where(RankingRun.strategy_version == strategy_version)
            .where(RankingRun.universe_code == universe_code)
            .where(RankingResult.stock_id.in_(stock_ids))
            .where(RankingRun.as_of_date >= start_date)
            .where(RankingRun.as_of_date <= end_date + timedelta(days=120))
            .order_by(RankingResult.stock_id, RankingRun.as_of_date)
        ).all()
        for row in rows:
            self._by_stock.setdefault(row.stock_id, []).append((row.as_of_date, row.rank))
        for stock_id in self._by_stock:
            self._by_stock[stock_id].sort(key=lambda item: item[0])

    def ranks_after(self, stock_id: UUID, entry_date: date) -> list[tuple[date, int]]:
        path = self._by_stock.get(stock_id, [])
        return [(d, r) for d, r in path if d > entry_date]


class RegimePathCache:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._by_date: dict[date, str] = {}

    def load(self, *, start_date: date, end_date: date) -> None:
        rows = self.db.scalars(
            select(RegimeHistory)
            .where(RegimeHistory.as_of_date >= start_date)
            .where(RegimeHistory.as_of_date <= end_date + timedelta(days=120))
            .order_by(RegimeHistory.as_of_date)
        ).all()
        self._by_date = {row.as_of_date: row.regime_label for row in rows}

    def regime_on(self, as_of: date) -> str | None:
        return self._by_date.get(as_of)

    def regime_changes_after(self, entry_date: date, entry_regime: str) -> list[date]:
        dates = []
        for day, regime in sorted(self._by_date.items()):
            if day > entry_date and regime != entry_regime:
                dates.append(day)
        return dates
