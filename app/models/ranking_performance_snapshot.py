from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ranking_run import RankingRun
    from app.models.stock import Stock


class RankingPerformanceSnapshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ranking_performance_snapshots"

    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    return_5d: Mapped[float | None] = mapped_column(Numeric(18, 8))
    return_10d: Mapped[float | None] = mapped_column(Numeric(18, 8))
    return_20d: Mapped[float | None] = mapped_column(Numeric(18, 8))
    return_60d: Mapped[float | None] = mapped_column(Numeric(18, 8))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ranking_run: Mapped[RankingRun] = relationship(back_populates="performance_snapshots")
    stock: Mapped[Stock] = relationship("Stock")

    __table_args__ = (
        UniqueConstraint("ranking_run_id", "stock_id", name="uq_ranking_performance_run_stock"),
        Index("ix_ranking_performance_run", "ranking_run_id"),
    )
