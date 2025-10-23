"""add api raw items to reports

Revision ID: 7f7b6e9d8af8
Revises: 4f0e2d1f5e7b
Create Date: 2024-06-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7f7b6e9d8af8'
down_revision = '4f0e2d1f5e7b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'api_fetch_jobs',
        sa.Column('report_api_raw_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column('api_fetch_jobs', 'report_api_raw_items')
