"""add topic column to user_progress and user_sample_seen

Revision ID: 20260417_000001
Revises: 20260416_000001
Create Date: 2026-04-17

The initial migration created user_progress and user_sample_seen without a
topic column, but the application schema (db.py _SCHEMA_SQL) has always used
topic to disambiguate progress across the SQL/Python/Pandas/PySpark tracks.
This migration:
  - adds topic TEXT NOT NULL DEFAULT 'sql' to both tables
  - rebuilds their primary keys to include topic
  - creates idx_progress_user_topic which ensure_schema relies on
"""
from alembic import op


revision = "20260417_000001"
down_revision = "20260416_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- user_progress ---
    # Add topic column (IF NOT EXISTS is safe for DBs already on the new schema)
    op.execute(
        "ALTER TABLE user_progress ADD COLUMN IF NOT EXISTS topic TEXT NOT NULL DEFAULT 'sql'"
    )
    # Rebuild PK to include topic
    op.execute("ALTER TABLE user_progress DROP CONSTRAINT IF EXISTS user_progress_pkey")
    op.execute(
        "ALTER TABLE user_progress ADD PRIMARY KEY (user_id, question_id, topic)"
    )

    # --- user_sample_seen ---
    op.execute(
        "ALTER TABLE user_sample_seen ADD COLUMN IF NOT EXISTS topic TEXT NOT NULL DEFAULT 'sql'"
    )
    op.execute(
        "ALTER TABLE user_sample_seen DROP CONSTRAINT IF EXISTS user_sample_seen_pkey"
    )
    op.execute(
        "ALTER TABLE user_sample_seen ADD PRIMARY KEY (user_id, difficulty, question_id, topic)"
    )

    # --- indexes ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_progress_user_topic ON user_progress(user_id, topic)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_progress_user_topic")

    # Restore user_progress PK (topic removed)
    op.execute("ALTER TABLE user_progress DROP CONSTRAINT IF EXISTS user_progress_pkey")
    op.execute("ALTER TABLE user_progress ADD PRIMARY KEY (user_id, question_id)")
    op.execute("ALTER TABLE user_progress DROP COLUMN IF EXISTS topic")

    # Restore user_sample_seen PK (topic removed)
    op.execute(
        "ALTER TABLE user_sample_seen DROP CONSTRAINT IF EXISTS user_sample_seen_pkey"
    )
    op.execute(
        "ALTER TABLE user_sample_seen ADD PRIMARY KEY (user_id, difficulty, question_id)"
    )
    op.execute("ALTER TABLE user_sample_seen DROP COLUMN IF EXISTS topic")
