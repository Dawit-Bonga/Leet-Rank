"""Create the V1 core schema."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_v1_core"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("auth_user_id", sa.Uuid(), unique=True),
        sa.Column("leetcode_username", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("scoring_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "problems",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("leetcode_slug", sa.String(255), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("difficulty", sa.String(6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("difficulty IN ('EASY', 'MEDIUM', 'HARD')", name="ck_problems_difficulty"),
    )
    op.create_table(
        "submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_id", sa.Uuid(), sa.ForeignKey("problems.id"), nullable=False),
        sa.Column("external_submission_id", sa.String(64), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "external_submission_id", name="uq_submissions_user_external_id"),
    )
    op.create_index("ix_submissions_user_submitted_at", "submissions", ["user_id", "submitted_at"])
    op.create_table(
        "user_problem_stats",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("problem_id", sa.Uuid(), sa.ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("first_solved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_solved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_rewarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rewarded_solve_count", sa.Integer(), nullable=False),
    )
    op.create_table(
        "score_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_id", sa.Uuid(), sa.ForeignKey("problems.id"), nullable=False),
        sa.Column("submission_id", sa.Uuid(), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("points >= 0", name="ck_score_events_points_nonnegative"),
        sa.CheckConstraint("reason IN ('FIRST_SOLVE', 'REVIEW', 'COOLDOWN')", name="ck_score_events_reason"),
    )
    op.create_index("ix_score_events_user_earned_at", "score_events", ["user_id", "earned_at"])
    op.create_table(
        "user_sync_state",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True)),
        sa.Column("last_successful_at", sa.DateTime(timezone=True)),
        sa.Column("sync_status", sa.String(16), nullable=False),
        sa.Column("last_error", sa.String(500)),
        sa.CheckConstraint("sync_status IN ('IDLE', 'RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_sync_status"),
    )
    op.create_table(
        "friendships",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("friend_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("user_id <> friend_id", name="ck_friendships_not_self"),
    )


def downgrade() -> None:
    op.drop_table("friendships")
    op.drop_table("user_sync_state")
    op.drop_index("ix_score_events_user_earned_at", table_name="score_events")
    op.drop_table("score_events")
    op.drop_table("user_problem_stats")
    op.drop_index("ix_submissions_user_submitted_at", table_name="submissions")
    op.drop_table("submissions")
    op.drop_table("problems")
    op.drop_table("users")
