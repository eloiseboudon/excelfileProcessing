"""Add margin percent to product_calculations

Revision ID: b5c2d6c4b317
Revises: 5d2070fd3bda
Create Date: 2024-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5c2d6c4b317'
down_revision: Union[str, Sequence[str], None] = '5d2070fd3bda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'product_calculations',
        sa.Column('marge_percent', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('product_calculations', 'marge_percent')
