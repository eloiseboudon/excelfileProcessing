"""Add coverage counters to matching_runs

Revision ID: u1_matching_run_coverage
Revises: t1_matching_run_extra_counters
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "u1_matching_run_coverage"
down_revision = "t1_matching_run_extra_counters"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    columns = [c["name"] for c in sa.inspect(conn).get_columns("matching_runs")]
    if "total_odoo_products" not in columns:
        op.add_column("matching_runs", sa.Column("total_odoo_products", sa.Integer(), nullable=True))
    if "matched_products" not in columns:
        op.add_column("matching_runs", sa.Column("matched_products", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("matching_runs", "matched_products")
    op.drop_column("matching_runs", "total_odoo_products")
