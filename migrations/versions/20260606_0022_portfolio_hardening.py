"""Portfolio hardening M2.2: nav_history, cash_ledger, reconciliation_reports, exit_recommendations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260606_0022"
down_revision: str | None = "20260606_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_nav_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("as_of_date", sa.Date, nullable=False, unique=True),
        sa.Column("total_equity", sa.Numeric(18, 2), nullable=False),
        sa.Column("cash_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("market_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("realized_pnl_cumulative", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("open_positions", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("cash_pct", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("day_return_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("benchmark_return_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("alpha_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("regime_label", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_portfolio_nav_history_date", "portfolio_nav_history", ["as_of_date"])

    op.create_table(
        "portfolio_cash_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(18, 2), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(32), nullable=True),
        sa.Column("description", sa.String(256), nullable=True),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_cash_ledger_date", "portfolio_cash_ledger", ["as_of_date"])
    op.create_index("ix_cash_ledger_type", "portfolio_cash_ledger", ["entry_type"])

    op.create_table(
        "portfolio_reconciliation_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("as_of_date", sa.Date, nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("cash_from_ledger", sa.Numeric(18, 2), nullable=False),
        sa.Column("market_value_from_positions", sa.Numeric(18, 2), nullable=False),
        sa.Column("realized_pnl_from_closed", sa.Numeric(18, 2), nullable=False),
        sa.Column("computed_nav", sa.Numeric(18, 2), nullable=False),
        sa.Column("reported_nav", sa.Numeric(18, 2), nullable=False),
        sa.Column("discrepancy", sa.Numeric(18, 2), nullable=False),
        sa.Column("discrepancy_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("checks", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("warnings", postgresql.JSONB, nullable=True),
        sa.Column("failures", postgresql.JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_recon_reports_status", "portfolio_reconciliation_reports", ["status"])
    op.create_index("ix_recon_reports_date", "portfolio_reconciliation_reports", ["as_of_date"])

    op.create_table(
        "portfolio_exit_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_position_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolio_positions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stock_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("triggers", postgresql.JSONB, nullable=False),
        sa.Column("trigger_details", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("current_rank", sa.Integer, nullable=True),
        sa.Column("days_held", sa.Integer, nullable=True),
        sa.Column("unrealized_pnl_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("urgency", sa.String(16), nullable=False, server_default="NORMAL"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_exit_recs_status", "portfolio_exit_recommendations", ["status"])
    op.create_index("ix_exit_recs_date", "portfolio_exit_recommendations", ["as_of_date"])
    op.create_index("ix_exit_recs_position", "portfolio_exit_recommendations", ["portfolio_position_id"])

    # Add position_sizing_version to portfolio_configs
    op.add_column("portfolio_configs", sa.Column(
        "position_sizing_version", sa.String(8), nullable=False, server_default="v1"
    ))


def downgrade() -> None:
    op.drop_column("portfolio_configs", "position_sizing_version")
    op.drop_index("ix_exit_recs_position", "portfolio_exit_recommendations")
    op.drop_index("ix_exit_recs_date", "portfolio_exit_recommendations")
    op.drop_index("ix_exit_recs_status", "portfolio_exit_recommendations")
    op.drop_table("portfolio_exit_recommendations")
    op.drop_index("ix_recon_reports_date", "portfolio_reconciliation_reports")
    op.drop_index("ix_recon_reports_status", "portfolio_reconciliation_reports")
    op.drop_table("portfolio_reconciliation_reports")
    op.drop_index("ix_cash_ledger_type", "portfolio_cash_ledger")
    op.drop_index("ix_cash_ledger_date", "portfolio_cash_ledger")
    op.drop_table("portfolio_cash_ledger")
    op.drop_index("ix_portfolio_nav_history_date", "portfolio_nav_history")
    op.drop_table("portfolio_nav_history")
