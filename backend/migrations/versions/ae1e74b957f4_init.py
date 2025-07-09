"""init"""

revision = 'ae1e74b957f4'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        'tests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False)
    )
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=True, unique=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('address', sa.String(length=200), nullable=True)
    )
    op.create_table(
        'brands',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('brand', sa.String(length=50), nullable=False)
    )
    op.create_table(
        'memory_options',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('memory', sa.String(length=50), nullable=False)
    )
    op.create_table(
        'colors',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('color', sa.String(length=50), nullable=False)
    )
    op.create_table(
        'color_translations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('color_source', sa.String(length=50), nullable=False),
        sa.Column('color_target', sa.String(length=50), nullable=False),
        sa.Column('color_target_id', sa.Integer(), sa.ForeignKey('colors.id'), nullable=False)
    )
    op.create_table(
        'device_types',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('type', sa.String(length=50), nullable=False)
    )
    op.create_table(
        'product_references',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('description', sa.String(length=200), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('selling_price', sa.Float(), nullable=True),
        sa.Column('ean', sa.String(length=20), nullable=False),
        sa.Column('supplier_id', sa.Integer(), sa.ForeignKey('suppliers.id'), nullable=True),
        sa.UniqueConstraint('ean', 'supplier_id', name='uix_reference_ean_supplier')
    )
    op.create_table(
        'temporary_imports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('description', sa.String(length=200), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('selling_price', sa.Float(), nullable=True),
        sa.Column('ean', sa.String(length=20), nullable=False),
        sa.Column('test', sa.Float(), nullable=True),
        sa.Column('test2', sa.Float(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), sa.ForeignKey('suppliers.id'), nullable=True),
        sa.UniqueConstraint('ean', 'supplier_id', name='uix_temp_ean_supplier')
    )
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('reference_id', sa.Integer(), sa.ForeignKey('product_references.id'), nullable=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.String(length=120), nullable=False),
        sa.Column('supplier_id', sa.Integer(), sa.ForeignKey('suppliers.id'), nullable=True),
        sa.Column('brand_id', sa.Integer(), sa.ForeignKey('brands.id'), nullable=True),
        sa.Column('memory_id', sa.Integer(), sa.ForeignKey('memory_options.id'), nullable=True),
        sa.Column('color_id', sa.Integer(), sa.ForeignKey('colors.id'), nullable=True),
        sa.Column('type_id', sa.Integer(), sa.ForeignKey('device_types.id'), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.UniqueConstraint('reference_id', 'supplier_id', name='uix_product_reference_supplier')
    )
    op.create_table(
        'product_calculations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('tcp', sa.Float(), nullable=False),
        sa.Column('marge4_5', sa.Float(), nullable=False),
        sa.Column('prixht_tcp_marge4_5', sa.Float(), nullable=False),
        sa.Column('prixht_marge4_5', sa.Float(), nullable=False),
        sa.Column('prixht_max', sa.Float(), nullable=False)
    )
    op.create_table(
        'import_histories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('filename', sa.String(length=200), nullable=False),
        sa.Column('supplier_id', sa.Integer(), sa.ForeignKey('suppliers.id'), nullable=True),
        sa.Column('product_count', sa.Integer(), nullable=False),
        sa.Column('import_date', sa.DateTime(), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('import_histories')
    op.drop_table('product_calculations')
    op.drop_table('products')
    op.drop_table('temporary_imports')
    op.drop_table('product_references')
    op.drop_table('device_types')
    op.drop_table('color_translations')
    op.drop_table('colors')
    op.drop_table('memory_options')
    op.drop_table('brands')
    op.drop_table('suppliers')
    op.drop_table('tests')

