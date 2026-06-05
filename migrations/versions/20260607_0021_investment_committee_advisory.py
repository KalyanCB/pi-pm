"""M3.1 Investment Committee Evolution: add advisory_action, high_concern,
high_concern_reason to committee_reviews; add cro_advisory_action,
investment_committee_summary to cro_reviews. Additive only."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260607_0021"
down_revision: str | None = "20260606_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # committee_reviews — investor-facing advisory fields
    op.add_column(
        "committee_reviews",
        sa.Column("advisory_action", sa.String(32), nullable=True),
    )
    op.add_column(
        "committee_reviews",
        sa.Column("high_concern", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "committee_reviews",
        sa.Column("high_concern_reason", sa.Text, nullable=True),
    )

    # cro_reviews — aggregate advisory + investor-facing summary
    op.add_column(
        "cro_reviews",
        sa.Column("cro_advisory_action", sa.String(32), nullable=True),
    )
    op.add_column(
        "cro_reviews",
        sa.Column("investment_committee_summary", sa.Text, nullable=True),
    )

    # Index for analytics queries
    op.create_index(
        "ix_committee_reviews_advisory_action",
        "committee_reviews",
        ["advisory_action"],
    )
    op.create_index(
        "ix_committee_reviews_high_concern",
        "committee_reviews",
        ["high_concern"],
    )
    op.create_index(
        "ix_cro_reviews_advisory_action",
        "cro_reviews",
        ["cro_advisory_action"],
    )


def downgrade() -> None:
    op.drop_index("ix_cro_reviews_advisory_action", "cro_reviews")
    op.drop_index("ix_committee_reviews_high_concern", "committee_reviews")
    op.drop_index("ix_committee_reviews_advisory_action", "committee_reviews")
    op.drop_column("cro_reviews", "investment_committee_summary")
    op.drop_column("cro_reviews", "cro_advisory_action")
    op.drop_column("committee_reviews", "high_concern_reason")
    op.drop_column("committee_reviews", "high_concern")
    op.drop_column("committee_reviews", "advisory_action")
