"""Sprint 4.2: ranking_validation_reports."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260530_0005"
down_revision: str | None = "20260530_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ranking_validation_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ranking_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("validation_hash", sa.String(length=64), nullable=True),
        sa.Column("regime_label", sa.String(length=32), nullable=True),
        sa.Column("trend_regime", sa.String(length=16), nullable=True),
        sa.Column("vol_regime", sa.String(length=16), nullable=True),
        sa.Column("horizon_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sample_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ranking_run_id"], ["ranking_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ranking_run_id", name="uq_ranking_validation_report_run"),
    )
    op.create_index(
        "ix_ranking_validation_reports_status",
        "ranking_validation_reports",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_ranking_validation_reports_regime",
        "ranking_validation_reports",
        ["regime_label"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ranking_validation_reports_regime", table_name="ranking_validation_reports")
    op.drop_index("ix_ranking_validation_reports_status", table_name="ranking_validation_reports")
    op.drop_table("ranking_validation_reports")
