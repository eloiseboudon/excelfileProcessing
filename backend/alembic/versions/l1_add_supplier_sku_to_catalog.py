"""Add supplier_sku column to supplier_catalog.

Revision ID: l1_add_supplier_sku_to_catalog
Revises: k1_normalize_memory_ram
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa

revision = "l1_add_supplier_sku_to_catalog"
down_revision = "k1_normalize_memory_ram"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "supplier_catalog",
        sa.Column("supplier_sku", sa.String(120), nullable=True),
    )


def downgrade():
    op.drop_column("supplier_catalog", "supplier_sku")
