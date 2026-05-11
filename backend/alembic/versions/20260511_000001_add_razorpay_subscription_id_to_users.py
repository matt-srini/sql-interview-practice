"""add razorpay_subscription_id to users

Revision ID: 20260511_000001
Revises: 20260504_000001
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260511_000001"
down_revision = "20260504_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS via raw SQL — op.add_column has no such flag
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_subscription_id TEXT")


def downgrade() -> None:
    op.drop_column("users", "razorpay_subscription_id")
