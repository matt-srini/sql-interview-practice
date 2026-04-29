"""add is_follow_up to mock_session_questions

Revision ID: 20260429_000001
Revises: 20260420_000002
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260429_000001"
down_revision = "20260420_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mock_session_questions",
        sa.Column("is_follow_up", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("mock_session_questions", "is_follow_up")
