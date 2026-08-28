from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import User


class SettingsUserNotFoundError(Exception):
    pass


class InvalidSettingsError(Exception):
    pass


def update_user_settings(
    session: Session,
    *,
    user_id: UUID,
    display_name: str | None = None,
    primary_goal: str | None = None,
    leetcode_experience: str | None = None,
    weekly_problem_goal: int | None = None,
    submission_source: str | None = None,
    neetcode_repo_owner: str | None = None,
    neetcode_repo_name: str | None = None,
) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise SettingsUserNotFoundError("LeetClimb user does not exist.")

    if display_name is not None:
        normalized_display_name = display_name.strip()
        if not normalized_display_name:
            raise InvalidSettingsError("Display name cannot be empty.")
        user.display_name = normalized_display_name
    if primary_goal is not None:
        user.primary_goal = primary_goal
    if leetcode_experience is not None:
        user.leetcode_experience = leetcode_experience
    if weekly_problem_goal is not None:
        user.weekly_problem_goal = weekly_problem_goal
    if neetcode_repo_owner is not None:
        user.neetcode_repo_owner = neetcode_repo_owner.strip()
    if neetcode_repo_name is not None:
        user.neetcode_repo_name = neetcode_repo_name.strip()
    if submission_source is not None:
        user.submission_source = submission_source

    if (user.neetcode_repo_owner is None) != (user.neetcode_repo_name is None):
        raise InvalidSettingsError(
            "NeetCode repository owner and name must be provided together."
        )
    session.commit()
    session.refresh(user)
    return user
