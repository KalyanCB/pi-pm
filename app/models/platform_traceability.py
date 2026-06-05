from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.market_data_ingestion_run import MarketDataIngestionRun
    from app.models.ranking_run import RankingRun
    from app.models.ranking_validation_report import RankingValidationReport
    from app.models.stock import Stock


class IngestionBatchRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ingestion_batch_runs"

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    period: Mapped[str] = mapped_column(String(8), nullable=False)
    ingestion_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol_count_requested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    symbol_count_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    symbol_count_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    symbol_runs: Mapped[list[MarketDataIngestionRun]] = relationship(back_populates="batch")


class RankingFactorContribution(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ranking_factor_contributions"

    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    factor_name: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_factor_value: Mapped[float | None] = mapped_column(Numeric(18, 8))
    normalized_factor_value: Mapped[float | None] = mapped_column(Numeric(18, 8))
    weighted_factor_value: Mapped[float | None] = mapped_column(Numeric(18, 8))

    ranking_run: Mapped[RankingRun] = relationship("RankingRun")
    stock: Mapped[Stock] = relationship("Stock")

    __table_args__ = (
        UniqueConstraint(
            "ranking_run_id",
            "stock_id",
            "factor_name",
            name="uq_ranking_factor_contributions_run_stock_factor",
        ),
        Index("ix_ranking_factor_contributions_run", "ranking_run_id"),
    )


class ValidationHorizonMetric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "validation_horizon_metrics"

    validation_report_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_validation_reports.id", ondelete="CASCADE"), nullable=False
    )
    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False
    )
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    regime_label: Mapped[str | None] = mapped_column(String(32))
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    ic_pearson: Mapped[float | None] = mapped_column(Numeric(18, 8))
    rank_ic_spearman: Mapped[float | None] = mapped_column(Numeric(18, 8))
    hit_rate: Mapped[float | None] = mapped_column(Numeric(18, 8))
    directional_hit_rate: Mapped[float | None] = mapped_column(Numeric(18, 8))
    spread: Mapped[float | None] = mapped_column(Numeric(18, 8))
    top_decile_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    bottom_decile_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    validation_report: Mapped[RankingValidationReport] = relationship("RankingValidationReport")


class ValidationDecileMetric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "validation_decile_metrics"

    validation_report_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_validation_reports.id", ondelete="CASCADE"), nullable=False
    )
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    decile: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    median_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    win_rate: Mapped[float | None] = mapped_column(Numeric(18, 8))

    validation_report: Mapped[RankingValidationReport] = relationship("RankingValidationReport")


class RunLineageRecord(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "run_lineage_records"

    child_entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    child_entity_id: Mapped[UUID] = mapped_column(nullable=False)
    parent_entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_entity_id: Mapped[UUID] = mapped_column(nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_run_lineage_records_child", "child_entity_type", "child_entity_id"),
    )


class ExperimentRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "experiment_runs"

    experiment_name: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    parameter_set: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RegimeHistory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "regime_history"

    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    benchmark_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    trend_regime: Mapped[str] = mapped_column(String(16), nullable=False)
    vol_regime: Mapped[str] = mapped_column(String(16), nullable=False)
    regime_label: Mapped[str] = mapped_column(String(32), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyRegimePerformance(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "strategy_regime_performance"

    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    regime_label: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_ic: Mapped[float | None] = mapped_column(Numeric(18, 8))
    avg_spread: Mapped[float | None] = mapped_column(Numeric(18, 8))
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
