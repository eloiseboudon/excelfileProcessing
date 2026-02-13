"""add_odoo_config_and_sync_jobs

Revision ID: e1a2b3c4d5e6
Revises: 13d58c57a974
Create Date: 2026-02-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "e1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "13d58c57a974"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    existing = inspect(conn).get_table_names()
    if "odoo_configs" in existing:
        return
    op.create_table(
        "odoo_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("database", sa.String(length=100), nullable=False),
        sa.Column("login", sa.String(length=100), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("auto_sync_enabled", sa.Boolean(), server_default="false"),
        sa.Column("auto_sync_interval_minutes", sa.Integer(), server_default="1440"),
        sa.Column("last_auto_sync_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
    )

    op.create_table(
        "odoo_sync_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "started_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="running"),
        sa.Column("trigger", sa.String(length=20), server_default="manual"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_odoo_products", sa.Integer(), server_default="0"),
        sa.Column("created_count", sa.Integer(), server_default="0"),
        sa.Column("updated_count", sa.Integer(), server_default="0"),
        sa.Column("unchanged_count", sa.Integer(), server_default="0"),
        sa.Column("error_count", sa.Integer(), server_default="0"),
        sa.Column("report_created", JSONB(), nullable=True),
        sa.Column("report_updated", JSONB(), nullable=True),
        sa.Column("report_unchanged", JSONB(), nullable=True),
        sa.Column("report_errors", JSONB(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("odoo_sync_jobs")
    op.drop_table("odoo_configs")
