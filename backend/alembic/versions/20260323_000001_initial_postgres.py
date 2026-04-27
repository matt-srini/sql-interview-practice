"""initial postgres schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260323_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=True, unique=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("pwd_hash", sa.Text(), nullable=True),
        sa.Column("pwd_salt", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=False, server_default=sa.text("'free'")),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True, unique=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("upgraded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("plan IN ('free', 'pro', 'elite')", name="ck_users_plan"),
    )

    op.create_table(
        "sessions",
        sa.Column("token", sa.Text(), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )

    op.create_table(
        "user_progress",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("solved_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("user_id", "question_id"),
    )

    op.create_table(
        "user_sample_seen",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("difficulty", sa.Text(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("user_id", "difficulty", "question_id"),
    )

    op.create_table(
        "stripe_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("payload_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track", sa.Text(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "plan_changes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("old_plan", sa.Text(), nullable=False),
        sa.Column("new_plan", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("stripe_event_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "oauth_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_user_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "provider_user_id"),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("token", sa.Text(), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_index("idx_sessions_user", "sessions", ["user_id"])
    op.create_index("idx_sessions_expires", "sessions", ["expires_at"])
    op.create_index("idx_progress_user", "user_progress", ["user_id"])
    op.create_index("idx_plan_changes_user", "plan_changes", ["user_id"])
    op.create_index("idx_submissions_user_question", "submissions", ["user_id", "question_id", "track"])
    op.create_index("idx_submissions_user_recent", "submissions", ["user_id", "submitted_at"])
    op.create_index("idx_oauth_accounts_user", "oauth_accounts", ["user_id"])
    op.create_index("idx_reset_tokens_user", "password_reset_tokens", ["user_id"])
    op.create_index("idx_reset_tokens_expires", "password_reset_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_reset_tokens_expires", table_name="password_reset_tokens")
    op.drop_index("idx_reset_tokens_user", table_name="password_reset_tokens")
    op.drop_index("idx_oauth_accounts_user", table_name="oauth_accounts")
    op.drop_index("idx_submissions_user_recent", table_name="submissions")
    op.drop_index("idx_submissions_user_question", table_name="submissions")
    op.drop_index("idx_plan_changes_user", table_name="plan_changes")
    op.drop_index("idx_progress_user", table_name="user_progress")
    op.drop_index("idx_sessions_expires", table_name="sessions")
    op.drop_index("idx_sessions_user", table_name="sessions")
    op.drop_table("password_reset_tokens")
    op.drop_table("oauth_accounts")
    op.drop_table("submissions")
    op.drop_table("plan_changes")
    op.drop_table("stripe_events")
    op.drop_table("user_sample_seen")
    op.drop_table("user_progress")
    op.drop_table("sessions")
    op.drop_table("users")
