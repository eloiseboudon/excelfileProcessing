"""
add api raw items to reports

Revision ID: 7f7b6e9d8af8
Revises: f9a0f1d3c2ab
Create Date: 2024-06-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7f7b6e9d8af8'
down_revision = 'f9a0f1d3c2ab'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'api_fetch_jobs',
        sa.Column('report_api_raw_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column('api_fetch_jobs', 'report_api_raw_items')
