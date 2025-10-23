"""Add supplier API ETL tables"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f5f1b5b3480d'
down_revision: Union[str, Sequence[str], None] = 'ce3dc80a2ad6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TYPE IF EXISTS authtype CASCADE")
    op.execute("DROP TYPE IF EXISTS paginationtype CASCADE")

    authtype = postgresql.ENUM(
        'none', 'api_key', 'basic', 'oauth2', name='authtype', create_type=False
    )
    authtype.create(op.get_bind(), checkfirst=True)
    pagination_type = postgresql.ENUM(
        'none',
        'page',
        'cursor',
        'link',
        'offset',
        name='paginationtype',
        create_type=False,
    )
    pagination_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'supplier_apis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('base_url', sa.String(length=255), nullable=False),
        sa.Column(
            'auth_type',
            postgresql.ENUM(
                'none', 'api_key', 'basic', 'oauth2', name='authtype', create_type=False
            ),
            nullable=False,
            server_default='none',
        ),
        sa.Column(
            'auth_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            'default_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column('rate_limit_per_min', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['supplier_id'],
            ['suppliers.id'],
            name=op.f('fk_supplier_apis_supplier_id_suppliers'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_supplier_apis')),
    )

    op.create_table(
        'api_endpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_api_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('path', sa.String(length=255), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False, server_default='GET'),
        sa.Column(
            'query_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            'body_template', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            'content_type',
            sa.String(length=50),
            nullable=False,
            server_default='application/json',
        ),
        sa.Column(
            'pagination_type',
            postgresql.ENUM(
                'none',
                'page',
                'cursor',
                'link',
                'offset',
                name='paginationtype',
                create_type=False,
            ),
            nullable=False,
            server_default='none',
        ),
        sa.Column(
            'pagination_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column('items_path', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ['supplier_api_id'],
            ['supplier_apis.id'],
            name=op.f('fk_api_endpoints_supplier_api_id_supplier_apis'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_api_endpoints')),
    )

    op.create_table(
        'mapping_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_api_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column(
            'is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')
        ),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['supplier_api_id'],
            ['supplier_apis.id'],
            name=op.f('fk_mapping_versions_supplier_api_id_supplier_apis'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_mapping_versions')),
    )

    op.create_table(
        'field_maps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mapping_version_id', sa.Integer(), nullable=False),
        sa.Column('target_field', sa.String(length=100), nullable=False),
        sa.Column('source_path', sa.String(length=300), nullable=False),
        sa.Column('transform', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ['mapping_version_id'],
            ['mapping_versions.id'],
            name=op.f('fk_field_maps_mapping_version_id_mapping_versions'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_field_maps')),
    )

    op.create_table(
        'api_fetch_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_api_id', sa.Integer(), nullable=False),
        sa.Column('endpoint_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column(
            'status', sa.String(length=20), nullable=True, server_default='running'
        ),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column(
            'params_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ['endpoint_id'],
            ['api_endpoints.id'],
            name=op.f('fk_api_fetch_jobs_endpoint_id_api_endpoints'),
        ),
        sa.ForeignKeyConstraint(
            ['supplier_api_id'],
            ['supplier_apis.id'],
            name=op.f('fk_api_fetch_jobs_supplier_api_id_supplier_apis'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_api_fetch_jobs')),
    )

    op.create_table(
        'raw_ingests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('payload', sa.LargeBinary(), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('page_index', sa.Integer(), nullable=True),
        sa.Column('cursor', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ['job_id'],
            ['api_fetch_jobs.id'],
            name=op.f('fk_raw_ingests_job_id_api_fetch_jobs'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_raw_ingests')),
    )

    op.create_table(
        'parsed_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('ean', sa.String(length=20), nullable=True),
        sa.Column('part_number', sa.String(length=120), nullable=True),
        sa.Column('model', sa.String(length=250), nullable=True),
        sa.Column('description', sa.String(length=400), nullable=True),
        sa.Column('brand', sa.String(length=100), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('memory', sa.String(length=50), nullable=True),
        sa.Column('ram', sa.String(length=50), nullable=True),
        sa.Column('norme', sa.String(length=50), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('purchase_price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('recommended_price', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['job_id'],
            ['api_fetch_jobs.id'],
            name=op.f('fk_parsed_items_job_id_api_fetch_jobs'),
        ),
        sa.ForeignKeyConstraint(
            ['supplier_id'],
            ['suppliers.id'],
            name=op.f('fk_parsed_items_supplier_id_suppliers'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_parsed_items')),
        sa.UniqueConstraint(
            'supplier_id',
            'ean',
            'part_number',
            'job_id',
            name='uix_parsed_supplier_ean_part_job',
        ),
    )

    op.create_table(
        'supplier_product_refs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('ean', sa.String(length=20), nullable=True),
        sa.Column('part_number', sa.String(length=120), nullable=True),
        sa.Column('supplier_sku', sa.String(length=120), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['product_id'],
            ['products.id'],
            name=op.f('fk_supplier_product_refs_product_id_products'),
        ),
        sa.ForeignKeyConstraint(
            ['supplier_id'],
            ['suppliers.id'],
            name=op.f('fk_supplier_product_refs_supplier_id_suppliers'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_supplier_product_refs')),
        sa.UniqueConstraint(
            'supplier_id', 'ean', 'part_number', 'supplier_sku', name='uix_supplier_ref'
        ),
    )


def downgrade() -> None:
    op.drop_table('supplier_product_refs')
    op.drop_table('parsed_items')
    op.drop_table('raw_ingests')
    op.drop_table('api_fetch_jobs')
    op.drop_table('field_maps')
    op.drop_table('mapping_versions')
    op.drop_table('api_endpoints')
    op.drop_table('supplier_apis')

    sa.Enum(name='paginationtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='authtype').drop(op.get_bind(), checkfirst=True)
