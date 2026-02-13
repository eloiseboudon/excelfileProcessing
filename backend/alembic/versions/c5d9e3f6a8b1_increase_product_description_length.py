"""increase product model and description to 500

Revision ID: c5d9e3f6a8b1
Revises: b4c8d2e5f6a7
Create Date: 2026-02-13 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c5d9e3f6a8b1"
down_revision: Union[str, None] = "b4c8d2e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "products",
        "model",
        existing_type=sa.String(250),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "description",
        existing_type=sa.String(120),
        type_=sa.String(500),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "model",
        existing_type=sa.String(500),
        type_=sa.String(250),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "description",
        existing_type=sa.String(500),
        type_=sa.String(120),
        existing_nullable=True,
    )
