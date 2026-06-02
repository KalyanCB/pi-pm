"""ARGS Phase 1: research runs, packets, committee/CRO reviews, governance reports."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0016"
down_revision: str | None = "20260607_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("committee_code", sa.String(length=16), nullable=False),
        sa.Column("version", sa.String(length=16), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("template_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "llm_execution_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("request_ref", sa.String(length=128), nullable=True),
        sa.Column("response_ref", sa.String(length=128), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "research_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("trigger_mode", sa.String(length=16), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=16), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("top_n", sa.Integer(), nullable=False),
        sa.Column("committee_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("config_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ranking_run_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("daily_batch_run_id", sa.Uuid(), nullable=True),
        sa.Column("checkpoint_ref", sa.String(length=128), nullable=True),
        sa.Column("phase", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_runs_status_started", "research_runs", ["status", "started_at"]
    )
    op.create_index(
        "ix_research_runs_as_of_strategy", "research_runs", ["as_of_date", "strategy_name"]
    )

    op.create_table(
        "investment_review_packets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("ranking_run_id", sa.Uuid(), nullable=False),
        sa.Column("stock_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("packet_version", sa.String(length=16), nullable=False),
        sa.Column("packet_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "research_run_id",
            "ranking_run_id",
            "stock_id",
            name="uq_investment_review_packets_run_stock",
        ),
    )
    op.create_index(
        "ix_investment_review_packets_hash", "investment_review_packets", ["packet_hash"]
    )

    op.create_table(
        "committee_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("packet_id", sa.Uuid(), nullable=False),
        sa.Column("committee_code", sa.String(length=16), nullable=False),
        sa.Column("committee_version", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("supporting_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("extensions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("prompt_version_id", sa.Uuid(), nullable=True),
        sa.Column("llm_execution_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["packet_id"], ["investment_review_packets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["llm_execution_id"], ["llm_execution_records.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("packet_id", "committee_code", name="uq_committee_reviews_packet_code"),
    )
    op.create_index(
        "ix_committee_reviews_run_code", "committee_reviews", ["research_run_id", "committee_code"]
    )

    op.create_table(
        "cro_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("packet_id", sa.Uuid(), nullable=False),
        sa.Column("aggregation_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("dissent_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("prompt_version_id", sa.Uuid(), nullable=True),
        sa.Column("llm_execution_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["packet_id"], ["investment_review_packets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["llm_execution_id"], ["llm_execution_records.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("packet_id", name="uq_cro_reviews_packet"),
    )

    op.create_table(
        "governance_research_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cro_review_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("stock_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("narrative_md", sa.Text(), nullable=True),
        sa.Column("structured", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("research_score", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cro_review_id"], ["cro_reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cro_review_id"),
    )
    op.create_index(
        "ix_governance_research_reports_run", "governance_research_reports", ["research_run_id"]
    )
    op.create_index(
        "ix_governance_research_reports_symbol_date",
        "governance_research_reports",
        ["symbol", "as_of_date"],
    )

    op.create_table(
        "governance_research_report_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("evidence_ref", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"], ["governance_research_reports.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("governance_research_report_evidence")
    op.drop_index(
        "ix_governance_research_reports_symbol_date", table_name="governance_research_reports"
    )
    op.drop_index("ix_governance_research_reports_run", table_name="governance_research_reports")
    op.drop_table("governance_research_reports")
    op.drop_table("cro_reviews")
    op.drop_index("ix_committee_reviews_run_code", table_name="committee_reviews")
    op.drop_table("committee_reviews")
    op.drop_index("ix_investment_review_packets_hash", table_name="investment_review_packets")
    op.drop_table("investment_review_packets")
    op.drop_index("ix_research_runs_as_of_strategy", table_name="research_runs")
    op.drop_index("ix_research_runs_status_started", table_name="research_runs")
    op.drop_table("research_runs")
    op.drop_table("llm_execution_records")
    op.drop_table("prompt_versions")
