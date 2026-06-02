"""SEE v1: stock setup research tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0017"
down_revision: str | None = "20260608_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_setup_research",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ranking_run_id", sa.Uuid(), nullable=False),
        sa.Column("ranking_result_id", sa.Uuid(), nullable=True),
        sa.Column("stock_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reference_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("similar_setups", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("nearest_n", sa.Integer(), nullable=False),
        sa.Column("min_similarity", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("match_count", sa.Integer(), nullable=False),
        sa.Column("parameter_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("research_hash", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ranking_result_id"], ["ranking_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ranking_run_id"], ["ranking_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ranking_run_id", "stock_id", name="uq_stock_setup_research_run_stock"),
    )
    op.create_index(
        "ix_stock_setup_research_run", "stock_setup_research", ["ranking_run_id"], unique=False
    )
    op.create_index(
        "ix_stock_setup_research_symbol", "stock_setup_research", ["symbol"], unique=False
    )

    op.create_table(
        "stock_setup_research_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stock_setup_research_id", sa.Uuid(), nullable=False),
        sa.Column("regime_label", sa.String(length=32), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("win_rate_5d", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column("win_rate_20d", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column("avg_return_5d", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("avg_return_20d", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("median_return_20d", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("avg_max_drawdown", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("avg_max_runup", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("avg_similarity_score", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.ForeignKeyConstraint(
            ["stock_setup_research_id"], ["stock_setup_research.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stock_setup_research_id",
            "regime_label",
            name="uq_stock_setup_research_metrics_regime",
        ),
    )
    op.create_index(
        "ix_stock_setup_research_metrics_research",
        "stock_setup_research_metrics",
        ["stock_setup_research_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_stock_setup_research_metrics_research", table_name="stock_setup_research_metrics")
    op.drop_table("stock_setup_research_metrics")
    op.drop_index("ix_stock_setup_research_symbol", table_name="stock_setup_research")
    op.drop_index("ix_stock_setup_research_run", table_name="stock_setup_research")
    op.drop_table("stock_setup_research")

