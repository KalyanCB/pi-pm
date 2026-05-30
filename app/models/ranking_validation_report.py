from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ranking_run import RankingRun


class RankingValidationReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ranking_validation_reports"

    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    regime_label: Mapped[str | None] = mapped_column(String(32))
    trend_regime: Mapped[str | None] = mapped_column(String(16))
    vol_regime: Mapped[str | None] = mapped_column(String(16))
    horizon_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sample_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    ranking_run: Mapped[RankingRun] = relationship(back_populates="validation_report")

    __table_args__ = (
        Index("ix_ranking_validation_reports_status", "status"),
        Index("ix_ranking_validation_reports_regime", "regime_label"),
    )
