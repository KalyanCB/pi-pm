"""Sprint 2: market intelligence schema changes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260530_0002"
down_revision: str | None = "20260530_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "stocks",
        "symbol",
        existing_type=sa.String(length=16),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.add_column(
        "stocks",
        sa.Column("data_status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
    )
    op.create_index("ix_stocks_data_status", "stocks", ["data_status"], unique=False)

    op.add_column("market_data", sa.Column("dividend", sa.Numeric(precision=18, scale=6), nullable=True))
    op.add_column(
        "market_data", sa.Column("split_factor", sa.Numeric(precision=18, scale=8), nullable=True)
    )

    op.create_table(
        "stock_universes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_stock_universes_code", "stock_universes", ["code"], unique=True)

    op.create_table(
        "universe_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("universe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["universe_id"], ["stock_universes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("universe_id", "stock_id", name="uq_universe_membership_universe_stock"),
    )
    op.create_index(
        "ix_universe_memberships_universe", "universe_memberships", ["universe_id"], unique=False
    )

    op.create_table(
        "market_data_ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("requested_period", sa.String(length=8), nullable=False),
        sa.Column("rows_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_data_ingestion_runs_symbol_started",
        "market_data_ingestion_runs",
        ["symbol", "started_at"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO stock_universes (id, code, name, description, is_active)
            VALUES
                ('00000000-0000-4000-8000-000000000001', 'NIFTY_50', 'NIFTY 50',
                 'NSE NIFTY 50 index constituents', true),
                ('00000000-0000-4000-8000-000000000002', 'NIFTY_100', 'NIFTY 100',
                 'NSE NIFTY 100 index constituents', true),
                ('00000000-0000-4000-8000-000000000003', 'NIFTY_500', 'NIFTY 500',
                 'NSE NIFTY 500 index constituents', true),
                ('00000000-0000-4000-8000-000000000004', 'PI_PM_CORE', 'Pi-PM Core Universe',
                 'Core tracked universe for Pi-PM', true)
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_market_data_ingestion_runs_symbol_started", table_name="market_data_ingestion_runs")
    op.drop_table("market_data_ingestion_runs")
    op.drop_index("ix_universe_memberships_universe", table_name="universe_memberships")
    op.drop_table("universe_memberships")
    op.drop_index("ix_stock_universes_code", table_name="stock_universes")
    op.drop_table("stock_universes")
    op.drop_column("market_data", "split_factor")
    op.drop_column("market_data", "dividend")
    op.drop_index("ix_stocks_data_status", table_name="stocks")
    op.drop_column("stocks", "data_status")
    op.alter_column(
        "stocks",
        "symbol",
        existing_type=sa.String(length=32),
        type_=sa.String(length=16),
        existing_nullable=False,
    )
