from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import ScoreEvent, Submission, User, UserProblemStats
from app.services.submission_sync import AcceptedSubmission, ProblemDetails, ingest_submission


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_user(session: Session, scoring_started_at: datetime) -> User:
    user = User(
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
