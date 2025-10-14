"""Add report columns to API fetch jobs

Revision ID: f9a0f1d3c2ab
Revises: f5f1b5b3480d
Create Date: 2024-03-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f9a0f1d3c2ab'
down_revision: Union[str, Sequence[str], None] = 'f5f1b5b3480d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'api_fetch_jobs',
        sa.Column(
            'report_updated_products',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        'api_fetch_jobs',
        sa.Column(
            'report_database_missing_products',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        'api_fetch_jobs',
        sa.Column(
            'report_api_missing_products',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('api_fetch_jobs', 'report_api_missing_products')
    op.drop_column('api_fetch_jobs', 'report_database_missing_products')
    op.drop_column('api_fetch_jobs', 'report_updated_products')
