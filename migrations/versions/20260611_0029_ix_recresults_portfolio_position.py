"""Index recommendation_results.portfolio_position_id (FK SET NULL support).

Without this index, every DELETE on portfolio_positions forces a sequential
scan of recommendation_results (1M+ rows) per deleted row to enforce the
ON DELETE SET NULL constraint — making portfolio wipes/closes glacial.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260611_0029"
down_revision: str | None = "20260611_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "ix_recommendation_results_portfolio_position_id"


def upgrade() -> None:
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {_INDEX} "
        "ON recommendation_results (portfolio_position_id)"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
