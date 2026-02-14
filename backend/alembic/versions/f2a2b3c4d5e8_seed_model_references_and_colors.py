"""seed_model_references_and_colors

Revision ID: f2a2b3c4d5e8
Revises: f1a2b3c4d5e7
Create Date: 2026-02-14 10:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a2b3c4d5e8"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MODEL_REFERENCES = [
    ("SM-S938B", "Galaxy S25 Ultra"),
    ("S938B", "Galaxy S25 Ultra"),
    ("SM-S936B", "Galaxy S25+"),
    ("S936B", "Galaxy S25+"),
    ("SM-S931B", "Galaxy S25"),
    ("S931B", "Galaxy S25"),
    ("SM-S928B", "Galaxy S24 Ultra"),
    ("S928B", "Galaxy S24 Ultra"),
    ("SM-S926B", "Galaxy S24+"),
    ("S926B", "Galaxy S24+"),
    ("SM-S921B", "Galaxy S24"),
    ("S921B", "Galaxy S24"),
    ("SM-A566B", "Galaxy A56"),
    ("A566B", "Galaxy A56"),
    ("SM-A556B", "Galaxy A55"),
    ("A556B", "Galaxy A55"),
    ("SM-A546B", "Galaxy A54"),
    ("A546B", "Galaxy A54"),
    ("SM-A356B", "Galaxy A35"),
    ("A356B", "Galaxy A35"),
    ("SM-A166B", "Galaxy A16"),
    ("A166B", "Galaxy A16"),
    ("SM-X230N", "Galaxy Tab A11+"),
    ("X230N", "Galaxy Tab A11+"),
]

_COLOR_TRANSLATIONS = [
    ("Midnight", "Noir"),
    ("Starlight", "Blanc"),
    ("Space Black", "Noir"),
    ("Space Grey", "Gris"),
    ("Space Gray", "Gris"),
    ("Graphite", "Gris"),
    ("Cloud White", "Blanc"),
    ("Mist Blue", "Bleu"),
    ("Sky Blue", "Bleu"),
    ("Deep Blue", "Bleu"),
    ("Cosmic Orange", "Orange"),
    ("Desert Titanium", "Titane Desert"),
    ("Natural Titanium", "Titane Naturel"),
    ("Black Titanium", "Titane Noir"),
    ("White Titanium", "Titane Blanc"),
    ("Deep Purple", "Violet"),
    ("Jetblack", "Noir"),
    ("Jet Black", "Noir"),
    ("Light Gold", "Or"),
    ("Lavender", "Lavande"),
    ("Sage", "Vert"),
    ("Obsidian", "Noir"),
    ("Moonstone", "Bleu"),
    ("Charcoal", "Gris"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # Find Samsung brand_id
    brands = sa.table("brands", sa.column("id"), sa.column("brand"))
    result = conn.execute(
        sa.select(brands.c.id).where(brands.c.brand == "Samsung")
    ).first()
    samsung_id = result[0] if result else None

    # Insert model references
    model_refs = sa.table(
        "model_references",
        sa.column("manufacturer_code"),
        sa.column("commercial_name"),
        sa.column("brand_id"),
    )
    for code, name in _MODEL_REFERENCES:
        exists = conn.execute(
            sa.select(sa.func.count()).select_from(model_refs).where(
                model_refs.c.manufacturer_code == code
            )
        ).scalar()
        if not exists:
            conn.execute(
                model_refs.insert().values(
                    manufacturer_code=code,
                    commercial_name=name,
                    brand_id=samsung_id,
                )
            )

    # Ensure target colors exist
    colors = sa.table("colors", sa.column("id"), sa.column("color"))
    target_colors = sorted({target for _, target in _COLOR_TRANSLATIONS})
    for color_name in target_colors:
        exists = conn.execute(
            sa.select(sa.func.count()).select_from(colors).where(
                colors.c.color == color_name
            )
        ).scalar()
        if not exists:
            conn.execute(colors.insert().values(color=color_name))

    # Build color name -> id map
    color_rows = conn.execute(sa.select(colors.c.id, colors.c.color)).fetchall()
    color_map = {row[1]: row[0] for row in color_rows}

    # Insert color translations
    ct = sa.table(
        "color_translations",
        sa.column("color_source"),
        sa.column("color_target"),
        sa.column("color_target_id"),
    )
    for source, target in _COLOR_TRANSLATIONS:
        target_id = color_map.get(target)
        if not target_id:
            continue
        exists = conn.execute(
            sa.select(sa.func.count()).select_from(ct).where(
                ct.c.color_source == source
            )
        ).scalar()
        if not exists:
            conn.execute(
                ct.insert().values(
                    color_source=source,
                    color_target=target,
                    color_target_id=target_id,
                )
            )


def downgrade() -> None:
    conn = op.get_bind()

    ct = sa.table("color_translations", sa.column("color_source"))
    for source, _ in _COLOR_TRANSLATIONS:
        conn.execute(ct.delete().where(ct.c.color_source == source))

    model_refs = sa.table("model_references", sa.column("manufacturer_code"))
    for code, _ in _MODEL_REFERENCES:
        conn.execute(
            model_refs.delete().where(model_refs.c.manufacturer_code == code)
        )
