from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from collections import defaultdict

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.constants import MARKET_DATA_SOURCE_YAHOO
from app.models.market_data import MarketData
from app.providers.yahoo.models import YahooOHLCVBar


@dataclass(frozen=True)
class UpsertCounts:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


class MarketDataRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_stock_and_date_range(
        self,
        stock_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[MarketData]:
        stmt = select(MarketData).where(MarketData.stock_id == stock_id)
        if start_date is not None:
            stmt = stmt.where(MarketData.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(MarketData.date <= end_date)
        if source is not None:
            stmt = stmt.where(MarketData.source == source)
        stmt = stmt.order_by(MarketData.date.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_latest_market_data(
        self,
        stock_id: UUID,
        source: str | None = MARKET_DATA_SOURCE_YAHOO,
    ) -> MarketData | None:
        stmt = select(MarketData).where(MarketData.stock_id == stock_id)
        if source is not None:
            stmt = stmt.where(MarketData.source == source)
        stmt = stmt.order_by(MarketData.date.desc()).limit(1)
        return self.db.scalar(stmt)

    def list_distinct_trading_dates(
        self,
        stock_ids: list[UUID],
        start_date: date,
        end_date: date,
        source: str | None = MARKET_DATA_SOURCE_YAHOO,
    ) -> list[date]:
        if not stock_ids:
            return []
        stmt = (
            select(MarketData.date)
            .where(
                MarketData.stock_id.in_(stock_ids),
                MarketData.date >= start_date,
                MarketData.date <= end_date,
            )
            .distinct()
            .order_by(MarketData.date)
        )
        if source is not None:
            stmt = stmt.where(MarketData.source == source)
        return list(self.db.scalars(stmt).all())

    def get_all_by_stock_ids_up_to_date(
        self,
        stock_ids: list[UUID],
        end_date: date,
        source: str | None = MARKET_DATA_SOURCE_YAHOO,
        start_date: date | None = None,
    ) -> dict[UUID, list]:
        """Bulk fetch bars for all stock_ids in a single query. Returns {stock_id: [rows]}."""
        if not stock_ids:
            return {}
        stmt = (
            select(MarketData)
            .where(
                MarketData.stock_id.in_(stock_ids),
                MarketData.date <= end_date,
            )
            .order_by(MarketData.stock_id, MarketData.date)
        )
        if source is not None:
            stmt = stmt.where(MarketData.source == source)
        if start_date is not None:
            stmt = stmt.where(MarketData.date >= start_date)
        result: dict[UUID, list] = defaultdict(list)
        for row in self.db.scalars(stmt).all():
            result[row.stock_id].append(row)
        return dict(result)

    def count_bars_on_or_before(
        self,
        stock_id: UUID,
        as_of_date: date,
        source: str | None = MARKET_DATA_SOURCE_YAHOO,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(MarketData)
            .where(
                MarketData.stock_id == stock_id,
                MarketData.date <= as_of_date,
            )
        )
        if source is not None:
            stmt = stmt.where(MarketData.source == source)
        return int(self.db.scalar(stmt) or 0)

    def upsert_bars(
        self,
        stock_id: UUID,
        bars: list[YahooOHLCVBar],
        source: str = MARKET_DATA_SOURCE_YAHOO,
    ) -> UpsertCounts:
        from uuid import uuid4
        today = datetime.now(UTC).date()
        now = datetime.now(UTC)

        if not bars:
            return UpsertCounts()

        # Deduplicate by date — keep last occurrence if Kite returns duplicates
        seen: dict = {}
        for bar in bars:
            if bar.date <= today and bar.close is not None:
                seen[bar.date] = bar

        rows = [
            {
                "id": uuid4(),
                "stock_id": stock_id,
                "date": bar.date,
                "open": _optional_float(bar.open),
                "high": _optional_float(bar.high),
                "low": _optional_float(bar.low),
                "close": float(bar.close),
                "volume": bar.volume,
                "adj_close": _optional_float(bar.adj_close),
                "dividend": _optional_float(bar.dividend),
                "split_factor": _optional_float(bar.split_factor),
                "source": source,
                "ingested_at": now,
            }
            for bar in seen.values()
        ]
        skipped = len(bars) - len(rows)

        if not rows:
            return UpsertCounts(skipped=skipped)

        # Count existing rows for this stock/source/dates to detect inserts vs updates
        dates = [r["date"] for r in rows]
        existing_count_stmt = (
            select(func.count())
            .select_from(MarketData)
            .where(
                MarketData.stock_id == stock_id,
                MarketData.source == source,
                MarketData.date.in_(dates),
            )
        )
        existing = int(self.db.scalar(existing_count_stmt) or 0)

        ins_stmt = pg_insert(MarketData).values(rows)
        ins_stmt = ins_stmt.on_conflict_do_update(
            index_elements=["stock_id", "date", "source"],
            set_={
                "open": ins_stmt.excluded.open,
                "high": ins_stmt.excluded.high,
                "low": ins_stmt.excluded.low,
                "close": ins_stmt.excluded.close,
                "volume": ins_stmt.excluded.volume,
                "adj_close": ins_stmt.excluded.adj_close,
                "dividend": ins_stmt.excluded.dividend,
                "split_factor": ins_stmt.excluded.split_factor,
                "ingested_at": ins_stmt.excluded.ingested_at,
            },
        )
        self.db.execute(ins_stmt)
        inserted = len(rows) - existing
        updated = existing
        return UpsertCounts(inserted=inserted, updated=updated, skipped=skipped)


def _optional_float(value) -> float | None:
    return float(value) if value is not None else None
