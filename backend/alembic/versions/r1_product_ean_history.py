"""Add product_ean_history table

Revision ID: r1_product_ean_history
Revises: q1_matching_runs
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa

revision = "r1_product_ean_history"
down_revision = "q1_matching_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_ean_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("ean", sa.String(20), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("matching_run_id", sa.Integer(), sa.ForeignKey("matching_runs.id"), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("seen_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_product_ean_history_product_ean",
        "product_ean_history",
        ["product_id", "ean"],
    )


def downgrade():
    op.drop_index("ix_product_ean_history_product_ean", table_name="product_ean_history")
    op.drop_table("product_ean_history")
