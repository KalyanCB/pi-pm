"""ADR-039: Fundamental Intelligence Layer — schema.

Creates:
  company_news_events    extracted per-stock catalysts (AI extraction output)
  fil_watch_list         active company catalysts with an expiry window
  fil_conviction_boosts  audit of boosts (Phase 2; populated once engine wired)
  sector_classifications stock → sector mapping (Phase 3)
  sector_news_events     extracted sector-level catalysts (Phase 3)

These tables are standalone — no recommendation-engine or daily-batch wiring yet.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260622_0032"
down_revision: str | Sequence[str] | None = "20260618_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_news_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "stock_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("sentiment", sa.String(20), nullable=False),
        sa.Column("magnitude", sa.String(10), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("catalyst_duration_days", sa.Integer, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("raw_excerpt", sa.Text, nullable=True),
        sa.Column("flags", JSONB, nullable=True),
        sa.Column("is_confirmed", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_company_news_events_stock_date", "company_news_events", ["stock_id", "event_date"]
    )
    op.create_index(
        "ix_company_news_events_date_category", "company_news_events", ["event_date", "category"]
    )
    op.create_unique_constraint(
        "uq_company_news_events_source_extid", "company_news_events", ["source", "external_id"]
    )

    op.create_table(
        "fil_watch_list",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "stock_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "news_event_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("company_news_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("added_date", sa.Date, nullable=False),
        sa.Column("expires_date", sa.Date, nullable=False),
        sa.Column("catalyst_type", sa.String(50), nullable=False),
        sa.Column("sentiment", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivation_reason", sa.String(50), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_fil_watch_list_active", "fil_watch_list", ["stock_id", "is_active", "expires_date"]
    )
    op.create_index("ix_fil_watch_list_added", "fil_watch_list", ["added_date"])

    op.create_table(
        "fil_conviction_boosts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recommendation_result_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("recommendation_results.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "fil_watch_list_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("fil_watch_list.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("original_conviction_band", sa.String(20), nullable=True),
        sa.Column("boosted_conviction_band", sa.String(20), nullable=True),
        sa.Column("boost_applied", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "sector_classifications",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "stock_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sector", sa.String(60), nullable=False),
        sa.Column("sub_sector", sa.String(60), nullable=True),
        sa.Column("index_membership", JSONB, nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_unique_constraint(
        "uq_sector_classifications_stock_sector", "sector_classifications", ["stock_id", "sector"]
    )
    op.create_index("ix_sector_classifications_sector", "sector_classifications", ["sector"])

    op.create_table(
        "sector_news_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("sector", sa.String(60), nullable=False),
        sa.Column("sub_sector", sa.String(60), nullable=True),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("sentiment", sa.String(20), nullable=False),
        sa.Column("magnitude", sa.String(10), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("catalyst_duration_days", sa.Integer, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("raw_excerpt", sa.Text, nullable=True),
        sa.Column("affected_stocks_count", sa.Integer, nullable=True),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_sector_news_events_sector_date", "sector_news_events", ["sector", "event_date"]
    )
    op.create_index(
        "ix_sector_news_events_date_sentiment", "sector_news_events", ["event_date", "sentiment"]
    )
    op.create_unique_constraint(
        "uq_sector_news_events_source_extid", "sector_news_events", ["source", "external_id"]
    )


def downgrade() -> None:
    op.drop_table("sector_news_events")
    op.drop_index("ix_sector_classifications_sector", table_name="sector_classifications")
    op.drop_table("sector_classifications")
    op.drop_table("fil_conviction_boosts")
    op.drop_index("ix_fil_watch_list_added", table_name="fil_watch_list")
    op.drop_index("ix_fil_watch_list_active", table_name="fil_watch_list")
    op.drop_table("fil_watch_list")
    op.drop_index("ix_company_news_events_date_category", table_name="company_news_events")
    op.drop_index("ix_company_news_events_stock_date", table_name="company_news_events")
    op.drop_table("company_news_events")
