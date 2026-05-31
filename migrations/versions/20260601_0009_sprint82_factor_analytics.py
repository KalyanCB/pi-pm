"""Sprint 8.2: factor predictive power analytics (schema only)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260601_0009"
down_revision: str | None = "20260531_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "factor_performance_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=True),
        sa.Column("as_of_date_start", sa.Date(), nullable=False),
        sa.Column("as_of_date_end", sa.Date(), nullable=False),
        sa.Column("holdout_start_date", sa.Date(), nullable=False),
        sa.Column("reports_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parameter_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_factor_performance_runs_status_started",
        "factor_performance_runs",
        ["status", "started_at"],
        unique=False,
    )

    op.create_table(
        "factor_daily_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factor_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("regime_label", sa.String(length=32), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("ranking_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("dataset_split", sa.String(length=16), nullable=False),
        sa.Column("ic_spearman", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ranking_run_id"],
            ["ranking_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "factor_name",
            "strategy_name",
            "strategy_version",
            "universe_code",
            "regime_label",
            "horizon",
            "ranking_run_id",
            name="uq_factor_daily_metrics_run_factor",
        ),
    )
    op.create_index(
        "ix_factor_daily_metrics_time",
        "factor_daily_metrics",
        ["factor_name", "as_of_date", "horizon"],
        unique=False,
    )
    op.create_index(
        "ix_factor_daily_metrics_run",
        "factor_daily_metrics",
        ["ranking_run_id"],
        unique=False,
    )

    op.create_table(
        "factor_performance_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factor_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("regime_label", sa.String(length=32), nullable=False),
        sa.Column("dataset_split", sa.String(length=16), nullable=False),
        sa.Column("ic_spearman", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("ic_pearson", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("hit_rate", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("spread_contribution", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ranked_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("regime_coverage_pct", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("stability_score", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("stability_label", sa.String(length=32), nullable=True),
        sa.Column("coverage_label", sa.String(length=32), nullable=True),
        sa.Column("bootstrap_ci_lower", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("bootstrap_ci_upper", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("p_value", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("is_statistically_significant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="low"),
        sa.Column("bootstrap_sample_count", sa.Integer(), nullable=True),
        sa.Column("bootstrap_method", sa.String(length=64), nullable=True),
        sa.Column("holdout_start_date", sa.Date(), nullable=False),
        sa.Column("as_of_date_start", sa.Date(), nullable=False),
        sa.Column("as_of_date_end", sa.Date(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "factor_name",
            "strategy_name",
            "strategy_version",
            "universe_code",
            "horizon",
            "regime_label",
            "dataset_split",
            "as_of_date_start",
            "as_of_date_end",
            "holdout_start_date",
            name="uq_factor_performance_metrics_key",
        ),
    )
    op.create_index(
        "ix_fpm_query",
        "factor_performance_metrics",
        ["strategy_name", "universe_code", "horizon", "regime_label", "dataset_split"],
        unique=False,
    )
    op.create_index(
        "ix_fpm_factor",
        "factor_performance_metrics",
        ["factor_name", "horizon", "dataset_split"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fpm_factor", table_name="factor_performance_metrics")
    op.drop_index("ix_fpm_query", table_name="factor_performance_metrics")
    op.drop_table("factor_performance_metrics")
    op.drop_index("ix_factor_daily_metrics_run", table_name="factor_daily_metrics")
    op.drop_index("ix_factor_daily_metrics_time", table_name="factor_daily_metrics")
    op.drop_table("factor_daily_metrics")
    op.drop_index("ix_factor_performance_runs_status_started", table_name="factor_performance_runs")
    op.drop_table("factor_performance_runs")
