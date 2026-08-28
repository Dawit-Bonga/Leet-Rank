from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Problem, User, UserSyncState
from app.services.automatic_sync import sync_due_users
from app.services.neetcode_sync import NEETCODE_PROVIDER, NeetCodeSubmissionEvent
from app.services.leetcode import UpstreamUnavailableError


class BatchProvider:
    def __init__(self, failing_usernames: set[str] | None = None) -> None:
        self.failing_usernames = failing_usernames or set()
        self.requested_usernames: list[str] = []

    def get_accepted_submissions(self, username: str, limit: int = 20):
        self.requested_usernames.append(username)
        if username in self.failing_usernames:
            raise UpstreamUnavailableError(f"Could not sync {username}.")
        return []

    def get_problem(self, title_slug: str):
        raise AssertionError("No problem lookup is expected for an empty submission list.")


class FakeNeetCodeProvider:
    provider_name = NEETCODE_PROVIDER

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def get_recent_accepted_submissions(self, *, owner: str, repo: str, limit: int = 100):
        self.calls.append((owner, repo, limit))
        return [
            NeetCodeSubmissionEvent(
                provider_submission_id=f"github:{owner}/{repo}:abc:neetcode/two-sum/submission.py",
                problem_slug="two-sum",
                problem_title="Two Sum",
                submitted_at=datetime(2026, 1, 2, 12, tzinfo=UTC),
                repository=f"{owner}/{repo}",
                commit_sha="abc",
                file_path="neetcode/two-sum/submission.py",
            )
        ]


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_account(
    session: Session,
    *,
    username: str,
    status: str = "IDLE",
    last_attempted_at: datetime | None = None,
) -> User:
    user = User(
        username=username,
        leetcode_username=f"{username}-lc",
        display_name=username.title(),
        scoring_started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    session.add(user)
    session.flush()
    session.add(
        UserSyncState(
            user_id=user.id,
            sync_status=status,
            last_attempted_at=last_attempted_at,
        )
    )
    session.commit()
    return user


def test_batch_syncs_new_and_due_accounts_but_skips_fresh_accounts():
    now = datetime(2026, 1, 2, 12, tzinfo=UTC)
    with make_session() as session:
        new_user = add_account(session, username="new-user")
        due_user = add_account(
            session,
            username="due-user",
            status="SUCCEEDED",
            last_attempted_at=now - timedelta(minutes=16),
        )
        fresh_user = add_account(
            session,
            username="fresh-user",
            status="SUCCEEDED",
            last_attempted_at=now - timedelta(minutes=5),
        )
        provider = BatchProvider()

        result = sync_due_users(session, provider, now=now)

        assert result.attempted == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert set(provider.requested_usernames) == {"new-user-lc", "due-user-lc"}
        assert session.get(UserSyncState, new_user.id).last_successful_at.replace(tzinfo=UTC) == now
        assert session.get(UserSyncState, due_user.id).last_successful_at.replace(tzinfo=UTC) == now
        assert session.get(UserSyncState, fresh_user.id).last_successful_at is None


def test_one_user_failure_is_recorded_without_stopping_the_batch():
    now = datetime(2026, 1, 2, 12, tzinfo=UTC)
    with make_session() as session:
        failed_user = add_account(session, username="broken")
        successful_user = add_account(session, username="working")
        provider = BatchProvider({"broken-lc"})

        result = sync_due_users(session, provider, now=now)

        assert result.attempted == 2
        assert result.succeeded == 1
        assert result.failed == 1
        assert result.failures[0].user_id == failed_user.id
        assert result.failures[0].username == "broken"
        assert set(provider.requested_usernames) == {"broken-lc", "working-lc"}
        assert session.get(UserSyncState, failed_user.id).sync_status == "FAILED"
        assert session.get(UserSyncState, successful_user.id).sync_status == "SUCCEEDED"


def test_stale_running_account_is_recovered_and_synced():
    now = datetime(2026, 1, 2, 12, tzinfo=UTC)
    with make_session() as session:
        user = add_account(
            session,
            username="stale",
            status="RUNNING",
            last_attempted_at=now - timedelta(minutes=31),
        )

        result = sync_due_users(session, BatchProvider(), now=now)

        assert result.succeeded == 1
        state = session.get(UserSyncState, user.id)
        assert state.sync_status == "SUCCEEDED"
        assert state.last_successful_at.replace(tzinfo=UTC) == now


def test_batch_size_limits_each_run():
    now = datetime(2026, 1, 2, 12, tzinfo=UTC)
    with make_session() as session:
        add_account(session, username="alice")
        add_account(session, username="bob")
        provider = BatchProvider()

        result = sync_due_users(session, provider, now=now, batch_size=1)

        assert result.attempted == 1
        assert len(provider.requested_usernames) == 1


def test_batch_runs_optional_neetcode_sync_when_repo_is_configured():
    now = datetime(2026, 1, 2, 12, tzinfo=UTC)
    with make_session() as session:
        with_repo = add_account(session, username="withrepo")
        with_repo.neetcode_repo_owner = "Dawit-Bonga"
        with_repo.neetcode_repo_name = "neetcode-submissions"
        session.add(Problem(leetcode_slug="two-sum", title="Two Sum", difficulty="EASY"))
        session.commit()

        provider = BatchProvider()
        neetcode_provider = FakeNeetCodeProvider()
        result = sync_due_users(
            session,
            provider,
            neetcode_provider=neetcode_provider,
            now=now,
        )

        assert result.attempted == 1
        assert result.succeeded == 1
        assert neetcode_provider.calls == [("Dawit-Bonga", "neetcode-submissions", 100)]
