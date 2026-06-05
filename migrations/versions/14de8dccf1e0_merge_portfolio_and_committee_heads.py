"""merge portfolio and committee heads

Revision ID: 14de8dccf1e0
Revises: 20260606_0022, 20260607_0021
Create Date: 2026-06-05 12:40:08.929912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14de8dccf1e0'
down_revision: Union[str, None] = ('20260606_0022', '20260607_0021')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
