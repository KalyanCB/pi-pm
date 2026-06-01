from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class DailyBatchRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "daily_batch_runs"

    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    benchmark_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    target_trading_day: Mapped[date | None] = mapped_column(Date, nullable=True)
    from_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    force_from_date: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    force_recompute: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    force_regenerate_rankings: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    percent_complete: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    current_load: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    parameter_set: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    plan_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    phase_results: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    __table_args__ = (Index("ix_daily_batch_runs_status_started", "status", "started_at"),)


class DailyBatchRunArtifact(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "daily_batch_run_artifacts"

    daily_batch_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("daily_batch_runs.id", ondelete="CASCADE"), nullable=False
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_id: Mapped[UUID] = mapped_column(nullable=False)
    strategy_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "daily_batch_run_id",
            "artifact_type",
            "artifact_id",
            name="uq_daily_batch_run_artifacts_key",
        ),
        Index("ix_daily_batch_run_artifacts_run_type", "daily_batch_run_id", "artifact_type"),
    )
