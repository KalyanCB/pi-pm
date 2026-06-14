"""ADR-034: deterministic trade levels on recommendations.

Adds to recommendation_results (all nullable, backward compatible):
  reference_close  — close used as the levels basis
  atr_pct          — ATR as % of close (volatility, provenance)
  entry_low        — entry range lower bound
  entry_high       — entry range upper bound
  stop_advisory    — advisory stop price (reuses advisory_stop_pct)
  stop_critical    — critical stop price (reuses critical_stop_pct)
  levels_basis     — "actionable" (BUY) | "indicative" (future: WATCH)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0028"
down_revision: str | None = "20260611_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    ("reference_close", sa.Numeric(18, 6)),
    ("atr_pct", sa.Numeric(10, 4)),
    ("entry_low", sa.Numeric(18, 6)),
    ("entry_high", sa.Numeric(18, 6)),
    ("stop_advisory", sa.Numeric(18, 6)),
    ("stop_critical", sa.Numeric(18, 6)),
    ("levels_basis", sa.String(16)),
)


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column(
            "recommendation_results",
            sa.Column(name, type_, nullable=True),
        )


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("recommendation_results", name)
