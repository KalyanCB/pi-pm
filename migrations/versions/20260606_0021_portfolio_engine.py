"""Portfolio Engine M2: portfolio_configs table + extend portfolio_positions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260606_0021"
down_revision: str | None = "20260606_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_REGIME_SLOTS = {
    "risk_on":   {"max_positions": 8, "max_buy_per_day": 2},
    "neutral":   {"max_positions": 6, "max_buy_per_day": 1},
    "defensive": {"max_positions": 4, "max_buy_per_day": 0},
    "crisis":    {"max_positions": 2, "max_buy_per_day": 0},
}


def upgrade() -> None:
    op.create_table(
        "portfolio_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("total_equity", sa.Numeric(18, 2), nullable=False),
        sa.Column("deploy_pct", sa.Numeric(5, 4), nullable=False, server_default="0.85"),
        sa.Column("cash_floor_pct", sa.Numeric(5, 4), nullable=False, server_default="0.15"),
        sa.Column("reserve_pct", sa.Numeric(5, 4), nullable=False, server_default="0.02"),
        sa.Column("regime_slots", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("single_name_cap_pct", sa.Numeric(5, 4), nullable=False, server_default="0.18"),
        sa.Column("sector_cap_pct", sa.Numeric(5, 4), nullable=False, server_default="0.30"),
        sa.Column("slippage_bps", sa.Numeric(6, 2), nullable=False, server_default="5.0"),
        sa.Column("fee_per_leg", sa.Numeric(10, 2), nullable=False, server_default="20.0"),
        sa.Column("notes", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Seed default config (₹10L starting equity)
    import json
    op.execute(
        f"""INSERT INTO portfolio_configs (id, total_equity, deploy_pct, cash_floor_pct,
            reserve_pct, regime_slots, single_name_cap_pct, sector_cap_pct, slippage_bps, fee_per_leg)
        VALUES (
            '00000000-0000-4000-8000-000000000010',
            1000000,
            0.85,
            0.15,
            0.02,
            '{json.dumps(_DEFAULT_REGIME_SLOTS)}'::jsonb,
            0.18,
            0.30,
            5.0,
            20.0
        )"""
    )

    # Extend portfolio_positions
    op.add_column("portfolio_positions", sa.Column(
        "recommendation_result_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("recommendation_results.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.add_column("portfolio_positions", sa.Column("entry_price", sa.Numeric(18, 6), nullable=True))
    op.add_column("portfolio_positions", sa.Column("exit_price", sa.Numeric(18, 6), nullable=True))
    op.add_column("portfolio_positions", sa.Column("entry_date", sa.Date, nullable=True))
    op.add_column("portfolio_positions", sa.Column("exit_date", sa.Date, nullable=True))
    op.add_column("portfolio_positions", sa.Column("unrealized_pnl", sa.Numeric(18, 2), nullable=True))
    op.add_column("portfolio_positions", sa.Column("realized_pnl", sa.Numeric(18, 2), nullable=True))
    op.add_column("portfolio_positions", sa.Column("conviction_band", sa.String(16), nullable=True))
    op.add_column("portfolio_positions", sa.Column("strategy_name", sa.String(64), nullable=True))
    op.add_column("portfolio_positions", sa.Column("sector", sa.String(64), nullable=True))
    op.add_column("portfolio_positions", sa.Column(
        "position_status", sa.String(16), nullable=False, server_default="OPEN"
    ))
    op.add_column("portfolio_positions", sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    ))
    op.add_column("portfolio_positions", sa.Column(
        "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    ))
    op.create_index("ix_portfolio_positions_status", "portfolio_positions", ["position_status"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_positions_status", "portfolio_positions")
    for col in ["recommendation_result_id", "entry_price", "exit_price", "entry_date",
                "exit_date", "unrealized_pnl", "realized_pnl", "conviction_band",
                "strategy_name", "sector", "position_status", "created_at", "updated_at"]:
        op.drop_column("portfolio_positions", col)
    op.drop_table("portfolio_configs")
