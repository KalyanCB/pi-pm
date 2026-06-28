"""Add market_regime_3way to regime_history (3-way BULL/BEAR/SIDEWAYS regime).

Additive, nullable column — legacy 2-way trend_regime/regime_label are untouched.
Based on the committed head 0032 (independent of the uncommitted intraday 0033).

Revision ID: 20260628_0034
Revises: 20260622_0032
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260628_0034"
down_revision = "20260622_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "regime_history",
        sa.Column("market_regime_3way", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("regime_history", "market_regime_3way")
