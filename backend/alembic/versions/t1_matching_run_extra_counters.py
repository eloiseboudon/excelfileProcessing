"""Add cache hit counters to matching_runs

Revision ID: t1_matching_run_extra_counters
Revises: s1_label_cache_last_seen_run
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa

revision = "t1_matching_run_extra_counters"
down_revision = "s1_label_cache_last_seen_run"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("matching_runs", sa.Column("cross_supplier_hits", sa.Integer(), nullable=True))
    op.add_column("matching_runs", sa.Column("fuzzy_hits", sa.Integer(), nullable=True))
    op.add_column("matching_runs", sa.Column("attr_share_hits", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("matching_runs", "attr_share_hits")
    op.drop_column("matching_runs", "fuzzy_hits")
    op.drop_column("matching_runs", "cross_supplier_hits")
