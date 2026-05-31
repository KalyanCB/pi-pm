from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Date, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import RankingRunStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
    from app.models.ranking_result import RankingResult
    from app.models.ranking_validation_report import RankingValidationReport


class RankingRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ranking_runs"

    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    inputs_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    universe_code: Mapped[str] = mapped_column(String(32), nullable=False)
    benchmark_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    filter_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalization_method: Mapped[str] = mapped_column(String(16), nullable=False, default="percentile")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=RankingRunStatus.PENDING.value
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    regime_label: Mapped[str | None] = mapped_column(String(32))
    weight_config_hash: Mapped[str | None] = mapped_column(String(64))
    ranked_stock_count: Mapped[int | None] = mapped_column(Integer)
    excluded_stock_count: Mapped[int | None] = mapped_column(Integer)
    execution_duration_ms: Mapped[int | None] = mapped_column(Integer)

    results: Mapped[list[RankingResult]] = relationship(back_populates="ranking_run")
    performance_snapshots: Mapped[list[RankingPerformanceSnapshot]] = relationship(
        back_populates="ranking_run"
    )
    validation_report: Mapped[RankingValidationReport | None] = relationship(
        back_populates="ranking_run", uselist=False
    )

    __table_args__ = (
        Index("ix_ranking_runs_as_of_date", "as_of_date"),
        Index("ix_ranking_runs_universe_as_of", "universe_code", "as_of_date"),
        Index("ix_ranking_runs_strategy_as_of", "strategy_name", "strategy_version", "as_of_date"),
    )
