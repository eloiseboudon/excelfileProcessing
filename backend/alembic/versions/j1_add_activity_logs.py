"""Add activity_logs table

Revision ID: j1_add_activity_logs
Revises: i1_rename_temp
Create Date: 2026-02-14
"""

from alembic import op
from sqlalchemy import inspect as sa_inspect
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "j1_add_activity_logs"
down_revision = "i1_rename_temp"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    if "activity_logs" not in inspector.get_table_names():
        op.create_table(
            "activity_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
            ),
            sa.Column("details", JSONB, nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
        )

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("activity_logs")}
    if "ix_activity_logs_action" not in existing_indexes:
        op.create_index("ix_activity_logs_action", "activity_logs", ["action"])
    if "ix_activity_logs_category" not in existing_indexes:
        op.create_index("ix_activity_logs_category", "activity_logs", ["category"])


def downgrade():
    op.drop_index("ix_activity_logs_category", table_name="activity_logs")
    op.drop_index("ix_activity_logs_action", table_name="activity_logs")
    op.drop_table("activity_logs")
