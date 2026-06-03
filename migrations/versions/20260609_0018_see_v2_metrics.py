"""SEE v2: strategy-aware retrieval, extended metrics, evidence score."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260609_0018"
down_revision: str | None = "20260608_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "stock_setup_research",
        sa.Column("strategy_name", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "stock_setup_research",
        sa.Column("engine_version", sa.String(length=16), nullable=False, server_default="see_v2"),
    )
    op.add_column(
        "stock_setup_research",
        sa.Column("total_matches", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "stock_setup_research",
        sa.Column("qualifying_matches", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "stock_setup_research",
        sa.Column("setup_evidence_score", sa.Numeric(precision=6, scale=2), nullable=True),
    )

    op.add_column(
        "stock_setup_research_metrics",
        sa.Column("standard_deviation_20d", sa.Numeric(precision=18, scale=8), nullable=True),
    )
    op.add_column(
        "stock_setup_research_metrics",
        sa.Column("max_return_20d", sa.Numeric(precision=18, scale=8), nullable=True),
    )
    op.add_column(
        "stock_setup_research_metrics",
        sa.Column("min_return_20d", sa.Numeric(precision=18, scale=8), nullable=True),
    )
    op.add_column(
        "stock_setup_research_metrics",
        sa.Column("confidence_interval_95_lower_20d", sa.Numeric(precision=18, scale=8), nullable=True),
    )
    op.add_column(
        "stock_setup_research_metrics",
        sa.Column("confidence_interval_95_upper_20d", sa.Numeric(precision=18, scale=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stock_setup_research_metrics", "confidence_interval_95_upper_20d")
    op.drop_column("stock_setup_research_metrics", "confidence_interval_95_lower_20d")
    op.drop_column("stock_setup_research_metrics", "min_return_20d")
    op.drop_column("stock_setup_research_metrics", "max_return_20d")
    op.drop_column("stock_setup_research_metrics", "standard_deviation_20d")
    op.drop_column("stock_setup_research", "setup_evidence_score")
    op.drop_column("stock_setup_research", "qualifying_matches")
    op.drop_column("stock_setup_research", "total_matches")
    op.drop_column("stock_setup_research", "engine_version")
    op.drop_column("stock_setup_research", "strategy_name")
