"""Add supplier_sku column to parsed_items

Revision ID: 4f0e2d1f5e7b
Revises: 3b8f3c9e9c41
Create Date: 2025-10-14 09:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4f0e2d1f5e7b'
down_revision: Union[str, Sequence[str], None] = '3b8f3c9e9c41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'parsed_items',
        sa.Column('supplier_sku', sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('parsed_items', 'supplier_sku')
