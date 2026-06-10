"""Add plan_override and plan_override_until columns to users.

Used by the admin grant system to give time-limited Pro/Elite access
to beta testers and invited users without a Razorpay subscription.

The effective plan returned to the frontend is:
  plan_override  if plan_override_until > now()
  plan           otherwise

Both columns are nullable; NULL means no override is active.

Revision ID: 20260610_000001
Revises: 20260609_000001
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = '20260610_000001'
down_revision = '20260609_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('plan_override', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('plan_override_until', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'plan_override_until')
    op.drop_column('users', 'plan_override')
