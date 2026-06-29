"""Create market_data_intraday for realistic next-session VWAP fills + impact model.

Revision ID: 20260625_0033
Revises: 20260622_0032
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260625_0033"
down_revision = "20260622_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_intraday",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=True),
        sa.Column("high", sa.Numeric(18, 6), nullable=True),
        sa.Column("low", sa.Numeric(18, 6), nullable=True),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "stock_id", "ts", "interval", "source",
            name="uq_md_intraday_stock_ts_interval_source",
        ),
    )
    op.create_index(
        "ix_md_intraday_stock_ts", "market_data_intraday", ["stock_id", "ts"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_md_intraday_stock_ts", table_name="market_data_intraday")
    op.drop_table("market_data_intraday")
