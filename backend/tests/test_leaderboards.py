from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Friendship, Problem, ScoreEvent, Submission, User
from app.services.leaderboards import (
    LeaderboardUserNotFoundError,
    get_friends_leaderboard,
)


AS_OF = datetime(2026, 8, 18, 20, 0, tzinfo=UTC)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_user(session: Session, username: str) -> User:
    user = User(
        username=username,
        leetcode_username=f"{username}_lc",
        display_name=username.title(),
        scoring_started_at=AS_OF - timedelta(days=60),
    )
    session.add(user)
    session.flush()
    return user


def add_score(
    session: Session,
    user: User,
    problem: Problem,
    *,
    external_id: str,
    earned_at: datetime,
    points: int,
) -> None:
    submission = Submission(
        user_id=user.id,
        problem_id=problem.id,
        provider="leetcode",
        provider_submission_id=external_id,
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
            reason="FIRST_SOLVE",
            earned_at=earned_at,
        )
    )


def test_leaderboard_includes_self_all_friends_and_zero_scores():
    with make_session() as session:
        alice = add_user(session, "alice")
        bob = add_user(session, "bob")
        carol = add_user(session, "carol")
        stranger = add_user(session, "stranger")
        problem = Problem(leetcode_slug="two-sum", title="Two Sum", difficulty="EASY")
        session.add(problem)
        session.flush()
        session.add_all(
            [
                Friendship(user_id=alice.id, friend_id=bob.id),
                Friendship(user_id=bob.id, friend_id=alice.id),
                Friendship(user_id=alice.id, friend_id=carol.id),
                Friendship(user_id=carol.id, friend_id=alice.id),
            ]
        )
        add_score(
            session,
            alice,
            problem,
            external_id="alice-week",
            earned_at=AS_OF - timedelta(days=2),
            points=10,
        )
        add_score(
            session,
            alice,
            problem,
            external_id="alice-month",
            earned_at=AS_OF - timedelta(days=20),
            points=30,
        )
        add_score(
            session,
            bob,
            problem,
            external_id="bob-boundary",
            earned_at=AS_OF - timedelta(days=7),
            points=10,
        )
        add_score(
            session,
            stranger,
            problem,
            external_id="stranger-week",
            earned_at=AS_OF - timedelta(days=1),
            points=100,
        )
        session.commit()

        week = get_friends_leaderboard(
            session,
            user_id=alice.id,
            period="week",
            as_of=AS_OF,
        )
        month = get_friends_leaderboard(
            session,
            user_id=alice.id,
            period="month",
            as_of=AS_OF,
        )
        all_time = get_friends_leaderboard(
            session,
            user_id=alice.id,
            period="all_time",
            as_of=AS_OF,
        )

        assert [(entry.username, entry.points, entry.rank) for entry in week.entries] == [
            ("alice", 10, 1),
            ("bob", 10, 1),
            ("carol", 0, 3),
        ]
        assert [(entry.username, entry.points) for entry in month.entries] == [
            ("alice", 40),
            ("bob", 10),
            ("carol", 0),
        ]
        assert [(entry.username, entry.points) for entry in all_time.entries] == [
            ("alice", 40),
            ("bob", 10),
            ("carol", 0),
        ]
        assert week.entries[0].is_current_user is True
        assert week.entries[1].is_current_user is False
        assert week.starts_at == AS_OF - timedelta(days=7)
        assert all_time.starts_at is None
        assert all(entry.username != "stranger" for entry in week.entries)


def test_leaderboard_rejects_unknown_user_and_period():
    with make_session() as session:
        alice = add_user(session, "alice")
        session.commit()

        with pytest.raises(ValueError):
            get_friends_leaderboard(
                session,
                user_id=alice.id,
                period="year",
                as_of=AS_OF,
            )
        with pytest.raises(LeaderboardUserNotFoundError):
            get_friends_leaderboard(
                session,
                user_id=uuid4(),
                period="week",
                as_of=AS_OF,
            )
