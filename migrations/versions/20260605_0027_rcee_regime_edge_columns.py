"""ADR-032: RCEE regime edge columns for strategy_regime_performance and recommendation_results."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260605_0027"
down_revision: str | None = "20260610_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # strategy_regime_performance: add OOS IC columns
    op.add_column(
        "strategy_regime_performance",
        sa.Column("ic_std", sa.Numeric(18, 8), nullable=True),
    )
    op.add_column(
        "strategy_regime_performance",
        sa.Column("ic_lower_95", sa.Numeric(18, 8), nullable=True),
    )
    op.add_column(
        "strategy_regime_performance",
        sa.Column("hit_rate", sa.Numeric(18, 8), nullable=True),
    )
    op.add_column(
        "strategy_regime_performance",
        sa.Column("expectancy", sa.Numeric(18, 8), nullable=True),
    )
    op.add_column(
        "strategy_regime_performance",
        sa.Column("expectancy_after_costs", sa.Numeric(18, 8), nullable=True),
    )
    op.add_column(
        "strategy_regime_performance",
        sa.Column("computed_from", sa.String(32), nullable=True),
    )

    # recommendation_results: add confidence column
    op.add_column(
        "recommendation_results",
        sa.Column("recommendation_confidence", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recommendation_results", "recommendation_confidence")
    op.drop_column("strategy_regime_performance", "computed_from")
    op.drop_column("strategy_regime_performance", "expectancy_after_costs")
    op.drop_column("strategy_regime_performance", "expectancy")
    op.drop_column("strategy_regime_performance", "hit_rate")
    op.drop_column("strategy_regime_performance", "ic_lower_95")
    op.drop_column("strategy_regime_performance", "ic_std")
