"""add email_verified column and email_verification_tokens table

Revision ID: 20260417_000001
Revises: 20260416_000001
Create Date: 2026-04-17

"""
from alembic import op


revision = "20260418_000001"
down_revision = "20260417_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            token TEXT PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_user ON email_verification_tokens(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_expires ON email_verification_tokens(expires_at)"
    )

    # Grandfather existing registered users — they were trusted at sign-up time
    op.execute("UPDATE users SET email_verified = true WHERE email IS NOT NULL AND pwd_hash IS NOT NULL")

    # Grandfather OAuth users — OAuth proves email ownership
    op.execute(
        "UPDATE users SET email_verified = true WHERE id IN (SELECT DISTINCT user_id FROM oauth_accounts)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS email_verification_tokens")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified")
