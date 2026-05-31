"""Widen factor_performance_metrics label columns for adequate_coverage (17 chars)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0010"
down_revision: str | None = "20260601_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "factor_performance_metrics",
        "coverage_label",
        existing_type=sa.String(length=16),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
    op.alter_column(
        "factor_performance_metrics",
        "stability_label",
        existing_type=sa.String(length=16),
        type_=sa.String(length=32),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "factor_performance_metrics",
        "stability_label",
        existing_type=sa.String(length=32),
        type_=sa.String(length=16),
        existing_nullable=True,
    )
    op.alter_column(
        "factor_performance_metrics",
        "coverage_label",
        existing_type=sa.String(length=32),
        type_=sa.String(length=16),
        existing_nullable=True,
    )
