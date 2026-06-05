"""Extend recommendation_outcomes: add symbol, strategy_name, conviction_band,
regime_label, days_held, target_hit, stop_hit, exit_reason, committee_advisory.
Rename holding_days → days_held. Add analytics indexes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260606_0020"
down_revision: str | None = "20260606_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Denormalised lookup columns
    op.add_column("recommendation_outcomes", sa.Column("symbol", sa.String(32), nullable=True))
    op.add_column("recommendation_outcomes", sa.Column("strategy_name", sa.String(64), nullable=True))
    op.add_column("recommendation_outcomes", sa.Column("conviction_band", sa.String(16), nullable=True))
    op.add_column("recommendation_outcomes", sa.Column("regime_label", sa.String(32), nullable=True))

    # Rename holding_days → days_held
    op.add_column("recommendation_outcomes", sa.Column("days_held", sa.Integer, nullable=True))
    # Copy existing data
    op.execute("UPDATE recommendation_outcomes SET days_held = holding_days")
    op.drop_column("recommendation_outcomes", "holding_days")

    # Exit tracking
    op.add_column("recommendation_outcomes", sa.Column("target_hit", sa.Boolean, nullable=True))
    op.add_column("recommendation_outcomes", sa.Column("stop_hit", sa.Boolean, nullable=True))
    op.add_column("recommendation_outcomes", sa.Column("exit_reason", sa.String(64), nullable=True))

    # Committee advisory snapshot at entry
    op.add_column("recommendation_outcomes", sa.Column("committee_advisory", sa.String(32), nullable=True))

    # Analytics indexes
    op.create_index(
        "ix_rec_outcomes_strategy_status",
        "recommendation_outcomes",
        ["strategy_name", "outcome_status"],
    )
    op.create_index(
        "ix_rec_outcomes_conviction_band",
        "recommendation_outcomes",
        ["conviction_band"],
    )
    op.create_index(
        "ix_rec_outcomes_regime",
        "recommendation_outcomes",
        ["regime_label"],
    )


def downgrade() -> None:
    op.drop_index("ix_rec_outcomes_regime", "recommendation_outcomes")
    op.drop_index("ix_rec_outcomes_conviction_band", "recommendation_outcomes")
    op.drop_index("ix_rec_outcomes_strategy_status", "recommendation_outcomes")
    op.drop_column("recommendation_outcomes", "committee_advisory")
    op.drop_column("recommendation_outcomes", "exit_reason")
    op.drop_column("recommendation_outcomes", "stop_hit")
    op.drop_column("recommendation_outcomes", "target_hit")
    op.add_column("recommendation_outcomes", sa.Column("holding_days", sa.Integer, nullable=True))
    op.execute("UPDATE recommendation_outcomes SET holding_days = days_held")
    op.drop_column("recommendation_outcomes", "days_held")
    op.drop_column("recommendation_outcomes", "regime_label")
    op.drop_column("recommendation_outcomes", "conviction_band")
    op.drop_column("recommendation_outcomes", "strategy_name")
    op.drop_column("recommendation_outcomes", "symbol")
