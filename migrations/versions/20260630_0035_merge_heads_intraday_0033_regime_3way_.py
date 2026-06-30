"""merge heads: intraday(0033) + regime_3way(0034)

Revision ID: 20260630_0035
Revises: 20260625_0033, 20260628_0034
Create Date: 2026-06-30 18:06:31.948154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260630_0035'
down_revision: Union[str, None] = ('20260625_0033', '20260628_0034')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
