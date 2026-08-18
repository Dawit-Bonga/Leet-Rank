from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Problem, ScoreEvent, Submission, User
from app.services.score_reads import ScoreUserNotFoundError, get_user_activity, get_user_scores


AS_OF = datetime(2026, 8, 18, 20, 0, tzinfo=UTC)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_scored_event(session, user, problem, *, external_id, earned_at, points, reason):
    submission = Submission(
        user_id=user.id,
        problem_id=problem.id,
        external_submission_id=external_id,
        submitted_at=earned_at,
    )
    session.add(submission)
    session.flush()
    session.add(
        ScoreEvent(
            user_id=user.id,
            problem_id=problem.id,
            submission_id=submission.id,
            points=points,
            reason=reason,
            earned_at=earned_at,
        )
    )


def seed_scores(session):
    user = User(
        leetcode_username="alice",
        display_name="Alice",
        scoring_started_at=AS_OF - timedelta(days=60),
    )
    problem = Problem(leetcode_slug="two-sum", title="Two Sum", difficulty="EASY")
    session.add_all([user, problem])
    session.flush()
    add_scored_event(
        session,
        user,
        problem,
        external_id="old",
        earned_at=AS_OF - timedelta(days=40),
        points=30,
        reason="FIRST_SOLVE",
    )
    add_scored_event(
        session,
        user,
        problem,
        external_id="month",
        earned_at=AS_OF - timedelta(days=20),
        points=20,
        reason="REVIEW",
    )
    add_scored_event(
        session,
        user,
        problem,
        external_id="week",
        earned_at=AS_OF - timedelta(days=2),
        points=10,
        reason="REVIEW",
    )
    add_scored_event(
        session,
        user,
        problem,
        external_id="cooldown",
        earned_at=AS_OF - timedelta(days=1),
        points=0,
        reason="COOLDOWN",
    )
    session.commit()
    return user


def test_score_snapshot_returns_all_periods_with_one_as_of():
    with make_session() as session:
        user = seed_scores(session)

        result = get_user_scores(session, user_id=user.id, as_of=AS_OF)

        assert result.as_of == AS_OF
        assert result.week.points == 10
        assert result.week.starts_at == AS_OF - timedelta(days=7)
        assert result.month.points == 30
        assert result.month.starts_at == AS_OF - timedelta(days=30)
        assert result.all_time.points == 60
        assert result.all_time.starts_at == AS_OF - timedelta(days=60)


def test_activity_is_newest_first_includes_zero_points_and_paginates():
    with make_session() as session:
        user = seed_scores(session)

        first_page = get_user_activity(session, user_id=user.id, limit=2)
        second_page = get_user_activity(session, user_id=user.id, limit=2, offset=2)

        assert [item.reason for item in first_page.items] == ["COOLDOWN", "REVIEW"]
        assert first_page.items[0].points == 0
        assert first_page.has_more is True
        assert len(second_page.items) == 2
        assert second_page.has_more is False


def test_score_snapshot_excludes_events_after_as_of():
    with make_session() as session:
        user = seed_scores(session)
        problem = session.query(Problem).filter_by(leetcode_slug="two-sum").one()
        add_scored_event(
            session,
            user,
            problem,
            external_id="future",
            earned_at=AS_OF + timedelta(minutes=1),
            points=100,
            reason="REVIEW",
        )
        session.commit()

        result = get_user_scores(session, user_id=user.id, as_of=AS_OF)

        assert result.week.points == 10
        assert result.month.points == 30
        assert result.all_time.points == 60


def test_score_reads_require_an_existing_user():
    from uuid import uuid4

    with make_session() as session:
        with pytest.raises(ScoreUserNotFoundError):
            get_user_scores(session, user_id=uuid4(), as_of=AS_OF)
