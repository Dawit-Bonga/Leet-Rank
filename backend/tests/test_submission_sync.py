from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import ScoreEvent, Submission, User, UserProblemStats, UserSyncState
from app.services.leetcode import UpstreamUnavailableError
from app.services.submission_sync import (
    AcceptedSubmission,
    ProblemDetails,
    SyncAlreadyRunningError,
    ingest_submission,
    sync_user_submissions,
)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_user(session: Session, scoring_started_at: datetime) -> User:
    user = User(
        username="alice",
        leetcode_username="alice",
        display_name="Alice",
        scoring_started_at=scoring_started_at,
    )
    session.add(user)
    session.commit()
    return user


def submission(external_id: str, submitted_at: datetime) -> AcceptedSubmission:
    return AcceptedSubmission(
        external_id=external_id,
        problem_slug="two-sum",
        problem_title="Two Sum",
        submitted_at=submitted_at,
    )


PROBLEM = ProblemDetails(slug="two-sum", title="Two Sum", difficulty="EASY")


class FakeSubmissionProvider:
    def __init__(self, submissions=None, error=None):
        self.submissions = submissions or []
        self.error = error
        self.problem_requests = []

    def get_accepted_submissions(self, username, limit=50):
        if self.error is not None:
            raise self.error
        return list(self.submissions)

    def get_problem(self, title_slug):
        self.problem_requests.append(title_slug)
        return PROBLEM


def test_pre_signup_submission_is_not_stored():
    with make_session() as session:
        signup = datetime(2026, 1, 2, tzinfo=UTC)
        user = add_user(session, signup)

        result = ingest_submission(
            session,
            user_id=user.id,
            submission=submission("old", signup - timedelta(seconds=1)),
            problem_details=PROBLEM,
        )

        assert result.status == "ignored_before_signup"
        assert session.scalar(select(func.count()).select_from(Submission)) == 0
        assert session.scalar(select(func.count()).select_from(ScoreEvent)) == 0


def test_submission_is_scored_once():
    with make_session() as session:
        signup = datetime(2026, 1, 2, tzinfo=UTC)
        user = add_user(session, signup)
        accepted = submission("123", signup + timedelta(minutes=1))

        first = ingest_submission(session, user_id=user.id, submission=accepted, problem_details=PROBLEM)
        second = ingest_submission(session, user_id=user.id, submission=accepted, problem_details=PROBLEM)

        assert (first.status, first.points, first.reason) == ("scored", 10, "FIRST_SOLVE")
        assert second.status == "duplicate"
        assert session.scalar(select(func.count()).select_from(Submission)) == 1
        assert session.scalar(select(func.count()).select_from(ScoreEvent)) == 1


def test_review_updates_stats_and_creates_audit_events():
    with make_session() as session:
        signup = datetime(2026, 1, 2, tzinfo=UTC)
        user = add_user(session, signup)
        first_time = signup + timedelta(minutes=1)

        ingest_submission(session, user_id=user.id, submission=submission("1", first_time), problem_details=PROBLEM)
        cooldown = ingest_submission(
            session,
            user_id=user.id,
            submission=submission("2", first_time + timedelta(days=1)),
            problem_details=PROBLEM,
        )
        review = ingest_submission(
            session,
            user_id=user.id,
            submission=submission("3", first_time + timedelta(days=7)),
            problem_details=PROBLEM,
        )

        stats = session.scalar(select(UserProblemStats))
        assert (cooldown.points, cooldown.reason) == (0, "COOLDOWN")
        assert (review.points, review.reason) == (3, "REVIEW")
        assert stats is not None
        assert stats.rewarded_solve_count == 2
        assert session.scalars(select(ScoreEvent)).all().__len__() == 3


def test_user_sync_filters_history_sorts_and_scores_new_submissions():
    with make_session() as session:
        signup = datetime(2026, 1, 2, tzinfo=UTC)
        user = add_user(session, signup)
        session.add(UserSyncState(user_id=user.id, sync_status="IDLE"))
        session.commit()
        provider = FakeSubmissionProvider(
            [
                submission("2", signup + timedelta(days=1)),
                submission("old", signup - timedelta(seconds=1)),
                submission("1", signup + timedelta(minutes=1)),
            ]
        )

        result = sync_user_submissions(session, provider, user_id=user.id)

        assert result.status == "SUCCEEDED"
        assert result.fetched == 3
        assert result.new_submissions == 2
        assert result.ignored_before_signup == 1
        assert result.points_awarded == 10
        assert provider.problem_requests == ["two-sum"]
        assert session.get(UserSyncState, user.id).sync_status == "SUCCEEDED"

        repeated = sync_user_submissions(session, provider, user_id=user.id)
        assert repeated.duplicate_submissions == 2
        assert repeated.new_submissions == 0
        assert repeated.points_awarded == 0
        assert provider.problem_requests == ["two-sum"]


def test_user_sync_records_provider_failure():
    with make_session() as session:
        signup = datetime(2026, 1, 2, tzinfo=UTC)
        user = add_user(session, signup)
        session.add(UserSyncState(user_id=user.id, sync_status="IDLE"))
        session.commit()
        provider = FakeSubmissionProvider(error=UpstreamUnavailableError("Provider unavailable."))

        with pytest.raises(UpstreamUnavailableError):
            sync_user_submissions(session, provider, user_id=user.id)

        state = session.get(UserSyncState, user.id)
        assert state.sync_status == "FAILED"
        assert state.last_error == "Provider unavailable."


def test_user_sync_rejects_overlapping_run():
    with make_session() as session:
        signup = datetime(2026, 1, 2, tzinfo=UTC)
        user = add_user(session, signup)
        session.add(UserSyncState(user_id=user.id, sync_status="RUNNING"))
        session.commit()

        with pytest.raises(SyncAlreadyRunningError):
            sync_user_submissions(session, FakeSubmissionProvider(), user_id=user.id)
