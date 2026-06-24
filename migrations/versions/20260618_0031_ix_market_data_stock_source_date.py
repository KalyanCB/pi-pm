"""Add composite index on market_data(stock_id, source, date) for ranking query performance.

Revision ID: 20260618_0031
Revises: 20260617_0030
"""
from __future__ import annotations

from alembic import op


revision = "20260618_0031"
down_revision = "20260617_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_market_data_stock_source_date",
        "market_data",
        ["stock_id", "source", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_market_data_stock_source_date", table_name="market_data")
