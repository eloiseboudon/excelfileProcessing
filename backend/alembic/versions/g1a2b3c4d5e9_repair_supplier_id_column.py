"""repair: ensure all columns exist on product_calculations

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
    """Repair product_calculations: add all potentially missing columns."""
    columns = [
        "ADD COLUMN IF NOT EXISTS supplier_id INTEGER REFERENCES suppliers(id)",
        "ADD COLUMN IF NOT EXISTS price DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ADD COLUMN IF NOT EXISTS tcp DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ADD COLUMN IF NOT EXISTS marge4_5 DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ADD COLUMN IF NOT EXISTS marge DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS marge_percent DOUBLE PRECISION",
        "ADD COLUMN IF NOT EXISTS prixht_tcp_marge4_5 DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ADD COLUMN IF NOT EXISTS prixht_marge4_5 DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ADD COLUMN IF NOT EXISTS prixht_max DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ADD COLUMN IF NOT EXISTS date TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()",
        "ADD COLUMN IF NOT EXISTS stock INTEGER",
    ]
    for col in columns:
        op.execute(f"ALTER TABLE product_calculations {col}")


def downgrade() -> None:
    """No-op: cannot safely remove columns that may have existed before."""
    pass
