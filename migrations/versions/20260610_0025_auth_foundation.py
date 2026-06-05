"""Track E: authentication, RBAC, and multi-tenant portfolio ownership."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260610_0025"
down_revision: str | None = "20260609_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_PORTFOLIO_ID = "00000000-0000-4000-8000-000000000010"
DEFAULT_USER_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("description", sa.String(256)),
    )

    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.String(256)),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_portfolios_slug", "portfolios", ["slug"])

    op.create_table(
        "user_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("locale", sa.String(16), nullable=False, server_default="en-IN"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "user_portfolio_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="owner"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "portfolio_id", name="uq_user_portfolio_membership"),
    )
    op.create_index("ix_user_portfolio_memberships_user", "user_portfolio_memberships", ["user_id"])
    op.create_index("ix_user_portfolio_memberships_portfolio", "user_portfolio_memberships", ["portfolio_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("refresh_tokens.id", ondelete="SET NULL")),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # Seed default portfolio for legacy single-user data
    op.execute(
        sa.text(
            f"""
            INSERT INTO portfolios (id, name, slug, is_default, created_at, updated_at)
            VALUES ('{DEFAULT_PORTFOLIO_ID}', 'Default Portfolio', 'default', true, now(), now())
            ON CONFLICT DO NOTHING
            """
        )
    )

    op.add_column(
        "portfolio_configs",
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True),
    )
    op.create_index("ix_portfolio_configs_portfolio_id", "portfolio_configs", ["portfolio_id"])
    op.execute(
        sa.text(f"UPDATE portfolio_configs SET portfolio_id = '{DEFAULT_PORTFOLIO_ID}' WHERE portfolio_id IS NULL")
    )

    op.add_column(
        "portfolio_positions",
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True),
    )
    op.create_index("ix_portfolio_positions_portfolio_id", "portfolio_positions", ["portfolio_id"])
    op.execute(
        sa.text(f"UPDATE portfolio_positions SET portfolio_id = '{DEFAULT_PORTFOLIO_ID}' WHERE portfolio_id IS NULL")
    )

    op.add_column(
        "copilot_query_logs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_copilot_query_logs_user_id", "copilot_query_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_copilot_query_logs_user_id", table_name="copilot_query_logs")
    op.drop_column("copilot_query_logs", "user_id")

    op.drop_index("ix_portfolio_positions_portfolio_id", table_name="portfolio_positions")
    op.drop_column("portfolio_positions", "portfolio_id")

    op.drop_index("ix_portfolio_configs_portfolio_id", table_name="portfolio_configs")
    op.drop_column("portfolio_configs", "portfolio_id")

    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_user_portfolio_memberships_portfolio", table_name="user_portfolio_memberships")
    op.drop_index("ix_user_portfolio_memberships_user", table_name="user_portfolio_memberships")
    op.drop_table("user_portfolio_memberships")
    op.drop_table("user_preferences")
    op.drop_index("ix_portfolios_slug", table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
