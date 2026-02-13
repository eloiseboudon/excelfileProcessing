"""add deleted fields to odoo_sync_jobs

Revision ID: b4c8d2e5f6a7
Revises: a3f7b9c1d2e4
Create Date: 2026-02-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b4c8d2e5f6a7"
down_revision: Union[str, None] = "a3f7b9c1d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "odoo_sync_jobs",
        sa.Column("deleted_count", sa.Integer(), server_default="0"),
    )
    op.add_column(
        "odoo_sync_jobs",
        sa.Column("report_deleted", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("odoo_sync_jobs", "report_deleted")
    op.drop_column("odoo_sync_jobs", "deleted_count")
