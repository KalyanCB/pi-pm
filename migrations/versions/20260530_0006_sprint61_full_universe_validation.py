"""Sprint 6.1: full-universe validation campaign tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260530_0006"
down_revision: str | None = "20260530_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "full_universe_validation_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("universe_code", sa.String(length=32), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ranking_runs_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ranking_runs_reused", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_days_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_days_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_full_universe_validation_campaigns_status",
        "full_universe_validation_campaigns",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_full_universe_validation_campaigns_dates",
        "full_universe_validation_campaigns",
        ["start_date", "end_date"],
        unique=False,
    )

    op.create_table(
        "full_universe_validation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ranking_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["full_universe_validation_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["ranking_run_id"], ["ranking_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "ranking_run_id",
            name="uq_full_universe_validation_run_campaign_ranking",
        ),
    )
    op.create_index(
        "ix_full_universe_validation_runs_campaign",
        "full_universe_validation_runs",
        ["campaign_id"],
        unique=False,
    )

    op.create_table(
        "full_universe_validation_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("ic_pearson", sa.Numeric(18, 8), nullable=True),
        sa.Column("rank_ic_spearman", sa.Numeric(18, 8), nullable=True),
        sa.Column("hit_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("directional_hit_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("top_decile_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("bottom_decile_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("spread", sa.Numeric(18, 8), nullable=True),
        sa.Column("top_20_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("top_50_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ranked_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_monotonic", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["full_universe_validation_campaigns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "horizon",
            name="uq_full_universe_validation_metrics_campaign_horizon",
        ),
    )

    op.create_table(
        "full_universe_validation_deciles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("decile", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("median_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("win_rate", sa.Numeric(18, 8), nullable=True),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["full_universe_validation_campaigns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "horizon",
            "decile",
            name="uq_full_universe_validation_deciles_campaign_horizon_decile",
        ),
    )


def downgrade() -> None:
    op.drop_table("full_universe_validation_deciles")
    op.drop_table("full_universe_validation_metrics")
    op.drop_index("ix_full_universe_validation_runs_campaign", table_name="full_universe_validation_runs")
    op.drop_table("full_universe_validation_runs")
    op.drop_index(
        "ix_full_universe_validation_campaigns_dates",
        table_name="full_universe_validation_campaigns",
    )
    op.drop_index(
        "ix_full_universe_validation_campaigns_status",
        table_name="full_universe_validation_campaigns",
    )
    op.drop_table("full_universe_validation_campaigns")
