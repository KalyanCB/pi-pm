from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ranking_run import RankingRun
    from app.models.stock import Stock


class RankingResult(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ranking_results"

    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    score_components: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ranking_run: Mapped[RankingRun] = relationship(back_populates="results")
    stock: Mapped[Stock] = relationship("Stock")

    __table_args__ = (
        UniqueConstraint("ranking_run_id", "stock_id", name="uq_ranking_result_run_stock"),
        UniqueConstraint("ranking_run_id", "rank", name="uq_ranking_result_run_rank"),
        Index("ix_ranking_results_run_rank", "ranking_run_id", "rank"),
    )
