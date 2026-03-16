"""Fix color translations: remove contradictory duplicates, add Icy Blue

Revision ID: w1_fix_color_translations
Revises: 97e5f0069448
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa

revision: str = 'w1_fix_color_translations'
down_revision: str = '97e5f0069448'
branch_labels = None
depends_on = None

# IDs of wrong/duplicate translations to remove
# (from the old seed that conflicts with Odoo data)
REMOVE_IDS = [
    8,   # midnight -> Bleu (should be Noir)
    35,  # graphite -> Noir (should be Gris)
    57,  # space gray -> Noir (should be Gris)
    58,  # space grey -> Noir (should be Gris)
    24,  # black titanium -> Noir (should be Titane Noir)
    33,  # desert titanium -> Blanc (should be Titane Desert)
    45,  # natural titanium -> Blanc (should be Titane Naturel)
    66,  # white titanium -> Blanc (should be Titane Blanc)
    41,  # lavender -> Violet (should be Lavande)
    5,   # starlight -> Blanc (duplicate of id=69)
]

# New translation to add
ADD_TRANSLATIONS = [
    ('Icy Blue', 'Bleu'),
]


def upgrade():
    conn = op.get_bind()

    # Remove contradictory/duplicate translations
    for tid in REMOVE_IDS:
        conn.execute(
            sa.text("DELETE FROM color_translations WHERE id = :id"),
            {"id": tid},
        )

    # Add new translations
    for source, target in ADD_TRANSLATIONS:
        # Get target color id
        row = conn.execute(
            sa.text("SELECT id FROM colors WHERE color = :color"),
            {"color": target},
        ).fetchone()
        if row:
            conn.execute(
                sa.text(
                    "INSERT INTO color_translations (color_source, color_target, color_target_id) "
                    "VALUES (:source, :target, :target_id)"
                ),
                {"source": source, "target": target, "target_id": row[0]},
            )


def downgrade():
    conn = op.get_bind()

    # Remove added translations
    for source, _ in ADD_TRANSLATIONS:
        conn.execute(
            sa.text("DELETE FROM color_translations WHERE color_source = :source"),
            {"source": source},
        )

    # Re-insert removed translations (for rollback)
    reinserts = [
        (8, 'midnight', 'Bleu'),
        (35, 'graphite', 'Noir'),
        (57, 'space gray', 'Noir'),
        (58, 'space grey', 'Noir'),
        (24, 'black titanium', 'Noir'),
        (33, 'desert titanium', 'Blanc'),
        (45, 'natural titanium', 'Blanc'),
        (66, 'white titanium', 'Blanc'),
        (41, 'lavender', 'Violet'),
        (5, 'starlight', 'Blanc'),
    ]
    for tid, source, target in reinserts:
        row = conn.execute(
            sa.text("SELECT id FROM colors WHERE color = :color"),
            {"color": target},
        ).fetchone()
        if row:
            conn.execute(
                sa.text(
                    "INSERT INTO color_translations (id, color_source, color_target, color_target_id) "
                    "VALUES (:id, :source, :target, :target_id)"
                ),
                {"id": tid, "source": source, "target": target, "target_id": row[0]},
            )
