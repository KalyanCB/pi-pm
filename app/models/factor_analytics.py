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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class FactorPerformanceRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "factor_performance_runs"

    status: Mapped[str] = mapped_column(String(16), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    as_of_date_start: Mapped[date] = mapped_column(Date, nullable=False)
    as_of_date_end: Mapped[date] = mapped_column(Date, nullable=False)
    holdout_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    reports_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parameter_set: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_factor_performance_runs_status_started", "status", "started_at"),)


class FactorDailyMetric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "factor_daily_metrics"

    factor_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    regime_label: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    dataset_split: Mapped[str] = mapped_column(String(16), nullable=False)
    ic_spearman: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "factor_name",
            "strategy_name",
            "strategy_version",
            "universe_code",
            "regime_label",
            "horizon",
            "ranking_run_id",
            name="uq_factor_daily_metrics_run_factor",
        ),
        Index("ix_factor_daily_metrics_time", "factor_name", "as_of_date", "horizon"),
        Index("ix_factor_daily_metrics_run", "ranking_run_id"),
    )


class FactorPerformanceMetric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "factor_performance_metrics"

    factor_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    regime_label: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_split: Mapped[str] = mapped_column(String(16), nullable=False)
    ic_spearman: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ic_pearson: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    hit_rate: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    spread_contribution: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ranked_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    regime_coverage_pct: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    stability_score: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    stability_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    coverage_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bootstrap_ci_lower: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    bootstrap_ci_upper: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    p_value: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    is_statistically_significant: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    bootstrap_sample_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bootstrap_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    holdout_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    as_of_date_start: Mapped[date] = mapped_column(Date, nullable=False)
    as_of_date_end: Mapped[date] = mapped_column(Date, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "factor_name",
            "strategy_name",
            "strategy_version",
            "universe_code",
            "horizon",
            "regime_label",
            "dataset_split",
            "as_of_date_start",
            "as_of_date_end",
            "holdout_start_date",
            name="uq_factor_performance_metrics_key",
        ),
        Index(
            "ix_fpm_query",
            "strategy_name",
            "universe_code",
            "horizon",
            "regime_label",
            "dataset_split",
        ),
        Index("ix_fpm_factor", "factor_name", "horizon", "dataset_split"),
    )
