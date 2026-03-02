"""cleanup cross-region pending matches

Revision ID: 97e5f0069448
Revises: 77ec0002c244
Create Date: 2026-03-02 12:13:53.492450

Deletes pending_matches (status='pending') where a candidate product has a
region mismatch with the extracted label region. These were created before
region inference was added and would never be valid matches.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97e5f0069448'
down_revision: Union[str, Sequence[str], None] = '77ec0002c244'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Delete pending matches where candidates have cross-region mismatches."""
    connection = op.get_bind()

    connection.execute(sa.text("""
        DELETE FROM pending_matches
        WHERE status = 'pending'
          AND id IN (
            SELECT pm.id
            FROM pending_matches pm,
                 jsonb_array_elements(pm.candidates) AS c
            JOIN products p ON p.id = (c->>'product_id')::int
            WHERE pm.status = 'pending'
              AND p.region IS NOT NULL
              AND p.region != ''
              AND p.region != 'EU'
              AND UPPER(COALESCE(pm.extracted_attributes->>'region', 'EU')) != UPPER(p.region)
          );
    """))


def downgrade() -> None:
    """No rollback — deleted pending matches will be recreated by the next matching run."""
    pass
