from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ranking_run import RankingRun


class FullUniverseValidationCampaign(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "full_universe_validation_campaigns"

    universe_code: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    ranking_runs_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ranking_runs_reused: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_days_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_days_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    validation_runs: Mapped[list[FullUniverseValidationRun]] = relationship(
        back_populates="campaign"
    )
    metrics: Mapped[list[FullUniverseValidationMetric]] = relationship(back_populates="campaign")
    deciles: Mapped[list[FullUniverseValidationDecile]] = relationship(back_populates="campaign")

    __table_args__ = (
        Index("ix_full_universe_validation_campaigns_status", "status"),
        Index("ix_full_universe_validation_campaigns_dates", "start_date", "end_date"),
    )


class FullUniverseValidationRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "full_universe_validation_runs"

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("full_universe_validation_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False
    )
    validation_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    campaign: Mapped[FullUniverseValidationCampaign] = relationship(
        back_populates="validation_runs"
    )
    ranking_run: Mapped[RankingRun] = relationship("RankingRun")

    __table_args__ = (Index("ix_full_universe_validation_runs_campaign", "campaign_id"),)


class FullUniverseValidationMetric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "full_universe_validation_metrics"

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("full_universe_validation_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    ic_pearson: Mapped[float | None] = mapped_column(Numeric(18, 8))
    rank_ic_spearman: Mapped[float | None] = mapped_column(Numeric(18, 8))
    hit_rate: Mapped[float | None] = mapped_column(Numeric(18, 8))
    directional_hit_rate: Mapped[float | None] = mapped_column(Numeric(18, 8))
    top_decile_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    bottom_decile_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    spread: Mapped[float | None] = mapped_column(Numeric(18, 8))
    top_20_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    top_50_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ranked_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_monotonic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    campaign: Mapped[FullUniverseValidationCampaign] = relationship(back_populates="metrics")


class FullUniverseValidationDecile(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "full_universe_validation_deciles"

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("full_universe_validation_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    decile: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    median_return: Mapped[float | None] = mapped_column(Numeric(18, 8))
    win_rate: Mapped[float | None] = mapped_column(Numeric(18, 8))

    campaign: Mapped[FullUniverseValidationCampaign] = relationship(back_populates="deciles")
