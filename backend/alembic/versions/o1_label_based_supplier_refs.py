"""Switch SupplierProductRef to label-based unique key.

Adds normalized_label column to supplier_product_refs, replaces the
(supplier_id, ean, part_number, supplier_sku) unique constraint with
(supplier_id, normalized_label), and drops the EAN-based unique constraint
on supplier_catalog that prevented two entries with the same EAN.

Revision ID: o1_label_refs
Revises: n1_match_reasoning
Create Date: 2026-02-24
"""

from alembic import op

revision = "o1_label_refs"
down_revision = "n1_match_reasoning"
branch_labels = None
depends_on = None


def upgrade():
    # --- supplier_product_refs ---
    op.execute(
        "ALTER TABLE supplier_product_refs "
        "ADD COLUMN IF NOT EXISTS normalized_label VARCHAR(300)"
    )
    # Populate existing rows so the UNIQUE constraint can be applied
    op.execute(
        """
        UPDATE supplier_product_refs
        SET normalized_label = COALESCE(supplier_sku, ean, part_number, CAST(id AS TEXT))
        WHERE normalized_label IS NULL
        """
    )
    op.execute(
        "ALTER TABLE supplier_product_refs "
        "DROP CONSTRAINT IF EXISTS uix_supplier_ref"
    )
    op.execute(
        "ALTER TABLE supplier_product_refs "
        "ADD CONSTRAINT uix_supplier_ref_label "
        "UNIQUE (supplier_id, normalized_label)"
    )

    # --- supplier_catalog ---
    op.execute(
        "ALTER TABLE supplier_catalog "
        "DROP CONSTRAINT IF EXISTS uix_supplier_catalog_ean_supplier"
    )


def downgrade():
    op.execute(
        "ALTER TABLE supplier_product_refs "
        "DROP CONSTRAINT IF EXISTS uix_supplier_ref_label"
    )
    op.execute(
        "ALTER TABLE supplier_product_refs "
        "DROP COLUMN IF EXISTS normalized_label"
    )
    op.execute(
        "ALTER TABLE supplier_catalog "
        "ADD CONSTRAINT uix_supplier_catalog_ean_supplier "
        "UNIQUE (ean, supplier_id)"
    )
