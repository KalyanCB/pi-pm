from __future__ import annotations

from datetime import date, datetime
from typing import Any
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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ExitResearchRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "exit_research_runs"

    status: Mapped[str] = mapped_column(String(16), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of_date_start: Mapped[date] = mapped_column(Date, nullable=False)
    as_of_date_end: Mapped[date] = mapped_column(Date, nullable=False)
    holdout_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    signals_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_entries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    percent_complete: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    last_progress_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    elapsed_seconds: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    current_phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    persistence_items_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    persistence_items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parameter_set: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_exit_research_runs_status_started", "status", "started_at"),)


class ExitResearchPolicyMetric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "exit_research_policy_metrics"

    research_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("exit_research_runs.id", ondelete="CASCADE"), nullable=False
    )
    policy_family: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_variant: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    regime_label: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_split: Mapped[str] = mapped_column(String(16), nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mean_return: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    median_return: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    std_dev: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    hit_rate: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    avg_holding_days: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ci_lower: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    ci_upper: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    conclusion_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    holdout_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    as_of_date_start: Mapped[date] = mapped_column(Date, nullable=False)
    as_of_date_end: Mapped[date] = mapped_column(Date, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "research_run_id",
            "policy_family",
            "policy_variant",
            "strategy_name",
            "strategy_version",
            "universe_code",
            "regime_label",
            "dataset_split",
            "horizon",
            name="uq_exit_research_policy_metrics_key",
        ),
        Index("ix_exit_policy_metrics_query", "policy_family", "regime_label", "dataset_split"),
    )


class ExitResearchAlphaDecayPoint(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "exit_research_alpha_decay_points"

    research_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("exit_research_runs.id", ondelete="CASCADE"), nullable=False
    )
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    regime_label: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_split: Mapped[str] = mapped_column(String(16), nullable=False)
    trading_day: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mean_return: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    cumulative_mean_return: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    conclusion_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    holdout_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    as_of_date_start: Mapped[date] = mapped_column(Date, nullable=False)
    as_of_date_end: Mapped[date] = mapped_column(Date, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "research_run_id",
            "strategy_name",
            "strategy_version",
            "universe_code",
            "regime_label",
            "dataset_split",
            "trading_day",
            name="uq_exit_alpha_decay_point_key",
        ),
    )
