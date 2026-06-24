"""Repository for ADR-039 fil_watch_list."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fil import FilWatchListEntry


class FilWatchListRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        *,
        stock_id: UUID,
        news_event_id: UUID,
        added_date: date,
        expires_date: date,
        catalyst_type: str,
        sentiment: str,
        confidence: float,
    ) -> FilWatchListEntry:
        entry = FilWatchListEntry(
            stock_id=stock_id,
            news_event_id=news_event_id,
            added_date=added_date,
            expires_date=expires_date,
            catalyst_type=catalyst_type,
            sentiment=sentiment,
            confidence=confidence,
            is_active=True,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def list_active(self, *, as_of: date) -> list[FilWatchListEntry]:
        """Active, non-expired entries as of a given date."""
        stmt = select(FilWatchListEntry).where(
            FilWatchListEntry.is_active.is_(True),
            FilWatchListEntry.expires_date >= as_of,
        )
        return list(self.db.scalars(stmt))

    def has_active_entry(self, *, stock_id: UUID, news_event_id: UUID) -> bool:
        return (
            self.db.scalar(
                select(FilWatchListEntry.id).where(
                    FilWatchListEntry.stock_id == stock_id,
                    FilWatchListEntry.news_event_id == news_event_id,
                    FilWatchListEntry.is_active.is_(True),
                )
            )
            is not None
        )

    def deactivate(self, entry: FilWatchListEntry, *, reason: str) -> FilWatchListEntry:
        entry.is_active = False
        entry.deactivated_at = datetime.now(UTC)
        entry.deactivation_reason = reason
        self.db.flush()
        return entry

    def expire_due(self, *, as_of: date, reason: str) -> int:
        """Deactivate every active entry whose expiry has passed. Returns count."""
        stmt = select(FilWatchListEntry).where(
            FilWatchListEntry.is_active.is_(True),
            FilWatchListEntry.expires_date < as_of,
        )
        count = 0
        for entry in self.db.scalars(stmt):
            self.deactivate(entry, reason=reason)
            count += 1
        return count
