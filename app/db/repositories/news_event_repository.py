"""Repository for ADR-039 company_news_events."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fil import CompanyNewsEvent


class CompanyNewsEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        *,
        stock_id: UUID,
        event_date: date,
        source: str,
        category: str,
        sentiment: str,
        magnitude: str,
        confidence: float,
        catalyst_duration_days: int,
        summary: str,
        raw_excerpt: str | None = None,
        flags: dict | None = None,
        is_confirmed: bool = True,
        external_id: str | None = None,
    ) -> CompanyNewsEvent:
        event = CompanyNewsEvent(
            stock_id=stock_id,
            event_date=event_date,
            source=source,
            category=category,
            sentiment=sentiment,
            magnitude=magnitude,
            confidence=confidence,
            catalyst_duration_days=catalyst_duration_days,
            summary=summary,
            raw_excerpt=raw_excerpt,
            flags=flags,
            is_confirmed=is_confirmed,
            external_id=external_id,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def exists(self, *, source: str, external_id: str) -> bool:
        """Dedup guard — skip raw items already ingested from the same source."""
        if not external_id:
            return False
        return (
            self.db.scalar(
                select(CompanyNewsEvent.id).where(
                    CompanyNewsEvent.source == source,
                    CompanyNewsEvent.external_id == external_id,
                )
            )
            is not None
        )

    def list_for_stock(
        self, stock_id: UUID, *, since: date | None = None
    ) -> list[CompanyNewsEvent]:
        stmt = select(CompanyNewsEvent).where(CompanyNewsEvent.stock_id == stock_id)
        if since is not None:
            stmt = stmt.where(CompanyNewsEvent.event_date >= since)
        stmt = stmt.order_by(CompanyNewsEvent.event_date.desc())
        return list(self.db.scalars(stmt))
