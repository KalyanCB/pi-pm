"""ADR-039 Fundamental Intelligence Layer — ORM tables.

Five tables:
  company_news_events    extracted per-stock catalysts
  fil_watch_list         active company catalysts with an expiry
  fil_conviction_boosts  audit of boosts applied at recommendation time (Phase 2)
  sector_classifications stock → sector mapping (Phase 3)
  sector_news_events     extracted sector-level catalysts (Phase 3)

Not yet referenced by the recommendation engine or daily batch — wiring is a
separate change.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class CompanyNewsEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "company_news_events"

    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    magnitude: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    catalyst_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    raw_excerpt: Mapped[str | None] = mapped_column(Text)
    flags: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # UNCONFIRMED events (0.70 <= conf < 0.85) are stored for analysis but never
    # enter the watch list.
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    external_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_company_news_events_stock_date", "stock_id", "event_date"),
        Index("ix_company_news_events_date_category", "event_date", "category"),
        UniqueConstraint("source", "external_id", name="uq_company_news_events_source_extid"),
    )


class FilWatchListEntry(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "fil_watch_list"

    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    news_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("company_news_events.id", ondelete="CASCADE"), nullable=False
    )
    added_date: Mapped[date] = mapped_column(Date, nullable=False)
    expires_date: Mapped[date] = mapped_column(Date, nullable=False)
    catalyst_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivation_reason: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_fil_watch_list_active", "stock_id", "is_active", "expires_date"),
        Index("ix_fil_watch_list_added", "added_date"),
    )


class FilConvictionBoost(Base, UUIDPrimaryKeyMixin):
    """Audit row written when (at integration time) a boost is evaluated for a rec."""

    __tablename__ = "fil_conviction_boosts"

    recommendation_result_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recommendation_results.id", ondelete="CASCADE")
    )
    fil_watch_list_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("fil_watch_list.id", ondelete="SET NULL")
    )
    original_conviction_band: Mapped[str | None] = mapped_column(String(20))
    boosted_conviction_band: Mapped[str | None] = mapped_column(String(20))
    boost_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SectorClassification(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "sector_classifications"

    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    sector: Mapped[str] = mapped_column(String(60), nullable=False)
    sub_sector: Mapped[str | None] = mapped_column(String(60))
    index_membership: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("stock_id", "sector", name="uq_sector_classifications_stock_sector"),
        Index("ix_sector_classifications_sector", "sector"),
    )


class SectorNewsEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "sector_news_events"

    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    sector: Mapped[str] = mapped_column(String(60), nullable=False)
    sub_sector: Mapped[str | None] = mapped_column(String(60))
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    magnitude: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    catalyst_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    raw_excerpt: Mapped[str | None] = mapped_column(Text)
    affected_stocks_count: Mapped[int | None] = mapped_column(Integer)
    external_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_sector_news_events_sector_date", "sector", "event_date"),
        Index("ix_sector_news_events_date_sentiment", "event_date", "sentiment"),
        UniqueConstraint("source", "external_id", name="uq_sector_news_events_source_extid"),
    )
