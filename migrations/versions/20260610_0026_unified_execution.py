"""Track K: unified execution platform (paper + live adapter layer)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260610_0026"
down_revision: str | None = "20260610_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portfolio_configs",
        sa.Column("execution_mode", sa.String(16), nullable=False, server_default="PAPER"),
    )

    op.create_table(
        "execution_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("strategy_name", sa.String(64)),
        sa.Column(
            "recommendation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recommendation_results.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "approval_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recommendation_approvals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "executed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("execution_mode", sa.String(16), nullable=False, server_default="PAPER"),
        sa.Column("status", sa.String(32), nullable=False, server_default="EXECUTION_PENDING"),
        sa.Column("client_order_id", sa.String(64), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(128), unique=True),
        sa.Column("broker_name", sa.String(32)),
        sa.Column("broker_order_id", sa.String(64)),
        sa.Column("filled_quantity", sa.Numeric(18, 8)),
        sa.Column("avg_fill_price", sa.Numeric(18, 4)),
        sa.Column("fees", sa.Numeric(12, 2)),
        sa.Column("slippage", sa.Numeric(10, 4)),
        sa.Column(
            "paper_trade_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("paper_trades.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("raw_response", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("rejection_reason", sa.Text),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_execution_orders_portfolio_id", "execution_orders", ["portfolio_id"])
    op.create_index("ix_execution_orders_recommendation_id", "execution_orders", ["recommendation_id"])
    op.create_index("ix_execution_orders_approval_id", "execution_orders", ["approval_id"])
    op.create_index("ix_execution_orders_broker_order_id", "execution_orders", ["broker_order_id"])
    op.create_index("ix_execution_orders_status", "execution_orders", ["status"])
    op.create_index(
        "ix_execution_orders_portfolio_status", "execution_orders", ["portfolio_id", "status"]
    )

    op.create_table(
        "execution_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "execution_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("execution_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False, server_default="STATE_TRANSITION"),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_execution_events_execution_order_id", "execution_events", ["execution_order_id"])
    op.create_index(
        "ix_execution_events_order_created", "execution_events", ["execution_order_id", "created_at"]
    )

    op.create_table(
        "execution_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("execution_mode", sa.String(16), nullable=False, server_default="PAPER"),
        sa.Column("broker_name", sa.String(32)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("settings", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("notes", sa.String(256)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_execution_configs_portfolio_id", "execution_configs", ["portfolio_id"])

    op.create_table(
        "execution_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "execution_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("execution_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("execution_mode", sa.String(16), nullable=False),
        sa.Column("broker_name", sa.String(32)),
        sa.Column("request_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("response_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("correlation_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_execution_audit_execution_order_id", "execution_audit", ["execution_order_id"])
    op.create_index(
        "ix_execution_audit_order_created", "execution_audit", ["execution_order_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("execution_audit")
    op.drop_table("execution_configs")
    op.drop_table("execution_events")
    op.drop_table("execution_orders")
    op.drop_column("portfolio_configs", "execution_mode")
