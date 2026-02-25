"""Add nightly pipeline tables.

Revision ID: p1_nightly_pipeline
Revises: o1_label_refs
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa

revision = "p1_nightly_pipeline"
down_revision = "o1_label_refs"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS nightly_config (
            id SERIAL PRIMARY KEY,
            enabled BOOLEAN NOT NULL DEFAULT false,
            run_hour INTEGER NOT NULL DEFAULT 2,
            run_minute INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS nightly_jobs (
            id SERIAL PRIMARY KEY,
            started_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            finished_at TIMESTAMP WITH TIME ZONE,
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            odoo_synced INTEGER,
            suppliers_synced INTEGER,
            matching_submitted INTEGER,
            email_sent BOOLEAN NOT NULL DEFAULT false,
            error_message TEXT
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS nightly_email_recipients (
            id SERIAL PRIMARY KEY,
            email VARCHAR(200) UNIQUE NOT NULL,
            name VARCHAR(100),
            active BOOLEAN NOT NULL DEFAULT true
        )
    """)

    # Insert default config row only if table is empty
    op.execute("""
        INSERT INTO nightly_config (enabled, run_hour, run_minute)
        SELECT false, 2, 0
        WHERE NOT EXISTS (SELECT 1 FROM nightly_config)
    """)


def downgrade():
    op.drop_table("nightly_email_recipients")
    op.drop_table("nightly_jobs")
    op.drop_table("nightly_config")
