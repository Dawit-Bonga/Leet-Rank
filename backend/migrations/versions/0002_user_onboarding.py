"""Add V1 user onboarding fields."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_user_onboarding"
down_revision: str | Sequence[str] | None = "0001_v1_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("primary_goal", sa.String(24)))
        batch_op.add_column(sa.Column("leetcode_experience", sa.String(16)))
        batch_op.add_column(sa.Column("weekly_problem_goal", sa.Integer()))
        batch_op.add_column(sa.Column("onboarding_completed_at", sa.DateTime(timezone=True)))
        batch_op.create_check_constraint(
            "ck_users_primary_goal",
            "primary_goal IS NULL OR primary_goal IN "
            "('ACCOUNTABILITY', 'CONSISTENCY', 'COMPETITION', 'INTERVIEW_PREP', 'LEARNING')",
        )
        batch_op.create_check_constraint(
            "ck_users_leetcode_experience",
            "leetcode_experience IS NULL OR leetcode_experience IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
        )
        batch_op.create_check_constraint(
            "ck_users_weekly_problem_goal",
            "weekly_problem_goal IS NULL OR weekly_problem_goal BETWEEN 1 AND 100",
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_weekly_problem_goal", type_="check")
        batch_op.drop_constraint("ck_users_leetcode_experience", type_="check")
        batch_op.drop_constraint("ck_users_primary_goal", type_="check")
        batch_op.drop_column("onboarding_completed_at")
        batch_op.drop_column("weekly_problem_goal")
        batch_op.drop_column("leetcode_experience")
        batch_op.drop_column("primary_goal")
