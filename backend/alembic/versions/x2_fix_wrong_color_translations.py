"""Fix wrong color translations (grey/gray→Gris, coral→Rose).

Revision ID: x2_fix_colors
Revises: x1_color_trans
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = "x2_fix_colors"
down_revision = "x1_color_trans"
branch_labels = None
depends_on = None

FIXES = [
    # (color_source, correct_target, correct_target_id)
    ("grey", "Gris", 10),
    ("gray", "Gris", 10),
    ("dark gray", "Gris", 10),
    ("dark grey", "Gris", 10),
    ("coral", "Rose", 6),
]


def upgrade():
    conn = op.get_bind()
    for source, target, target_id in FIXES:
        conn.execute(
            sa.text(
                "UPDATE color_translations "
                "SET color_target = :tgt, color_target_id = :tid "
                "WHERE color_source = :src"
            ),
            {"src": source, "tgt": target, "tid": target_id},
        )


def downgrade():
    # Revert to old (wrong) values
    conn = op.get_bind()
    old_values = [
        ("grey", "Noir", 2),
        ("gray", "Noir", 2),
        ("dark gray", "Noir", 2),
        ("dark grey", "Noir", 2),
        ("coral", "Vert", 5),
    ]
    for source, target, target_id in old_values:
        conn.execute(
            sa.text(
                "UPDATE color_translations "
                "SET color_target = :tgt, color_target_id = :tid "
                "WHERE color_source = :src"
            ),
            {"src": source, "tgt": target, "tid": target_id},
        )
