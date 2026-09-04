from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import User
from app.services.user_settings import (
    InvalidSettingsError,
    SettingsUserNotFoundError,
    update_user_settings,
)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_user(session: Session) -> User:
    user = User(
        username="alice",
        leetcode_username="alice-lc",
        display_name="Alice",
        primary_goal="CONSISTENCY",
        leetcode_experience="INTERMEDIATE",
        weekly_problem_goal=5,
        scoring_started_at=datetime(2026, 8, 18, tzinfo=UTC),
    )
    session.add(user)
    session.commit()
    return user


def test_updates_only_requested_profile_settings():
    with make_session() as session:
        user = add_user(session)

        updated = update_user_settings(
            session,
            user_id=user.id,
            display_name="  Alice A.  ",
            weekly_problem_goal=8,
        )

        assert updated.display_name == "Alice A."
        assert updated.weekly_problem_goal == 8
        assert updated.primary_goal == "CONSISTENCY"
        assert updated.leetcode_experience == "INTERMEDIATE"
        assert updated.username == "alice"
        assert updated.leetcode_username == "alice-lc"
        assert updated.submission_source == "leetcode"


def test_rejects_blank_display_name_and_missing_user():
    with make_session() as session:
        user = add_user(session)

        with pytest.raises(InvalidSettingsError):
            update_user_settings(session, user_id=user.id, display_name="   ")
        with pytest.raises(SettingsUserNotFoundError):
            update_user_settings(
                session,
                user_id=uuid4(),
                weekly_problem_goal=10,
            )


def test_neetcode_repo_requires_owner_and_name_together():
    with make_session() as session:
        user = add_user(session)

        with pytest.raises(InvalidSettingsError):
            update_user_settings(
                session,
                user_id=user.id,
                neetcode_repo_owner="Dawit-Bonga",
            )

        updated = update_user_settings(
            session,
            user_id=user.id,
            neetcode_repo_owner="Dawit-Bonga",
            neetcode_repo_name="neetcode-submissions",
            neetcode_accepted_only_confirmed=True,
        )
        assert updated.neetcode_repo_owner == "Dawit-Bonga"
        assert updated.neetcode_repo_name == "neetcode-submissions"


def test_neetcode_repo_change_requires_accepted_only_confirmation():
    with make_session() as session:
        user = add_user(session)

        with pytest.raises(InvalidSettingsError, match="accepted submissions only"):
            update_user_settings(
                session,
                user_id=user.id,
                neetcode_repo_owner="alice-github",
                neetcode_repo_name="neetcode-solutions",
            )

        assert user.neetcode_repo_owner is None
        assert user.neetcode_repo_name is None
