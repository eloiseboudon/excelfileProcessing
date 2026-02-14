"""add_llm_matching_tables

Revision ID: f1a2b3c4d5e7
Revises: c5d9e3f6a8b1
Create Date: 2026-02-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "f1a2b3c4d5e7"
down_revision: Union[str, Sequence[str], None] = "c5d9e3f6a8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = inspect(conn).get_table_names()

    # Add region column to products
    columns = [col["name"] for col in inspect(conn).get_columns("products")]
    if "region" not in columns:
        op.add_column("products", sa.Column("region", sa.String(30), nullable=True))

    # Add region column to temporary_imports
    ti_columns = [col["name"] for col in inspect(conn).get_columns("temporary_imports")]
    if "region" not in ti_columns:
        op.add_column(
            "temporary_imports", sa.Column("region", sa.String(30), nullable=True)
        )

    if "model_references" not in existing:
        op.create_table(
            "model_references",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "manufacturer_code", sa.String(50), nullable=False, unique=True
            ),
            sa.Column("commercial_name", sa.String(100), nullable=False),
            sa.Column(
                "brand_id",
                sa.Integer(),
                sa.ForeignKey("brands.id"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
            ),
        )

    if "label_cache" not in existing:
        op.create_table(
            "label_cache",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "supplier_id",
                sa.Integer(),
                sa.ForeignKey("suppliers.id"),
                nullable=False,
            ),
            sa.Column("normalized_label", sa.String(300), nullable=False),
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("products.id"),
                nullable=True,
            ),
            sa.Column("match_score", sa.Integer(), nullable=True),
            sa.Column("match_source", sa.String(20), nullable=False),
            sa.Column("extracted_attributes", JSONB, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "last_used_at",
                sa.DateTime(),
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "supplier_id", "normalized_label", name="uix_label_cache"
            ),
        )

    if "pending_matches" not in existing:
        op.create_table(
            "pending_matches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "supplier_id",
                sa.Integer(),
                sa.ForeignKey("suppliers.id"),
                nullable=False,
            ),
            sa.Column(
                "temporary_import_id",
                sa.Integer(),
                sa.ForeignKey("temporary_imports.id"),
                nullable=True,
            ),
            sa.Column("source_label", sa.String(300), nullable=False),
            sa.Column("extracted_attributes", JSONB, nullable=False),
            sa.Column("candidates", JSONB, nullable=False),
            sa.Column("status", sa.String(20), server_default="pending"),
            sa.Column(
                "resolved_product_id",
                sa.Integer(),
                sa.ForeignKey("products.id"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
            ),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("pending_matches")
    op.drop_table("label_cache")
    op.drop_table("model_references")
    op.drop_column("temporary_imports", "region")
    op.drop_column("products", "region")
