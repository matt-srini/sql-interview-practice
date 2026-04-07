"""add mock tables

Revision ID: 20260407_000001
Revises: 20260323_000001
Create Date: 2026-04-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260407_000001"
down_revision = "20260323_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mock_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("track", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_limit_s", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_mock_sessions_user_started",
        "mock_sessions",
        ["user_id", sa.text("started_at DESC")],
    )

    op.create_table(
        "mock_session_questions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("track", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_solved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_code", sa.Text(), nullable=True),
        sa.Column("time_spent_s", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["mock_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_mock_session_questions_session",
        "mock_session_questions",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_mock_session_questions_session", table_name="mock_session_questions")
    op.drop_table("mock_session_questions")
    op.drop_index("idx_mock_sessions_user_started", table_name="mock_sessions")
    op.drop_table("mock_sessions")
