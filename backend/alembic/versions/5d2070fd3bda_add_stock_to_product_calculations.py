"""Add stock column to product_calculations

Revision ID: 5d2070fd3bda
Revises: ce3dc80a2ad6
Create Date: 2025-10-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d2070fd3bda'
down_revision: Union[str, Sequence[str], None] = 'ce3dc80a2ad6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('product_calculations', sa.Column('stock', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('product_calculations', 'stock')
