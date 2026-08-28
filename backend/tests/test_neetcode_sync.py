from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Problem, ScoreEvent, Submission, UnmappedSubmission, User, UserSyncState
from app.services.leetcode import AcceptedSubmission, ProblemDetails
from app.services.neetcode_sync import (
    NEETCODE_PROVIDER,
    NeetCodeSubmissionEvent,
    sync_user_neetcode_submissions,
)
from app.services.problem_resolution import retry_unmapped_submissions
from app.services.submission_sync import ingest_submission


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_user(session: Session, scoring_started_at: datetime) -> User:
    user = User(
        username="alice",
        leetcode_username="alice-lc",
        display_name="Alice",
        primary_goal="CONSISTENCY",
        leetcode_experience="INTERMEDIATE",
        weekly_problem_goal=5,
        scoring_started_at=scoring_started_at,
        submission_source="github_neetcode",
        neetcode_repo_owner="Dawit-Bonga",
        neetcode_repo_name="neetcode-submissions",
    )
    session.add(user)
    session.commit()
    return user


class FakeNeetCodeProvider:
    provider_name = NEETCODE_PROVIDER

    def __init__(self, events=None, error: Exception | None = None):
        self.events = events or []
        self.error = error
        self.calls: list[tuple[str, str, int]] = []

    def get_recent_accepted_submissions(self, *, owner: str, repo: str, limit: int = 100):
        self.calls.append((owner, repo, limit))
        if self.error is not None:
            raise self.error
        return list(self.events)


def _event(event_id: str, slug: str, submitted_at: datetime) -> NeetCodeSubmissionEvent:
    return NeetCodeSubmissionEvent(
        provider_submission_id=event_id,
        problem_slug=slug,
        problem_title=slug.replace("-", " ").title(),
        submitted_at=submitted_at,
        repository="Dawit-Bonga/neetcode-submissions",
        commit_sha=event_id.split(":")[2] if ":" in event_id else event_id,
        file_path=f"neetcode/{slug}/submission.py",
    )


def test_neetcode_sync_dedupes_and_avoids_double_first_solve_points():
    with make_session() as session:
        signup = datetime(2026, 8, 1, tzinfo=UTC)
        user = add_user(session, signup)
        session.add(Problem(leetcode_slug="two-sum", title="Two Sum", difficulty="EASY"))
        session.commit()

        ingest_submission(
            session,
            user_id=user.id,
            submission=AcceptedSubmission(
                external_id="leetcode:1",
                problem_slug="two-sum",
                problem_title="Two Sum",
                submitted_at=signup + timedelta(minutes=1),
            ),
            problem_details=ProblemDetails(slug="two-sum", title="Two Sum", difficulty="EASY"),
            provider="leetcode",
            provider_submission_id="leetcode:1",
        )

        event_id = "github:Dawit-Bonga/neetcode-submissions:abc123:neetcode/two-sum/submission.py"
        provider = FakeNeetCodeProvider(
            [
                _event(event_id, "two-sum", signup + timedelta(days=1)),
                _event(event_id, "two-sum", signup + timedelta(days=1)),
            ]
        )

        result = sync_user_neetcode_submissions(session, provider, user_id=user.id)

        assert result.status == "SUCCEEDED"
        assert result.fetched == 2
        assert result.new_submissions == 1
        assert result.duplicate_submissions == 1
        assert result.points_awarded == 0
        assert session.scalar(select(func.count()).select_from(Submission)) == 2
        reasons = [row[0] for row in session.execute(select(ScoreEvent.reason)).all()]
        assert reasons.count("FIRST_SOLVE") == 1
        assert session.get(UserSyncState, user.id).sync_status == "SUCCEEDED"


def test_unmapped_neetcode_events_are_queued_and_retryable():
    with make_session() as session:
        signup = datetime(2026, 8, 1, tzinfo=UTC)
        user = add_user(session, signup)
        missing_slug = "totally-new-problem"
        event_id = "github:Dawit-Bonga/neetcode-submissions:def456:neetcode/totally-new-problem/submission.py"
        provider = FakeNeetCodeProvider([_event(event_id, missing_slug, signup + timedelta(hours=1))])

        result = sync_user_neetcode_submissions(session, provider, user_id=user.id)

        assert result.unmapped_submissions == 1
        queued = session.scalar(select(UnmappedSubmission))
        assert queued is not None
        assert queued.provider == NEETCODE_PROVIDER
        assert queued.provider_submission_id == event_id
        assert queued.resolved_at is None

        session.add(Problem(leetcode_slug=missing_slug, title="Totally New Problem", difficulty="MEDIUM"))
        session.commit()
        resolved = retry_unmapped_submissions(session, limit=10)

        assert resolved == 1
        resolved_row = session.get(UnmappedSubmission, queued.id)
        assert resolved_row is not None
        assert resolved_row.resolved_at is not None
        inserted = session.scalar(
            select(Submission).where(
                Submission.provider == NEETCODE_PROVIDER,
                Submission.provider_submission_id == event_id,
            )
        )
        assert inserted is not None


def test_neetcode_provider_failure_marks_sync_failed():
    with make_session() as session:
        signup = datetime(2026, 8, 1, tzinfo=UTC)
        user = add_user(session, signup)
        provider = FakeNeetCodeProvider(error=RuntimeError("GitHub unavailable"))

        with pytest.raises(RuntimeError):
            sync_user_neetcode_submissions(session, provider, user_id=user.id)

        state = session.get(UserSyncState, user.id)
        assert state is not None
        assert state.sync_status == "FAILED"
        assert state.last_error == "GitHub unavailable"
