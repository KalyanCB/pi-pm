"""Sprint 8.1: regime-aware trading policy layer (schema only)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260531_0008"
down_revision: str | None = "20260530_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "regime_policy_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_name", sa.String(length=64), nullable=False),
        sa.Column("policy_type", sa.String(length=32), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("allowed_regimes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("size_multipliers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("min_decile", sa.Integer(), nullable=True),
        sa.Column("max_decile", sa.Integer(), nullable=True),
        sa.Column("default_action", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_name",
            "policy_version",
            name="uq_regime_policy_configs_name_version",
        ),
    )
    op.create_index(
        "ix_regime_policy_configs_strategy_status",
        "regime_policy_configs",
        ["strategy_name", "strategy_version", "status"],
        unique=False,
    )

    op.create_table(
        "regime_policy_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ranking_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("validation_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("regime_label", sa.String(length=32), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("size_multiplier", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("decile_filter", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("experiment_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["policy_config_id"],
            ["regime_policy_configs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ranking_run_id"],
            ["ranking_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["validation_report_id"],
            ["ranking_validation_reports.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_run_id"],
            ["experiment_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_regime_policy_decisions_run",
        "regime_policy_decisions",
        ["ranking_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_regime_policy_decisions_date_regime",
        "regime_policy_decisions",
        ["as_of_date", "regime_label"],
        unique=False,
    )
    op.create_index(
        "ix_regime_policy_decisions_experiment",
        "regime_policy_decisions",
        ["experiment_run_id"],
        unique=False,
    )

    op.create_table(
        "regime_backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experiment_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_policy_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("universe_code", sa.String(length=32), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("window_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("holdout_start_date", sa.Date(), nullable=True),
        sa.Column("train_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("holdout_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("comparison_vs_baseline", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("research_findings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("days_included", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("days_excluded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["experiment_run_id"],
            ["experiment_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["policy_config_id"],
            ["regime_policy_configs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_policy_config_id"],
            ["regime_policy_configs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_regime_backtest_runs_experiment",
        "regime_backtest_runs",
        ["experiment_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_regime_backtest_runs_policy",
        "regime_backtest_runs",
        ["policy_config_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_regime_backtest_runs_policy", table_name="regime_backtest_runs")
    op.drop_index("ix_regime_backtest_runs_experiment", table_name="regime_backtest_runs")
    op.drop_table("regime_backtest_runs")
    op.drop_index("ix_regime_policy_decisions_experiment", table_name="regime_policy_decisions")
    op.drop_index("ix_regime_policy_decisions_date_regime", table_name="regime_policy_decisions")
    op.drop_index("ix_regime_policy_decisions_run", table_name="regime_policy_decisions")
    op.drop_table("regime_policy_decisions")
    op.drop_index("ix_regime_policy_configs_strategy_status", table_name="regime_policy_configs")
    op.drop_table("regime_policy_configs")
