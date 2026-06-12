"""Add provider column to payment_events (dual-rail Razorpay + Paddle).

datathink now bills through two rails: Razorpay for INR (India) and Paddle —
acting as Merchant of Record — for the rest of the world. Both feed the same
payment_events idempotency log. The event_id PK stays collision-proof because
Paddle events are stored with a "paddle:" prefix, but we add an explicit
provider column so monthly reconciliation (e.g. mapping a Paddle payout to its
FIRC for GST export treatment) and operator queries can slice by rail without
parsing the id. Existing rows are all Razorpay, hence the default.

Revision ID: 20260612_000001
Revises: 20260610_000002
Create Date: 2026-06-12
"""

from alembic import op

revision = '20260612_000001'
down_revision = '20260610_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS keeps this idempotent and aligned with the additive ALTER in
    # db._SCHEMA_SQL (dev/test build the schema from there, prod from Alembic).
    op.execute(
        "ALTER TABLE payment_events "
        "ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'razorpay'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE payment_events DROP COLUMN IF EXISTS provider")
