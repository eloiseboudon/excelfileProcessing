"""Add matching_runs table.

Revision ID: q1_matching_runs
Revises: p1_nightly_pipeline
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

revision = "q1_matching_runs"
down_revision = "p1_nightly_pipeline"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS matching_runs (
            id SERIAL PRIMARY KEY,
            ran_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            supplier_id INTEGER,
            nightly_job_id INTEGER REFERENCES nightly_jobs(id),
            total_products INTEGER,
            from_cache INTEGER,
            llm_calls INTEGER,
            auto_matched INTEGER,
            pending_review INTEGER,
            auto_rejected INTEGER,
            not_found INTEGER,
            errors INTEGER,
            cost_estimate DOUBLE PRECISION,
            duration_seconds DOUBLE PRECISION,
            error_message TEXT
        )
    """)


def downgrade():
    op.drop_table("matching_runs")
