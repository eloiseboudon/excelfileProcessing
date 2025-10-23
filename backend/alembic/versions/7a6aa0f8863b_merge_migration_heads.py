"""Merge migration heads

Revision ID: 7a6aa0f8863b
Revises: 7f7b6e9d8af8, b5c2d6c4b317
Create Date: 2025-10-23 17:18:17.251334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a6aa0f8863b'
down_revision: Union[str, Sequence[str], None] = ('7f7b6e9d8af8', 'b5c2d6c4b317')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
