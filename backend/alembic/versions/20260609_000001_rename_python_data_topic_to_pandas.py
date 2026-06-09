"""Rename python_data/python-data topic to pandas in all tables.

This migration eliminates the legacy python_data (db_topic) and python-data (slug)
aliases from the database, replacing them with the single canonical token 'pandas'.

Tables affected:
  - user_progress.topic:           was 'python_data'
  - user_sample_seen.topic:        was 'python_data'
  - submissions.track:             was 'python-data'
  - mock_sessions.track:           was 'python-data'
  - mock_session_questions.track:  was 'python-data'

Idempotent: uses WHERE IN ('python_data', 'python-data') so it is safe to run twice.

Revision ID: 20260609_000001
Revises: 20260528_000003
Create Date: 2026-06-09
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '20260609_000001'
down_revision = '20260528_000003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user_progress — written with db_topic = 'python_data'
    op.execute(
        "UPDATE user_progress SET topic = 'pandas' WHERE topic IN ('python_data', 'python-data')"
    )
    # user_sample_seen — written with db_topic = 'python_data'
    op.execute(
        "UPDATE user_sample_seen SET topic = 'pandas' WHERE topic IN ('python_data', 'python-data')"
    )
    # submissions — written with track = 'python-data' (the slug)
    op.execute(
        "UPDATE submissions SET track = 'pandas' WHERE track IN ('python_data', 'python-data')"
    )
    # mock_sessions — written with track = 'python-data' (the slug)
    op.execute(
        "UPDATE mock_sessions SET track = 'pandas' WHERE track IN ('python_data', 'python-data')"
    )
    # mock_session_questions — written with track = 'python-data' (the slug)
    op.execute(
        "UPDATE mock_session_questions SET track = 'pandas' WHERE track IN ('python_data', 'python-data')"
    )


def downgrade() -> None:
    # Lossy best-effort: reverses to 'python_data' (the canonical old write value).
    # Note: 'python-data' was the slug but 'python_data' was what the practice router
    # wrote to user_progress/user_sample_seen. We reverse to 'python_data' uniformly.
    op.execute(
        "UPDATE user_progress SET topic = 'python_data' WHERE topic = 'pandas'"
    )
    op.execute(
        "UPDATE user_sample_seen SET topic = 'python_data' WHERE topic = 'pandas'"
    )
    op.execute(
        "UPDATE submissions SET track = 'python-data' WHERE track = 'pandas'"
    )
    op.execute(
        "UPDATE mock_sessions SET track = 'python-data' WHERE track = 'pandas'"
    )
    op.execute(
        "UPDATE mock_session_questions SET track = 'python-data' WHERE track = 'pandas'"
    )
