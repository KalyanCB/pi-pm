"""ADR-033: intraday exit monitor — schema additions.

Adds:
  portfolio_exit_recommendations.monitor_tier   INTRADAY | DAILY (default DAILY)
  portfolio_exit_recommendations.auto_executed  bool (default false) — critical stop bypass
  portfolio_exit_recommendations.actor_id       who fired it (system | user_id)
  portfolio_positions.stop_loss_price           absolute stop price computed at entry
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0027"
down_revision: tuple[str, str] = ("20260610_0026", "20260605_0027")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portfolio_exit_recommendations",
        sa.Column(
            "monitor_tier",
            sa.String(16),
            nullable=False,
            server_default="DAILY",
        ),
    )
    op.add_column(
        "portfolio_exit_recommendations",
        sa.Column(
            "auto_executed",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "portfolio_exit_recommendations",
        sa.Column("actor_id", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_exit_recs_tier",
        "portfolio_exit_recommendations",
        ["monitor_tier"],
    )
    op.add_column(
        "portfolio_positions",
        sa.Column("stop_loss_price", sa.Numeric(18, 6), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portfolio_positions", "stop_loss_price")
    op.drop_index("ix_exit_recs_tier", table_name="portfolio_exit_recommendations")
    op.drop_column("portfolio_exit_recommendations", "actor_id")
    op.drop_column("portfolio_exit_recommendations", "auto_executed")
    op.drop_column("portfolio_exit_recommendations", "monitor_tier")
