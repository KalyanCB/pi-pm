from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import CommitteeReviewStatus, ResearchRunStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.stock import Stock


class ResearchRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "research_runs"

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ResearchRunStatus.PENDING.value
    )
    trigger_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    universe_code: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    top_n: Mapped[int] = mapped_column(nullable=False, default=20)
    committee_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ranking_run_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    daily_batch_run_id: Mapped[UUID | None] = mapped_column(nullable=True)
    checkpoint_ref: Mapped[str | None] = mapped_column(String(128))
    phase: Mapped[str | None] = mapped_column(String(32))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(12, 2))

    packets: Mapped[list[InvestmentReviewPacket]] = relationship(back_populates="research_run")
    committee_reviews: Mapped[list[CommitteeReview]] = relationship(back_populates="research_run")
    cro_reviews: Mapped[list[CroReview]] = relationship(back_populates="research_run")
    governance_reports: Mapped[list[GovernanceResearchReport]] = relationship(
        back_populates="research_run"
    )

    __table_args__ = (
        Index("ix_research_runs_status_started", "status", "started_at"),
        Index("ix_research_runs_as_of_strategy", "as_of_date", "strategy_name"),
    )


class InvestmentReviewPacket(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "investment_review_packets"

    research_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False
    )
    ranking_run_id: Mapped[UUID] = mapped_column(nullable=False)
    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    packet_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0.0")
    packet_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    research_run: Mapped[ResearchRun] = relationship(back_populates="packets")
    stock: Mapped[Stock] = relationship("Stock")
    committee_reviews: Mapped[list[CommitteeReview]] = relationship(back_populates="packet")
    cro_reviews: Mapped[list[CroReview]] = relationship(back_populates="packet")

    __table_args__ = (
        UniqueConstraint(
            "research_run_id",
            "ranking_run_id",
            "stock_id",
            name="uq_investment_review_packets_run_stock",
        ),
        Index("ix_investment_review_packets_hash", "packet_hash"),
    )


class PromptVersion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "prompt_versions"

    committee_code: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    template_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LlmExecutionRecord(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "llm_execution_records"

    model: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    input_tokens: Mapped[int] = mapped_column(nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(nullable=False, default=0)
    request_ref: Mapped[str | None] = mapped_column(String(128))
    response_ref: Mapped[str | None] = mapped_column(String(128))
    latency_ms: Mapped[int | None] = mapped_column()
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommitteeReview(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "committee_reviews"

    research_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False
    )
    packet_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_review_packets.id", ondelete="CASCADE"), nullable=False
    )
    committee_code: Mapped[str] = mapped_column(String(16), nullable=False)
    committee_version: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=CommitteeReviewStatus.PENDING.value
    )
    findings: Mapped[str | None] = mapped_column(Text)
    strengths: Mapped[list[Any] | None] = mapped_column(JSONB)
    risks: Mapped[list[Any] | None] = mapped_column(JSONB)
    supporting_evidence: Mapped[list[Any] | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 4))
    extensions: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # M3.1 Investment Committee Evolution — advisory fields (additive)
    advisory_action: Mapped[str | None] = mapped_column(String(32))
    high_concern: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    high_concern_reason: Mapped[str | None] = mapped_column(Text)
    prompt_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="SET NULL")
    )
    llm_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("llm_execution_records.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    research_run: Mapped[ResearchRun] = relationship(back_populates="committee_reviews")
    packet: Mapped[InvestmentReviewPacket] = relationship(back_populates="committee_reviews")

    __table_args__ = (
        UniqueConstraint("packet_id", "committee_code", name="uq_committee_reviews_packet_code"),
        Index("ix_committee_reviews_run_code", "research_run_id", "committee_code"),
    )


class CroReview(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "cro_reviews"

    research_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False
    )
    packet_id: Mapped[UUID] = mapped_column(
        ForeignKey("investment_review_packets.id", ondelete="CASCADE"), nullable=False
    )
    aggregation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    dissent_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 4))
    # M3.1 Investment Committee Evolution — advisory fields (additive)
    cro_advisory_action: Mapped[str | None] = mapped_column(String(32))
    investment_committee_summary: Mapped[str | None] = mapped_column(Text)
    prompt_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="SET NULL")
    )
    llm_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("llm_execution_records.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    research_run: Mapped[ResearchRun] = relationship(back_populates="cro_reviews")
    packet: Mapped[InvestmentReviewPacket] = relationship(back_populates="cro_reviews")
    governance_report: Mapped[GovernanceResearchReport | None] = relationship(
        back_populates="cro_review", uselist=False
    )

    __table_args__ = (UniqueConstraint("packet_id", name="uq_cro_reviews_packet"),)


class GovernanceResearchReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "governance_research_reports"

    cro_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("cro_reviews.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    research_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[UUID] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    narrative_md: Mapped[str | None] = mapped_column(Text)
    structured: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    research_score: Mapped[float | None] = mapped_column(Numeric(8, 4))
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    cro_review: Mapped[CroReview] = relationship(back_populates="governance_report")
    research_run: Mapped[ResearchRun] = relationship(back_populates="governance_reports")
    stock: Mapped[Stock] = relationship("Stock")
    evidence: Mapped[list[GovernanceResearchReportEvidence]] = relationship(back_populates="report")

    __table_args__ = (
        Index("ix_governance_research_reports_run", "research_run_id"),
        Index("ix_governance_research_reports_symbol_date", "symbol", "as_of_date"),
    )


class GovernanceResearchReportEvidence(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "governance_research_report_evidence"

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("governance_research_reports.id", ondelete="CASCADE"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    report: Mapped[GovernanceResearchReport] = relationship(back_populates="evidence")
