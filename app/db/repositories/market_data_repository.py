from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
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

    def upsert_bars(
        self,
        stock_id: UUID,
        bars: list[YahooOHLCVBar],
        source: str = MARKET_DATA_SOURCE_YAHOO,
    ) -> UpsertCounts:
        today = datetime.now(UTC).date()
        inserted = updated = skipped = 0
        now = datetime.now(UTC)

        if not bars:
            return UpsertCounts()

        dates = [bar.date for bar in bars if bar.date <= today and bar.close is not None]
        existing_rows = {}
        if dates:
            rows = self.db.scalars(
                select(MarketData).where(
                    MarketData.stock_id == stock_id,
                    MarketData.source == source,
                    MarketData.date.in_(dates),
                )
            ).all()
            existing_rows = {row.date: row for row in rows}

        for bar in bars:
            if bar.date > today:
                skipped += 1
                continue
            if bar.close is None:
                skipped += 1
                continue

            existing = existing_rows.get(bar.date)
            if existing is None:
                self.db.add(
                    MarketData(
                        stock_id=stock_id,
                        date=bar.date,
                        open=_optional_float(bar.open),
                        high=_optional_float(bar.high),
                        low=_optional_float(bar.low),
                        close=float(bar.close),
                        volume=bar.volume,
                        adj_close=_optional_float(bar.adj_close),
                        dividend=_optional_float(bar.dividend),
                        split_factor=_optional_float(bar.split_factor),
                        source=source,
                        ingested_at=now,
                    )
                )
                inserted += 1
            else:
                existing.open = _optional_float(bar.open)
                existing.high = _optional_float(bar.high)
                existing.low = _optional_float(bar.low)
                existing.close = float(bar.close)
                existing.volume = bar.volume
                existing.adj_close = _optional_float(bar.adj_close)
                existing.dividend = _optional_float(bar.dividend)
                existing.split_factor = _optional_float(bar.split_factor)
                existing.ingested_at = now
                updated += 1

        self.db.flush()
        return UpsertCounts(inserted=inserted, updated=updated, skipped=skipped)


def _optional_float(value) -> float | None:
    return float(value) if value is not None else None
