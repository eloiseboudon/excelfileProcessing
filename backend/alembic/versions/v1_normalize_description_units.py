"""Normalize storage units in product descriptions (GB -> Go, TB -> To).

Revision ID: v1_normalize_description_units
Revises: u1_matching_run_coverage
Create Date: 2026-02-27
"""

import re

from alembic import op
import sqlalchemy as sa

revision = "v1_normalize_description_units"
down_revision = "u1_matching_run_coverage"
branch_labels = None
depends_on = None

_UNIT_GB_RE = re.compile(r"(\d+)\s*(?:GB|Gb|gb)\b")
_UNIT_TB_RE = re.compile(r"(\d+)\s*(?:TB|Tb|tb)\b")


def _normalize(text):
    text = _UNIT_GB_RE.sub(r"\1Go", text)
    text = _UNIT_TB_RE.sub(r"\1To", text)
    return text


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, description FROM products WHERE description ~* '[0-9]+\\s*(GB|TB)'")
    ).fetchall()

    if not rows:
        return

    for row in rows:
        new_desc = _normalize(row[1])
        if new_desc != row[1]:
            conn.execute(
                sa.text("UPDATE products SET description = :desc WHERE id = :id"),
                {"desc": new_desc, "id": row[0]},
            )


def downgrade():
    pass
