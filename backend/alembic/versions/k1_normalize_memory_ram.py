"""Normalize memory_options and ram_options values, merge duplicates.

Revision ID: k1_normalize_memory_ram
Revises: j1_add_activity_logs
Create Date: 2026-02-15
"""

import re
from collections import defaultdict

from alembic import op
import sqlalchemy as sa

revision = "k1_normalize_memory_ram"
down_revision = "j1_add_activity_logs"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Normalization logic (duplicated from utils/normalize.py to be self-contained)
# ---------------------------------------------------------------------------
_STORAGE_RE = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*(go|gb|to|tb)?\s*$",
    re.IGNORECASE,
)


def _normalize_storage(value):
    if not value or not value.strip():
        return None
    m = _STORAGE_RE.match(value.strip())
    if not m:
        return value.strip()
    number = m.group(1).replace(",", ".")
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    number = str(int(float(number))) if float(number) == int(float(number)) else number
    unit = (m.group(2) or "").lower()
    if unit in ("tb", "to"):
        return f"{number} To"
    return f"{number} Go"


def _normalize_ram(value):
    if not value or not value.strip():
        return None
    m = _STORAGE_RE.match(value.strip())
    if not m:
        return value.strip()
    number = m.group(1).replace(",", ".")
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    number = str(int(float(number))) if float(number) == int(float(number)) else number
    return f"{number} Go"


# ---------------------------------------------------------------------------
# FK tables that reference memory_options / ram_options
# ---------------------------------------------------------------------------
MEMORY_FK_TABLES = [
    ("products", "memory_id"),
    ("supplier_catalog", "memory_id"),
]

RAM_FK_TABLES = [
    ("products", '"RAM_id"'),       # column is uppercase in products
    ("supplier_catalog", "ram_id"),
]


def _merge_duplicates(conn, table_name, attr_col, normalize_fn, fk_tables):
    """Read all rows, group by normalized value, merge duplicates."""
    rows = conn.execute(
        sa.text(f"SELECT id, {attr_col} FROM {table_name} ORDER BY id")
    ).fetchall()

    # Group by normalized value
    groups = defaultdict(list)
    for row_id, raw_value in rows:
        normalized = normalize_fn(raw_value) if raw_value else raw_value
        if not normalized:
            normalized = raw_value
        groups[normalized].append((row_id, raw_value))

    for normalized_value, members in groups.items():
        if not normalized_value:
            continue

        # The survivor is the one with the lowest id
        survivor_id = members[0][0]

        # Reassign FKs from duplicates to survivor and delete them FIRST
        # (to avoid unique constraint violations when updating the survivor)
        duplicate_ids = [mid for mid, _ in members[1:]]
        if duplicate_ids:
            for fk_table, fk_col in fk_tables:
                conn.execute(
                    sa.text(
                        f"UPDATE {fk_table} SET {fk_col} = :survivor "
                        f"WHERE {fk_col} = ANY(:dups)"
                    ),
                    {"survivor": survivor_id, "dups": duplicate_ids},
                )
            # Delete duplicate rows
            conn.execute(
                sa.text(f"DELETE FROM {table_name} WHERE id = ANY(:dups)"),
                {"dups": duplicate_ids},
            )

        # Now update survivor's value to the normalized form
        conn.execute(
            sa.text(f"UPDATE {table_name} SET {attr_col} = :val WHERE id = :sid"),
            {"val": normalized_value, "sid": survivor_id},
        )

        # For tcp_value on memory_options, update it too
        if table_name == "memory_options":
            digits = re.sub(r"[^\d]", "", normalized_value)
            tcp_val = int(digits) if digits else 0
            conn.execute(
                sa.text("UPDATE memory_options SET tcp_value = :tcp WHERE id = :sid"),
                {"tcp": tcp_val, "sid": survivor_id},
            )


def upgrade():
    conn = op.get_bind()
    _merge_duplicates(conn, "memory_options", "memory", _normalize_storage, MEMORY_FK_TABLES)
    _merge_duplicates(conn, "ram_options", "ram", _normalize_ram, RAM_FK_TABLES)


def downgrade():
    # Data migration — not reversible (original heterogeneous values are lost)
    pass
