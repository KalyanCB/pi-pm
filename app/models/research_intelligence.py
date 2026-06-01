from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ResearchIntelligenceRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "research_intelligence_runs"

    status: Mapped[str] = mapped_column(String(16), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of_date_start: Mapped[date] = mapped_column(Date, nullable=False)
    as_of_date_end: Mapped[date] = mapped_column(Date, nullable=False)
    holdout_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    parameter_set: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResearchIntelligenceReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "research_intelligence_reports"

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_intelligence_runs.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("run_id", "report_type", name="uq_research_intelligence_report_run_type"),
    )
