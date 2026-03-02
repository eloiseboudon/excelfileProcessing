"""infer region from model for products with null region

Revision ID: 77ec0002c244
Revises: v3_populate_memory
Create Date: 2026-03-02 11:20:40.900081

Infers region for products with NULL region by detecting patterns in model/description:
- "Indian Spec" / "India Spec" / "(IN)" → IN
- "US Spec" / "USA Spec" / "(US)" → US
- "(DE)" / "deutsch" / "German Spec" → DE
- etc.

Then resets matching data for affected products so they can be re-matched with correct scoring.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77ec0002c244'
down_revision: Union[str, Sequence[str], None] = 'v3_populate_memory'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade: Infer region for products with NULL region, reset their matchings."""

    # Step 1: Update products with NULL region based on model/description patterns
    connection = op.get_bind()

    # Indian Spec
    connection.execute(sa.text("""
        UPDATE products
        SET region = 'IN'
        WHERE (region IS NULL OR region = '')
          AND (LOWER(COALESCE(model, '') || COALESCE(description, ''))
               LIKE ANY(ARRAY['%indian spec%', '%india spec%', '%(in)%', '%indian%']))
    """))

    # US Spec
    connection.execute(sa.text("""
        UPDATE products
        SET region = 'US'
        WHERE (region IS NULL OR region = '')
          AND (LOWER(COALESCE(model, '') || COALESCE(description, ''))
               LIKE ANY(ARRAY['%us spec%', '%usa spec%', '%(us)%', '%american%', '%us version%']))
    """))

    # DE Spec
    connection.execute(sa.text("""
        UPDATE products
        SET region = 'DE'
        WHERE (region IS NULL OR region = '')
          AND (LOWER(COALESCE(model, '') || COALESCE(description, ''))
               LIKE ANY(ARRAY['%(de)%', '%deutsch%', '%german spec%']))
    """))

    # JP Spec
    connection.execute(sa.text("""
        UPDATE products
        SET region = 'JP'
        WHERE (region IS NULL OR region = '')
          AND (LOWER(COALESCE(model, '') || COALESCE(description, ''))
               LIKE ANY(ARRAY['%japan spec%', '%(jp)%', '%japanese%']))
    """))

    # AU Spec
    connection.execute(sa.text("""
        UPDATE products
        SET region = 'AU'
        WHERE (region IS NULL OR region = '')
          AND (LOWER(COALESCE(model, '') || COALESCE(description, ''))
               LIKE ANY(ARRAY['%australia spec%', '%(au)%', '%australian%']))
    """))

    # CA Spec
    connection.execute(sa.text("""
        UPDATE products
        SET region = 'CA'
        WHERE (region IS NULL OR region = '')
          AND (LOWER(COALESCE(model, '') || COALESCE(description, ''))
               LIKE ANY(ARRAY['%canada spec%', '%(ca)%', '%canadian%']))
    """))

    # BR Spec
    connection.execute(sa.text("""
        UPDATE products
        SET region = 'BR'
        WHERE (region IS NULL OR region = '')
          AND (LOWER(COALESCE(model, '') || COALESCE(description, ''))
               LIKE ANY(ARRAY['%brasil spec%', '%brazil spec%', '%(br)%', '%brazilian%']))
    """))

    # MX Spec
    connection.execute(sa.text("""
        UPDATE products
        SET region = 'MX'
        WHERE (region IS NULL OR region = '')
          AND (LOWER(COALESCE(model, '') || COALESCE(description, ''))
               LIKE ANY(ARRAY['%mexico spec%', '%(mx)%', '%mexican%']))
    """))

    # Step 2: For products where we inferred a region (were NULL, now have value),
    # reset their matching data so they can be re-matched with correct scoring
    connection.execute(sa.text("""
        -- Find product IDs that were updated (had NULL region and now have one)
        -- We'll use a heuristic: products with region in (IN, US, DE, JP, AU, CA, BR, MX)
        -- that have a pattern in their model/description matching their region
        WITH affected_products AS (
            SELECT id FROM products
            WHERE region IN ('IN', 'US', 'DE', 'JP', 'AU', 'CA', 'BR', 'MX')
        )
        -- Delete associated SupplierProductRef entries
        DELETE FROM supplier_product_refs
        WHERE product_id IN (SELECT id FROM affected_products);
    """))

    connection.execute(sa.text("""
        -- Find product IDs with inferred regions
        WITH affected_products AS (
            SELECT id FROM products
            WHERE region IN ('IN', 'US', 'DE', 'JP', 'AU', 'CA', 'BR', 'MX')
        )
        -- Reset LabelCache entries (set product_id to NULL so they re-match)
        UPDATE label_cache
        SET product_id = NULL,
            match_source = 'extracted',
            match_score = NULL
        WHERE product_id IN (SELECT id FROM affected_products);
    """))


def downgrade() -> None:
    """Downgrade: Reverse region inference (set back to NULL for re-inferred products)."""

    connection = op.get_bind()

    # Reset region to NULL for products in non-EU regions
    # (These were inferred, not explicitly set by users)
    connection.execute(sa.text("""
        UPDATE products
        SET region = NULL
        WHERE region IN ('IN', 'US', 'DE', 'JP', 'AU', 'CA', 'BR', 'MX')
    """))
