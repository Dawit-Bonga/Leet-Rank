"""Add NeetCode provider integration schema."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_neetcode_integration"
down_revision: str | Sequence[str] | None = "0004_lock_down_data_api"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("submission_source", sa.String(length=32), server_default="leetcode")
        )
        batch_op.add_column(sa.Column("neetcode_repo_owner", sa.String(length=100)))
        batch_op.add_column(sa.Column("neetcode_repo_name", sa.String(length=100)))
    op.execute("UPDATE users SET submission_source = 'leetcode' WHERE submission_source IS NULL")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("submission_source", existing_type=sa.String(length=32), nullable=False)
        batch_op.create_check_constraint(
            "ck_users_submission_source",
            "submission_source IN ('leetcode', 'github_neetcode')",
        )
        batch_op.create_check_constraint(
            "ck_users_neetcode_repo_pair",
            "(neetcode_repo_owner IS NULL AND neetcode_repo_name IS NULL) "
            "OR (neetcode_repo_owner IS NOT NULL AND neetcode_repo_name IS NOT NULL)",
        )

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.add_column(sa.Column("provider", sa.String(length=32), server_default="leetcode"))
        batch_op.add_column(sa.Column("provider_submission_id", sa.String(length=255)))
    op.execute("UPDATE submissions SET provider = 'leetcode' WHERE provider IS NULL")
    op.execute(
        "UPDATE submissions SET provider_submission_id = external_submission_id "
        "WHERE provider_submission_id IS NULL"
    )
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.alter_column("provider", existing_type=sa.String(length=32), nullable=False)
        batch_op.alter_column(
            "provider_submission_id", existing_type=sa.String(length=255), nullable=False
        )
        batch_op.create_check_constraint(
            "ck_submissions_provider",
            "provider IN ('leetcode', 'github_neetcode')",
        )
        batch_op.create_unique_constraint(
            "uq_submissions_provider_event",
            ["provider", "provider_submission_id"],
        )
        batch_op.create_index(
            "ix_submissions_provider_event",
            ["provider", "provider_submission_id"],
        )
        batch_op.drop_constraint("uq_submissions_user_external_id", type_="unique")

    op.create_table(
        "unmapped_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_submission_id", sa.String(length=255), nullable=False),
        sa.Column("problem_slug", sa.String(length=255), nullable=False),
        sa.Column("problem_title", sa.String(length=255), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.String(length=4000)),
        sa.Column("last_error", sa.String(length=500)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "provider IN ('leetcode', 'github_neetcode')",
            name="ck_unmapped_submissions_provider",
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_submission_id",
            name="uq_unmapped_submissions_provider_event",
        ),
    )
    op.create_index("ix_unmapped_submissions_created_at", "unmapped_submissions", ["created_at"])

    op.execute('ALTER TABLE public."unmapped_submissions" ENABLE ROW LEVEL SECURITY')
    op.execute(
        'REVOKE ALL PRIVILEGES ON TABLE public."unmapped_submissions" '
        "FROM anon, authenticated"
    )


def downgrade() -> None:
    op.execute(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public."unmapped_submissions" '
        "TO anon, authenticated"
    )
    op.execute('ALTER TABLE public."unmapped_submissions" DISABLE ROW LEVEL SECURITY')
    op.drop_index("ix_unmapped_submissions_created_at", table_name="unmapped_submissions")
    op.drop_table("unmapped_submissions")

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.create_unique_constraint(
            "uq_submissions_user_external_id",
            ["user_id", "external_submission_id"],
        )
        batch_op.drop_index("ix_submissions_provider_event")
        batch_op.drop_constraint("uq_submissions_provider_event", type_="unique")
        batch_op.drop_constraint("ck_submissions_provider", type_="check")
        batch_op.drop_column("provider_submission_id")
        batch_op.drop_column("provider")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_neetcode_repo_pair", type_="check")
        batch_op.drop_constraint("ck_users_submission_source", type_="check")
        batch_op.drop_column("neetcode_repo_name")
        batch_op.drop_column("neetcode_repo_owner")
        batch_op.drop_column("submission_source")
