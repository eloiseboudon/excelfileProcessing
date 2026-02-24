"""Add match_reasoning JSONB column to label_cache.

Stores the score breakdown (brand: +15, model_family: +38, ...) for every
auto-match and human-validated match, enabling n-shot selection by confidence
and future calibration analysis.

Revision ID: n1_add_match_reasoning_to_label_cache
Revises: m1_seed_user_role
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "n1_match_reasoning"
down_revision = "m1_seed_user_role"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE label_cache ADD COLUMN IF NOT EXISTS match_reasoning JSONB"
    )


def downgrade():
    op.drop_column("label_cache", "match_reasoning")
