"""add focus_fallback to mock_sessions

Revision ID: 20260504_000001
Revises: 20260502_000001
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260504_000001"
down_revision = "20260502_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mock_sessions",
        sa.Column(
            "focus_fallback",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("mock_sessions", "focus_fallback")
