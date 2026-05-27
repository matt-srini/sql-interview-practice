"""add follow_up_dimension to mock_session_questions

Revision ID: 20260528_000002
Revises: 20260528_000001
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_000002"
down_revision = "20260528_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mock_session_questions",
        sa.Column("follow_up_dimension", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mock_session_questions", "follow_up_dimension")
