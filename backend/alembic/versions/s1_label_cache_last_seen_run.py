"""Add last_seen_run_id to label_cache

Revision ID: s1_label_cache_last_seen_run
Revises: r1_product_ean_history
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa

revision = "s1_label_cache_last_seen_run"
down_revision = "r1_product_ean_history"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "label_cache",
        sa.Column("last_seen_run_id", sa.Integer(), sa.ForeignKey("matching_runs.id"), nullable=True),
    )
    op.create_index("ix_label_cache_last_seen_run", "label_cache", ["last_seen_run_id"])


def downgrade():
    op.drop_index("ix_label_cache_last_seen_run", table_name="label_cache")
    op.drop_column("label_cache", "last_seen_run_id")
