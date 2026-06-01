"""Sprint 8.3: exit research run progress tracking columns."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260605_0013"
down_revision: str | None = "20260604_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exit_research_runs",
        sa.Column("total_entries", sa.Integer(), nullable=True),
    )
    op.add_column(
        "exit_research_runs",
        sa.Column("processed_entries", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "exit_research_runs",
        sa.Column("percent_complete", sa.Numeric(precision=8, scale=4), nullable=True),
    )
    op.add_column(
        "exit_research_runs",
        sa.Column("last_progress_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "exit_research_runs",
        sa.Column("elapsed_seconds", sa.Numeric(precision=12, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("exit_research_runs", "elapsed_seconds")
    op.drop_column("exit_research_runs", "last_progress_at")
    op.drop_column("exit_research_runs", "percent_complete")
    op.drop_column("exit_research_runs", "processed_entries")
    op.drop_column("exit_research_runs", "total_entries")
