from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.platform_traceability import ExperimentRun
    from app.models.ranking_run import RankingRun
    from app.models.ranking_validation_report import RankingValidationReport


class RegimePolicyConfig(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "regime_policy_configs"

    policy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_regimes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    size_multipliers: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    min_decile: Mapped[int | None] = mapped_column(Integer)
    max_decile: Mapped[int | None] = mapped_column(Integer)
    default_action: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    decisions: Mapped[list[RegimePolicyDecision]] = relationship(back_populates="policy_config")
    backtest_runs: Mapped[list[RegimeBacktestRun]] = relationship(
        back_populates="policy_config",
        foreign_keys="RegimeBacktestRun.policy_config_id",
    )

    __table_args__ = (
        UniqueConstraint(
            "policy_name",
            "policy_version",
            name="uq_regime_policy_configs_name_version",
        ),
        Index("ix_regime_policy_configs_strategy_status", "strategy_name", "strategy_version", "status"),
    )


class RegimePolicyDecision(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "regime_policy_decisions"

    policy_config_id: Mapped[UUID] = mapped_column(
        ForeignKey("regime_policy_configs.id", ondelete="CASCADE"), nullable=False
    )
    ranking_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="SET NULL"), nullable=True
    )
    validation_report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ranking_validation_reports.id", ondelete="SET NULL"), nullable=True
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    regime_label: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    size_multiplier: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    decile_filter: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    experiment_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("experiment_runs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    policy_config: Mapped[RegimePolicyConfig] = relationship(back_populates="decisions")
    ranking_run: Mapped[RankingRun | None] = relationship("RankingRun")
    validation_report: Mapped[RankingValidationReport | None] = relationship("RankingValidationReport")
    experiment_run: Mapped[ExperimentRun | None] = relationship("ExperimentRun")

    __table_args__ = (
        Index("ix_regime_policy_decisions_run", "ranking_run_id"),
        Index("ix_regime_policy_decisions_date_regime", "as_of_date", "regime_label"),
        Index("ix_regime_policy_decisions_experiment", "experiment_run_id"),
    )


class RegimeBacktestRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "regime_backtest_runs"

    experiment_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("experiment_runs.id", ondelete="CASCADE"), nullable=False
    )
    policy_config_id: Mapped[UUID] = mapped_column(
        ForeignKey("regime_policy_configs.id", ondelete="CASCADE"), nullable=False
    )
    baseline_policy_config_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("regime_policy_configs.id", ondelete="SET NULL"), nullable=True
    )
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    window_spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    holdout_start_date: Mapped[date | None] = mapped_column(Date)
    train_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    holdout_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    comparison_vs_baseline: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    research_findings: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    days_included: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    days_excluded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    experiment_run: Mapped[ExperimentRun] = relationship("ExperimentRun")
    policy_config: Mapped[RegimePolicyConfig] = relationship(
        back_populates="backtest_runs",
        foreign_keys=[policy_config_id],
    )
    baseline_policy_config: Mapped[RegimePolicyConfig | None] = relationship(
        foreign_keys=[baseline_policy_config_id],
    )

    __table_args__ = (
        Index("ix_regime_backtest_runs_experiment", "experiment_run_id"),
        Index("ix_regime_backtest_runs_policy", "policy_config_id"),
    )
