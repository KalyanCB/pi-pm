from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ResearchReportStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.stock import Stock


class ResearchReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "research_reports"

    stock_id: Mapped[UUID] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    model_id: Mapped[str] = mapped_column(String(64), nullable=False, default="stub")
    prompt_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ResearchReportStatus.PUBLISHED.value
    )
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_reports.id", ondelete="SET NULL"), nullable=True
    )

    stock: Mapped[Stock] = relationship("Stock")
    superseded_by: Mapped[ResearchReport | None] = relationship(remote_side="ResearchReport.id")

    __table_args__ = (Index("ix_research_reports_stock_created", "stock_id", "created_at"),)
