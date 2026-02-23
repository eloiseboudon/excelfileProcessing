"""Seed user with role 'user' (user@user / user).

Revision ID: m1_seed_user_role
Revises: l1_add_supplier_sku_to_catalog
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash

revision = "m1_seed_user_role"
down_revision = "l1_add_supplier_sku_to_catalog"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT id FROM users WHERE email = 'user@user'")
    ).fetchone()
    if not existing:
        conn.execute(
            sa.text(
                "INSERT INTO users (email, password_hash, role) "
                "VALUES (:email, :pw, :role)"
            ),
            {"email": "user@user", "pw": generate_password_hash("user"), "role": "user"},
        )


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM users WHERE email = 'user@user'"))
