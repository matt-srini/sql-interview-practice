"""add lifetime_pro and lifetime_elite to users.plan check constraint

Revision ID: 20260416_000001
Revises: 20260407_000001
Create Date: 2026-04-16

"""
from alembic import op


revision = "20260416_000001"
down_revision = "20260407_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop both possible constraint names: the initial migration used
    # 'ck_users_plan' but this migration originally referenced 'users_plan_check'.
    # Drop both defensively so databases created via Alembic from scratch
    # (e.g. CI) and those seeded via ensure_schema_admin both end up clean.
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_plan")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_plan_check")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT users_plan_check "
        "CHECK (plan IN ('free', 'pro', 'elite', 'lifetime_pro', 'lifetime_elite'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_plan_check")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT users_plan_check "
        "CHECK (plan IN ('free', 'pro', 'elite'))"
    )
