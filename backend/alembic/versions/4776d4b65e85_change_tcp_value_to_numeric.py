"""change-tcp-value-to-numeric

Revision ID: 4776d4b65e85
Revises: w1_fix_color_translations
Create Date: 2026-03-16 11:56:42.682707

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4776d4b65e85'
down_revision: Union[str, Sequence[str], None] = 'w1_fix_color_translations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('memory_options', 'tcp_value',
               existing_type=sa.INTEGER(),
               type_=sa.Numeric(precision=5, scale=2),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('memory_options', 'tcp_value',
               existing_type=sa.Numeric(precision=5, scale=2),
               type_=sa.INTEGER(),
               existing_nullable=False)
