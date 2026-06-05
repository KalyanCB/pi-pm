"""Copilot: add copilot_query_logs audit table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260609_0024"
down_revision: str | None = "20260609_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "copilot_query_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("intent", sa.String(32), nullable=False),
        sa.Column("entities", postgresql.JSONB, nullable=True),
        sa.Column("retrieved_ids", postgresql.JSONB, nullable=True),
        sa.Column("answer", sa.Text, nullable=True),
        sa.Column("answer_hash", sa.String(64), nullable=True),
        sa.Column("citations", postgresql.JSONB, nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("prompt_tokens", sa.Integer, nullable=True),
        sa.Column("completion_tokens", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("refused", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_copilot_query_logs_intent", "copilot_query_logs", ["intent"])
    op.create_index("ix_copilot_query_logs_created_at", "copilot_query_logs", ["created_at"])
    op.create_index("ix_copilot_query_logs_session", "copilot_query_logs", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_copilot_query_logs_session", "copilot_query_logs")
    op.drop_index("ix_copilot_query_logs_created_at", "copilot_query_logs")
    op.drop_index("ix_copilot_query_logs_intent", "copilot_query_logs")
    op.drop_table("copilot_query_logs")
