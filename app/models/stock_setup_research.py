from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ranking_result import RankingResult
    from app.models.ranking_run import RankingRun
    from app.models.stock import Stock


class StockSetupResearch(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "stock_setup_research"

    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False
    )
    ranking_result_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ranking_results.id", ondelete="SET NULL"), nullable=True
    )
    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    similar_setups: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    nearest_n: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    min_similarity: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parameter_set: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    research_hash: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    metrics: Mapped[list[StockSetupResearchMetric]] = relationship(
        back_populates="research", cascade="all, delete-orphan"
    )
    ranking_run: Mapped[RankingRun] = relationship("RankingRun")
    ranking_result: Mapped[RankingResult | None] = relationship("RankingResult")
    stock: Mapped[Stock] = relationship("Stock")

    __table_args__ = (
        UniqueConstraint("ranking_run_id", "stock_id", name="uq_stock_setup_research_run_stock"),
        Index("ix_stock_setup_research_run", "ranking_run_id"),
        Index("ix_stock_setup_research_symbol", "symbol"),
    )


class StockSetupResearchMetric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "stock_setup_research_metrics"

    stock_setup_research_id: Mapped[UUID] = mapped_column(
        ForeignKey("stock_setup_research.id", ondelete="CASCADE"), nullable=False
    )
    regime_label: Mapped[str] = mapped_column(String(32), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate_5d: Mapped[float | None] = mapped_column(Numeric(8, 6))
    win_rate_20d: Mapped[float | None] = mapped_column(Numeric(8, 6))
    avg_return_5d: Mapped[float | None] = mapped_column(Numeric(18, 8))
    avg_return_20d: Mapped[float | None] = mapped_column(Numeric(18, 8))
    median_return_20d: Mapped[float | None] = mapped_column(Numeric(18, 8))
    avg_max_drawdown: Mapped[float | None] = mapped_column(Numeric(18, 8))
    avg_max_runup: Mapped[float | None] = mapped_column(Numeric(18, 8))
    avg_similarity_score: Mapped[float | None] = mapped_column(Numeric(8, 6))

    research: Mapped[StockSetupResearch] = relationship(back_populates="metrics")

    __table_args__ = (
        UniqueConstraint(
            "stock_setup_research_id",
            "regime_label",
            name="uq_stock_setup_research_metrics_regime",
        ),
        Index("ix_stock_setup_research_metrics_research", "stock_setup_research_id"),
    )
