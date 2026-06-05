"""Seed NIFTY_1000 broad-market universe."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260608_0016"
down_revision: str | None = "20260607_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO stock_universes (id, code, name, description, is_active)
            VALUES
                ('00000000-0000-4000-8000-000000000005', 'NIFTY_1000', 'NIFTY 1000',
                 'Broad NSE universe: NIFTY 500 plus the most-liquid additional '
                 'NSE-listed equities, ~1000 constituents', true)
            ON CONFLICT (code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM stock_universes WHERE code = 'NIFTY_1000'"))
