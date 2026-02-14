"""repair: add remaining missing columns on product_calculations

Revision ID: h1a2b3c4d5f0
Revises: g1a2b3c4d5e9
Create Date: 2026-02-14 15:55:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "h1a2b3c4d5f0"
down_revision: Union[str, Sequence[str], None] = "g1a2b3c4d5e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add all missing columns to product_calculations (idempotent)."""
    columns = [
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
