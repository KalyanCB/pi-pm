"""Sprint 3.1: nullable inputs_hash for failed ranking runs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260530_0004"
down_revision: str | None = "20260530_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("ranking_runs", "inputs_hash", existing_type=sa.String(length=64), nullable=True)
    op.execute(
        sa.text(
            """
            UPDATE ranking_runs
            SET inputs_hash = NULL
            WHERE status IN ('failed', 'pending')
               OR inputs_hash = 'pending'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE ranking_runs
            SET inputs_hash = 'unknown'
            WHERE inputs_hash IS NULL
            """
        )
    )
    op.alter_column(
        "ranking_runs", "inputs_hash", existing_type=sa.String(length=64), nullable=False
    )
