"""add submission duration_ms

Revision ID: 20260420_000002
Revises: 20260420_000001
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260420_000002"
down_revision = "20260420_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("duration_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("submissions", "duration_ms")
