"""Add LeetRank usernames and pending friend requests."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_friendships"
down_revision: str | Sequence[str] | None = "0002_user_onboarding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(30)))

    op.execute("UPDATE users SET username = lower(leetcode_username)")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("username", existing_type=sa.String(30), nullable=False)
        batch_op.create_unique_constraint("uq_users_username", ["username"])
        batch_op.create_check_constraint(
            "ck_users_username_length", "length(username) BETWEEN 3 AND 30"
        )
        batch_op.create_check_constraint(
            "ck_users_username_lowercase", "username = lower(username)"
        )

    op.create_table(
        "friend_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "requester_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "addressee_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "requester_id", "addressee_id", name="uq_friend_requests_direction"
        ),
        sa.CheckConstraint(
            "requester_id <> addressee_id", name="ck_friend_requests_not_self"
        ),
    )
    op.create_index(
        "ix_friend_requests_addressee_created_at",
        "friend_requests",
        ["addressee_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_friend_requests_addressee_created_at", table_name="friend_requests"
    )
    op.drop_table("friend_requests")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_username_lowercase", type_="check")
        batch_op.drop_constraint("ck_users_username_length", type_="check")
        batch_op.drop_constraint("uq_users_username", type_="unique")
        batch_op.drop_column("username")
