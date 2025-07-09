"""Initial migration"""

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

import backend.models as models


def upgrade() -> None:
    bind = op.get_bind()
    models.db.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    models.db.metadata.drop_all(bind=bind)
