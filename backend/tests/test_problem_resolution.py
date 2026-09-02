from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Problem, Submission, UnmappedSubmission, User
from app.services.problem_resolution import (
    canonical_problem_slug,
    queue_unmapped_submission,
    retry_unmapped_submissions,
)


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
    )
    session.add(user)
    session.commit()
    return user


def test_confirmed_neetcode_aliases_use_canonical_leetcode_slugs():
    assert canonical_problem_slug("rotting-fruit") == "rotting-oranges"
    assert canonical_problem_slug("Duplicate Integer") == "contains-duplicate"
    assert canonical_problem_slug("two_sum") == "two-sum"


def test_retry_resolves_queued_submission_after_alias_is_added():
    with make_session() as session:
        signup = datetime(2026, 9, 1, tzinfo=UTC)
        user = add_user(session, signup)
        problem = Problem(
            leetcode_slug="rotting-oranges",
            title="Rotting Oranges",
            difficulty="MEDIUM",
        )
        session.add(problem)
        session.commit()

        provider_submission_id = (
            "github:alice/neetcode-solutions:commit123:"
            "Data Structures & Algorithms/rotting-fruit/submission-5.py"
        )
        queue_unmapped_submission(
            session,
            user_id=user.id,
            provider="github_neetcode",
            provider_submission_id=provider_submission_id,
            problem_slug="rotting-fruit",
            problem_title="Rotting Fruit",
            submitted_at=signup + timedelta(hours=1),
        )

        assert retry_unmapped_submissions(session, user_id=user.id) == 1

        queued = session.scalar(select(UnmappedSubmission))
        submission = session.scalar(select(Submission))
        assert queued is not None
        assert queued.resolved_at is not None
        assert submission is not None
        assert submission.problem_id == problem.id
