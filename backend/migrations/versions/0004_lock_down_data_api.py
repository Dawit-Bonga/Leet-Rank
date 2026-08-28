"""Lock LeetClimb tables behind the FastAPI data-access boundary."""

from collections.abc import Sequence

from alembic import op


revision: str = "0004_lock_down_data_api"
down_revision: str | Sequence[str] | None = "0003_friendships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


APPLICATION_TABLES = (
    "users",
    "problems",
    "submissions",
    "user_problem_stats",
    "score_events",
    "user_sync_state",
    "friend_requests",
    "friendships",
)


def upgrade() -> None:
    for table_name in APPLICATION_TABLES:
        op.execute(
            f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY'
        )
        op.execute(
            f'REVOKE ALL PRIVILEGES ON TABLE public."{table_name}" '
            "FROM anon, authenticated"
        )

    # Alembic creates tables as the postgres role. Remove the Supabase Data API
    # roles from that role's defaults so later application tables stay private
    # until a migration intentionally grants access.
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON TABLES FROM anon, authenticated"
    )


def downgrade() -> None:
    # This restores Supabase's traditional public-schema DML grants. Running
    # this downgrade intentionally reopens direct Data API access.
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO anon, authenticated"
    )
    for table_name in reversed(APPLICATION_TABLES):
        op.execute(
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public."{table_name}" '
            "TO anon, authenticated"
        )
        op.execute(
            f'ALTER TABLE public."{table_name}" DISABLE ROW LEVEL SECURITY'
        )
