"""Populate RAM_id from description pattern (e.g. 8/256Go -> RAM=8 Go).

Revision ID: v2_populate_ram
Revises: v1_norm_desc_units
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "v2_populate_ram"
down_revision = "v1_norm_desc_units"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Build ram_options lookup: "4" -> id, "8" -> id, etc.
    ram_rows = conn.execute(sa.text("SELECT id, ram FROM ram_options")).fetchall()
    ram_lookup = {}
    for row in ram_rows:
        # ram format is "X Go", extract the number
        num = row[1].replace(" Go", "").strip()
        ram_lookup[num] = row[0]

    # Find products with RAM/Storage pattern and no RAM_id
    products = conn.execute(
        sa.text(
            "SELECT id, substring(description FROM '(\\d+)/\\d+\\s*Go') AS ram_val "
            "FROM products "
            "WHERE \"RAM_id\" IS NULL AND description ~ '\\d+/\\d+\\s*Go'"
        )
    ).fetchall()

    count = 0
    for row in products:
        ram_val = row[1]
        if ram_val and ram_val in ram_lookup:
            conn.execute(
                sa.text('UPDATE products SET "RAM_id" = :ram_id WHERE id = :id'),
                {"ram_id": ram_lookup[ram_val], "id": row[0]},
            )
            count += 1

    if count:
        print(f"  -> Populated RAM_id for {count} products")


def downgrade():
    op.execute('UPDATE products SET "RAM_id" = NULL')
