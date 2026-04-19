"""rename stripe_* identifiers to razorpay/payment equivalents

Revision ID: 20260419_000001
Revises: 20260418_000001
Create Date: 2026-04-19

Stripe is unavailable in India, so we replaced it with Razorpay.  This
migration renames the payment-related columns and tables to be
provider-neutral where possible, and to the new provider where not.

No data is transformed: Stripe customer IDs were never persisted against
live users (the product was still pre-launch on payments), but we keep
the column values in place rather than null them to avoid surprising
data loss if any exist.  The values simply won't be used by the new
Razorpay router, which populates razorpay_customer_id via its own flow.
"""
from alembic import op


revision = "20260419_000001"
down_revision = "20260418_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users RENAME COLUMN stripe_customer_id TO razorpay_customer_id")
    op.execute("ALTER TABLE stripe_events RENAME TO payment_events")
    op.execute("ALTER TABLE plan_changes RENAME COLUMN stripe_event_id TO payment_event_id")


def downgrade() -> None:
    op.execute("ALTER TABLE plan_changes RENAME COLUMN payment_event_id TO stripe_event_id")
    op.execute("ALTER TABLE payment_events RENAME TO stripe_events")
    op.execute("ALTER TABLE users RENAME COLUMN razorpay_customer_id TO stripe_customer_id")
