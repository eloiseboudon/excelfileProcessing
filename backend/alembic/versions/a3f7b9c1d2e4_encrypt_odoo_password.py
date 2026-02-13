"""encrypt_odoo_password

Revision ID: a3f7b9c1d2e4
Revises: e1a2b3c4d5e6
Create Date: 2026-02-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a3f7b9c1d2e4"
down_revision: Union[str, None] = "e1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Encrypt existing plaintext passwords in odoo_configs."""
    from utils.crypto import encrypt_value

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, password FROM odoo_configs")).fetchall()
    for row in rows:
        # Skip already-encrypted values (Fernet tokens start with 'gAAAAA')
        if row[1] and not row[1].startswith("gAAAAA"):
            encrypted = encrypt_value(row[1])
            conn.execute(
                sa.text("UPDATE odoo_configs SET password = :pwd WHERE id = :id"),
                {"pwd": encrypted, "id": row[0]},
            )


def downgrade() -> None:
    """Decrypt passwords back to plaintext."""
    from utils.crypto import decrypt_value

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, password FROM odoo_configs")).fetchall()
    for row in rows:
        if row[1] and row[1].startswith("gAAAAA"):
            plaintext = decrypt_value(row[1])
            conn.execute(
                sa.text("UPDATE odoo_configs SET password = :pwd WHERE id = :id"),
                {"pwd": plaintext, "id": row[0]},
            )
