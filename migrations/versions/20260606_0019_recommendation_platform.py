"""Recommendation Platform: recommendation_configs, recommendation_runs,
recommendation_results, recommendation_approvals, recommendation_outcomes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260606_0019"
down_revision: str | None = "20260609_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recommendation_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("config_version", sa.String(32), nullable=False, unique=True),
        sa.Column("config_blob", postgresql.JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "recommendation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ranking_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ranking_runs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("strategy_name", sa.String(64), nullable=False),
        sa.Column("universe_code", sa.String(32), nullable=False),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("config_version", sa.String(32), nullable=False),
        sa.Column("config_snapshot", postgresql.JSONB, nullable=False),
        sa.Column("regime_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_recommendation_runs_as_of_strategy",
        "recommendation_runs",
        ["as_of_date", "strategy_name"],
    )

    op.create_table(
        "recommendation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recommendation_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stock_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer, nullable=True),
        sa.Column("composite_score", sa.Numeric(18, 8), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=True),
        sa.Column("conviction_score", sa.SmallInteger, nullable=False),
        sa.Column("conviction_band", sa.String(16), nullable=False),
        sa.Column("conviction_components", postgresql.JSONB, nullable=False),
        sa.Column("reason_codes", postgresql.JSONB, nullable=False),
        sa.Column(
            "portfolio_position_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolio_positions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "prior_recommendation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recommendation_results.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "args_research_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "recommendation_run_id", "stock_id", name="uq_rec_results_run_stock"
        ),
    )
    op.create_index(
        "ix_rec_results_run_action", "recommendation_results", ["recommendation_run_id", "action"]
    )
    op.create_index(
        "ix_rec_results_stock_lifecycle", "recommendation_results", ["stock_id", "lifecycle_state"]
    )

    op.create_table(
        "recommendation_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recommendation_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recommendation_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("approval_type", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=True, unique=True),
    )

    op.create_table(
        "recommendation_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recommendation_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recommendation_results.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("outcome_status", sa.String(16), nullable=False, server_default="OPEN"),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("exit_date", sa.Date, nullable=True),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("exit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("holding_days", sa.Integer, nullable=True),
        sa.Column("pnl_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_gain_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_drawdown_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("benchmark_return_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("alpha_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("exit_reason_codes", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("recommendation_outcomes")
    op.drop_table("recommendation_approvals")
    op.drop_index("ix_rec_results_stock_lifecycle", "recommendation_results")
    op.drop_index("ix_rec_results_run_action", "recommendation_results")
    op.drop_table("recommendation_results")
    op.drop_index("ix_recommendation_runs_as_of_strategy", "recommendation_runs")
    op.drop_table("recommendation_runs")
    op.drop_table("recommendation_configs")
