"""Sprint 8.3: exit research run phase and persistence progress columns."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260606_0014"
down_revision: str | None = "20260605_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exit_research_runs",
        sa.Column("current_phase", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "exit_research_runs",
        sa.Column("persistence_items_total", sa.Integer(), nullable=True),
    )
    op.add_column(
        "exit_research_runs",
        sa.Column("persistence_items_processed", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("exit_research_runs", "persistence_items_processed")
    op.drop_column("exit_research_runs", "persistence_items_total")
    op.drop_column("exit_research_runs", "current_phase")
