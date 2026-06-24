"""Repository for ADR-039 sector_news_events."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fil import SectorNewsEvent


class SectorNewsEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        *,
        event_date: date,
        sector: str,
        source: str,
        category: str,
        sentiment: str,
        magnitude: str,
        confidence: float,
        catalyst_duration_days: int,
        summary: str,
        sub_sector: str | None = None,
        raw_excerpt: str | None = None,
        affected_stocks_count: int | None = None,
        external_id: str | None = None,
    ) -> SectorNewsEvent:
        event = SectorNewsEvent(
            event_date=event_date,
            sector=sector,
            sub_sector=sub_sector,
            source=source,
            category=category,
            sentiment=sentiment,
            magnitude=magnitude,
            confidence=confidence,
            catalyst_duration_days=catalyst_duration_days,
            summary=summary,
            raw_excerpt=raw_excerpt,
            affected_stocks_count=affected_stocks_count,
            external_id=external_id,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def exists(self, *, source: str, external_id: str) -> bool:
        if not external_id:
            return False
        return (
            self.db.scalar(
                select(SectorNewsEvent.id).where(
                    SectorNewsEvent.source == source,
                    SectorNewsEvent.external_id == external_id,
                )
            )
            is not None
        )

    def list_active(self, *, as_of: date) -> list[SectorNewsEvent]:
        """Sector events still within their catalyst window as of a date.

        Active window = event_date <= as_of < event_date + catalyst_duration_days.
        Computed in Python to stay dialect-agnostic for tests.
        """
        from datetime import timedelta

        rows = list(
            self.db.scalars(
                select(SectorNewsEvent).where(SectorNewsEvent.event_date <= as_of)
            )
        )
        return [
            r
            for r in rows
            if as_of < r.event_date + timedelta(days=int(r.catalyst_duration_days))
        ]
