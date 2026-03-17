"""Add missing color translations (onyx, silverblue, whitesilver, marble, aurora, mint green).

Revision ID: x1_color_trans
Revises: 4776d4b65e85
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "x1_color_trans"
down_revision = "4776d4b65e85"
branch_labels = None
depends_on = None

TRANSLATIONS = [
    ("onyx", "Noir", 2),
    ("silverblue", "Bleu", 3),
    ("whitesilver", "Blanc", 1),
    ("marble", "Blanc", 1),
    ("aurora", "Violet", 7),
    ("mint green", "Vert", 5),
]


def upgrade():
    conn = op.get_bind()
    for source, target, target_id in TRANSLATIONS:
        conn.execute(
            sa.text(
                "INSERT INTO color_translations (color_source, color_target, color_target_id) "
                "VALUES (:src, :tgt, :tid) ON CONFLICT DO NOTHING"
            ),
            {"src": source, "tgt": target, "tid": target_id},
        )


def downgrade():
    conn = op.get_bind()
    for source, _, _ in TRANSLATIONS:
        conn.execute(
            sa.text("DELETE FROM color_translations WHERE color_source = :src"),
            {"src": source},
        )
