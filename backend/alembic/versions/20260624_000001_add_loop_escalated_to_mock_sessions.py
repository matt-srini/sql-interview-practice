"""Add loop_escalated column to mock_sessions.

Stores the actual escalation flag per interview_loop session at creation time
so history and active-session reads reflect what the session ACTUALLY did
rather than recomputing from the current cell-level flag (which can change as
new chains are added). NULL = not an interview_loop session (or pre-backfill).

Revision ID: 20260624_000001
Revises: 20260612_000001
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa

revision = '20260624_000001'
down_revision = '20260612_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS keeps this idempotent and aligned with the additive ALTER in
    # db._SCHEMA_SQL (dev/test build the schema from there, prod from Alembic).
    op.execute(
        "ALTER TABLE mock_sessions "
        "ADD COLUMN IF NOT EXISTS loop_escalated BOOLEAN"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE mock_sessions DROP COLUMN IF EXISTS loop_escalated")
