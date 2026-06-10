"""Add mock_discards table — per-day penalty-free discard cap (audit C4).

A mock-session discard within the 2-minute window hard-deletes the session row,
which refunds the rate-limit quota. To stop a user from re-rolling/previewing
question sets indefinitely (start -> discard -> repeat), penalty-free discards are
capped per day. Discarded sessions leave no trace in mock_sessions, so each allowed
discard is logged here and counted per UTC day.

Revision ID: 20260610_000002
Revises: 20260610_000001
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260610_000002'
down_revision = '20260610_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mock_discards',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'discarded_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_mock_discards_user_day', 'mock_discards', ['user_id', 'discarded_at'])


def downgrade() -> None:
    op.drop_index('idx_mock_discards_user_day', table_name='mock_discards')
    op.drop_table('mock_discards')
