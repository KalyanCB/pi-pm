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
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ranking_run import RankingRun
    from app.models.stock import Stock


class RecommendationConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recommendation_configs"

    config_version: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    config_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)


class RecommendationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recommendation_runs"

    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    config_version: Mapped[str] = mapped_column(String(32), nullable=False)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    regime_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    ranking_run: Mapped[RankingRun] = relationship("RankingRun")
    results: Mapped[list[RecommendationResult]] = relationship(
        "RecommendationResult", back_populates="recommendation_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_recommendation_runs_as_of_strategy", "as_of_date", "strategy_name"),
    )


class RecommendationResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recommendation_results"

    recommendation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int | None] = mapped_column(Integer)
    composite_score: Mapped[float | None] = mapped_column(Numeric(18, 8))
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_state: Mapped[str | None] = mapped_column(String(32))
    conviction_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    conviction_band: Mapped[str] = mapped_column(String(16), nullable=False)
    conviction_components: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    portfolio_position_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("portfolio_positions.id", ondelete="SET NULL"), nullable=True
    )
    prior_recommendation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recommendation_results.id", ondelete="SET NULL"), nullable=True
    )
    args_research_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_runs.id", ondelete="SET NULL"), nullable=True
    )

    recommendation_run: Mapped[RecommendationRun] = relationship(
        "RecommendationRun", back_populates="results"
    )
    stock: Mapped[Stock] = relationship("Stock")
    approvals: Mapped[list[RecommendationApproval]] = relationship(
        "RecommendationApproval", back_populates="recommendation_result", cascade="all, delete-orphan"
    )
    outcome: Mapped[RecommendationOutcome | None] = relationship(
        "RecommendationOutcome", back_populates="recommendation_result", uselist=False
    )

    __table_args__ = (
        UniqueConstraint(
            "recommendation_run_id", "stock_id", name="uq_rec_results_run_stock"
        ),
        Index("ix_rec_results_run_action", "recommendation_run_id", "action"),
        Index("ix_rec_results_stock_lifecycle", "stock_id", "lifecycle_state"),
    )


class RecommendationApproval(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "recommendation_approvals"

    recommendation_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_results.id", ondelete="CASCADE"), nullable=False
    )
    approval_type: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)

    recommendation_result: Mapped[RecommendationResult] = relationship(
        "RecommendationResult", back_populates="approvals"
    )


class RecommendationOutcome(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recommendation_outcomes"

    recommendation_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_results.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    outcome_status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    exit_date: Mapped[date | None] = mapped_column(Date)
    entry_price: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Numeric(18, 8))
    holding_days: Mapped[int | None] = mapped_column(Integer)
    pnl_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_gain_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_drawdown_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    benchmark_return_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    alpha_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    exit_reason_codes: Mapped[list[str] | None] = mapped_column(JSONB)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    recommendation_result: Mapped[RecommendationResult] = relationship(
        "RecommendationResult", back_populates="outcome"
    )
