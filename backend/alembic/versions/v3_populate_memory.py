"""Populate memory_id from description pattern (e.g. 8/256Go -> Memory=256 Go).

Revision ID: v3_populate_memory
Revises: v2_populate_ram
Create Date: 2026-02-27
"""

import re

from alembic import op
import sqlalchemy as sa

revision = "v3_populate_memory"
down_revision = "v2_populate_ram"
branch_labels = None
depends_on = None

# Matches "X/YGo" (RAM/Storage) or standalone "YGo" (Storage only)
_RAM_STORAGE_RE = re.compile(r"\d+/(\d+)\s*Go", re.IGNORECASE)
_STORAGE_RE = re.compile(r"(\d+)\s*Go", re.IGNORECASE)


def upgrade():
    conn = op.get_bind()

    # Build memory_options lookup: "128" -> id, "256" -> id, etc.
    mem_rows = conn.execute(sa.text("SELECT id, memory FROM memory_options")).fetchall()
    mem_lookup = {}
    for row in mem_rows:
        num = row[1].replace(" Go", "").replace(" To", "").strip()
        mem_lookup[num] = row[0]

    # Find products with no memory_id and a storage pattern in description
    products = conn.execute(
        sa.text(
            "SELECT id, description FROM products "
            "WHERE memory_id IS NULL AND description ~* '[0-9]+\\s*Go'"
        )
    ).fetchall()

    count = 0
    for row in products:
        desc = row[1]
        # Try RAM/Storage pattern first, then standalone Storage
        m = _RAM_STORAGE_RE.search(desc)
        if not m:
            m = _STORAGE_RE.search(desc)
        if m:
            storage_val = m.group(1)
            if storage_val in mem_lookup:
                conn.execute(
                    sa.text("UPDATE products SET memory_id = :mem_id WHERE id = :id"),
                    {"mem_id": mem_lookup[storage_val], "id": row[0]},
                )
                count += 1

    if count:
        print(f"  -> Populated memory_id for {count} products")


def downgrade():
    pass
