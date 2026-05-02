"""add oauth_states and magic_link_tokens tables

Revision ID: 20260502_000001
Revises: 20260429_000001
Create Date: 2026-05-02
"""

from alembic import op


revision = "20260502_000001"
down_revision = "20260429_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_states (
            state_token TEXT PRIMARY KEY,
            user_agent_hash TEXT,
            ip_prefix TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states(expires_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS magic_link_tokens (
            token TEXT PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_magic_link_tokens_user ON magic_link_tokens(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_magic_link_tokens_expires ON magic_link_tokens(expires_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS magic_link_tokens")
    op.execute("DROP TABLE IF EXISTS oauth_states")
