"""add role to mock_sessions

Revision ID: 20260528_000001
Revises: 20260511_000001
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_000001"
down_revision = "20260511_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mock_sessions",
        sa.Column("role", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mock_sessions", "role")
