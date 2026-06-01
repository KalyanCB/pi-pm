"""Sprint 8.6: daily batch orchestration runs and artifacts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260607_0015"
down_revision: str | None = "20260606_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_batch_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("universe_code", sa.String(length=64), nullable=False),
        sa.Column("benchmark_symbol", sa.String(length=32), nullable=False),
        sa.Column("target_trading_day", sa.Date(), nullable=True),
        sa.Column("from_date", sa.Date(), nullable=True),
        sa.Column("force_from_date", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("force_recompute", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("force_regenerate_rankings", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("current_phase", sa.String(length=32), nullable=True),
        sa.Column("percent_complete", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("current_load", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("parameter_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("plan_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("phase_results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_daily_batch_runs_idempotency_key"),
    )
    op.create_index("ix_daily_batch_runs_status_started", "daily_batch_runs", ["status", "started_at"])
    op.create_index("ix_daily_batch_runs_target_day", "daily_batch_runs", ["target_trading_day"])

    op.create_table(
        "daily_batch_run_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("daily_batch_run_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=True),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["daily_batch_run_id"], ["daily_batch_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "daily_batch_run_id",
            "artifact_type",
            "artifact_id",
            name="uq_daily_batch_run_artifacts_key",
        ),
    )
    op.create_index(
        "ix_daily_batch_run_artifacts_run_type",
        "daily_batch_run_artifacts",
        ["daily_batch_run_id", "artifact_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_daily_batch_run_artifacts_run_type", table_name="daily_batch_run_artifacts")
    op.drop_table("daily_batch_run_artifacts")
    op.drop_index("ix_daily_batch_runs_target_day", table_name="daily_batch_runs")
    op.drop_index("ix_daily_batch_runs_status_started", table_name="daily_batch_runs")
    op.drop_table("daily_batch_runs")
