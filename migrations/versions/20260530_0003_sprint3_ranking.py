"""Sprint 3: ranking engine and performance snapshots."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260530_0003"
down_revision: str | None = "20260530_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ranking_runs", sa.Column("universe_code", sa.String(length=32), nullable=True))
    op.add_column("ranking_runs", sa.Column("benchmark_symbol", sa.String(length=32), nullable=True))
    op.add_column(
        "ranking_runs", sa.Column("filter_config_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "ranking_runs",
        sa.Column("normalization_method", sa.String(length=16), nullable=True, server_default="percentile"),
    )
    op.add_column("ranking_runs", sa.Column("error_message", sa.Text(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE ranking_runs
            SET universe_code = 'UNKNOWN',
                benchmark_symbol = 'UNKNOWN',
                filter_config_hash = inputs_hash,
                normalization_method = 'percentile'
            WHERE universe_code IS NULL
            """
        )
    )

    op.alter_column("ranking_runs", "universe_code", nullable=False)
    op.alter_column("ranking_runs", "benchmark_symbol", nullable=False)
    op.alter_column("ranking_runs", "filter_config_hash", nullable=False)
    op.alter_column("ranking_runs", "normalization_method", nullable=False)

    op.create_index(
        "ix_ranking_runs_universe_as_of",
        "ranking_runs",
        ["universe_code", "as_of_date"],
        unique=False,
    )
    op.create_index(
        "ix_ranking_runs_strategy_as_of",
        "ranking_runs",
        ["strategy_name", "strategy_version", "as_of_date"],
        unique=False,
    )

    op.create_table(
        "ranking_performance_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ranking_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_5d", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("return_10d", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("return_20d", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("return_60d", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ranking_run_id"], ["ranking_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ranking_run_id", "stock_id", name="uq_ranking_performance_run_stock"
        ),
    )
    op.create_index(
        "ix_ranking_performance_run",
        "ranking_performance_snapshots",
        ["ranking_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ranking_performance_run", table_name="ranking_performance_snapshots")
    op.drop_table("ranking_performance_snapshots")
    op.drop_index("ix_ranking_runs_strategy_as_of", table_name="ranking_runs")
    op.drop_index("ix_ranking_runs_universe_as_of", table_name="ranking_runs")
    op.drop_column("ranking_runs", "error_message")
    op.drop_column("ranking_runs", "normalization_method")
    op.drop_column("ranking_runs", "filter_config_hash")
    op.drop_column("ranking_runs", "benchmark_symbol")
    op.drop_column("ranking_runs", "universe_code")
