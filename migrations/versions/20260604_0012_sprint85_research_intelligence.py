"""Sprint 8.5: research intelligence / executive reporting schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260604_0012"
down_revision: str | None = "20260603_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_intelligence_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("as_of_date_start", sa.Date(), nullable=False),
        sa.Column("as_of_date_end", sa.Date(), nullable=False),
        sa.Column("holdout_start_date", sa.Date(), nullable=False),
        sa.Column("parameter_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "research_intelligence_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["research_intelligence_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "report_type",
            name="uq_research_intelligence_report_run_type",
        ),
    )


def downgrade() -> None:
    op.drop_table("research_intelligence_reports")
    op.drop_table("research_intelligence_runs")
