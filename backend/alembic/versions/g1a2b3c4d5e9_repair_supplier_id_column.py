"""repair: ensure supplier_id column exists on product_calculations

Revision ID: g1a2b3c4d5e9
Revises: f2a2b3c4d5e8
Create Date: 2026-02-14 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "g1a2b3c4d5e9"
down_revision: Union[str, Sequence[str], None] = "f2a2b3c4d5e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add supplier_id to product_calculations if missing (repair)."""
    op.execute("""
        ALTER TABLE product_calculations
        ADD COLUMN IF NOT EXISTS supplier_id INTEGER REFERENCES suppliers(id)
    """)


def downgrade() -> None:
    """Remove supplier_id from product_calculations."""
    op.drop_column("product_calculations", "supplier_id")
