"""create mock_chain_consumption table

Revision ID: 20260528_000003
Revises: 20260528_000002
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_000003"
down_revision = "20260528_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mock_chain_consumption",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column(
            "consumed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "reclaimed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["mock_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("user_id", "parent_id"),
    )
    op.create_index(
        "idx_mcc_user_active",
        "mock_chain_consumption",
        ["user_id"],
        postgresql_where=sa.text("NOT reclaimed"),
    )


def downgrade() -> None:
    op.drop_index("idx_mcc_user_active", table_name="mock_chain_consumption")
    op.drop_table("mock_chain_consumption")
