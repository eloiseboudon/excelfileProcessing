"""add mapping version foreign key to api fetch jobs

Revision ID: 3b8f3c9e9c41
Revises: f9a0f1d3c2ab
Create Date: 2025-10-14 08:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b8f3c9e9c41'
down_revision = 'f9a0f1d3c2ab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'api_fetch_jobs',
        sa.Column('mapping_version_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        op.f('fk_api_fetch_jobs_mapping_version_id_mapping_versions'),
        'api_fetch_jobs',
        'mapping_versions',
        ['mapping_version_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f('fk_api_fetch_jobs_mapping_version_id_mapping_versions'),
        'api_fetch_jobs',
        type_='foreignkey',
    )
    op.drop_column('api_fetch_jobs', 'mapping_version_id')
