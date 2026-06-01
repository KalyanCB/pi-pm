"""Sprint 8.3: exit research workspace schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260603_0011"
down_revision: str | None = "20260602_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exit_research_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("as_of_date_start", sa.Date(), nullable=False),
        sa.Column("as_of_date_end", sa.Date(), nullable=False),
        sa.Column("holdout_start_date", sa.Date(), nullable=False),
        sa.Column("signals_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parameter_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exit_research_runs_status_started",
        "exit_research_runs",
        ["status", "started_at"],
        unique=False,
    )

    op.create_table(
        "exit_research_policy_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_family", sa.String(length=32), nullable=False),
        sa.Column("policy_variant", sa.String(length=64), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("regime_label", sa.String(length=32), nullable=False),
        sa.Column("dataset_split", sa.String(length=16), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mean_return", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("median_return", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("std_dev", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("hit_rate", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("avg_holding_days", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("ci_lower", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("ci_upper", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("conclusion_status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("holdout_start_date", sa.Date(), nullable=False),
        sa.Column("as_of_date_start", sa.Date(), nullable=False),
        sa.Column("as_of_date_end", sa.Date(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["exit_research_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "research_run_id",
            "policy_family",
            "policy_variant",
            "strategy_name",
            "strategy_version",
            "universe_code",
            "regime_label",
            "dataset_split",
            "horizon",
            name="uq_exit_research_policy_metrics_key",
        ),
    )
    op.create_index(
        "ix_exit_policy_metrics_query",
        "exit_research_policy_metrics",
        ["policy_family", "regime_label", "dataset_split"],
        unique=False,
    )

    op.create_table(
        "exit_research_alpha_decay_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("regime_label", sa.String(length=32), nullable=False),
        sa.Column("dataset_split", sa.String(length=16), nullable=False),
        sa.Column("trading_day", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mean_return", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("cumulative_mean_return", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("conclusion_status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("holdout_start_date", sa.Date(), nullable=False),
        sa.Column("as_of_date_start", sa.Date(), nullable=False),
        sa.Column("as_of_date_end", sa.Date(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["exit_research_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "research_run_id",
            "strategy_name",
            "strategy_version",
            "universe_code",
            "regime_label",
            "dataset_split",
            "trading_day",
            name="uq_exit_alpha_decay_point_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("exit_research_alpha_decay_points")
    op.drop_index("ix_exit_policy_metrics_query", table_name="exit_research_policy_metrics")
    op.drop_table("exit_research_policy_metrics")
    op.drop_index("ix_exit_research_runs_status_started", table_name="exit_research_runs")
    op.drop_table("exit_research_runs")
