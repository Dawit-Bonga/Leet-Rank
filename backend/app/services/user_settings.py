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
    neetcode_accepted_only_confirmed: bool | None = None,
) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise SettingsUserNotFoundError("LeetClimb user does not exist.")

    next_repo_owner = user.neetcode_repo_owner
    next_repo_name = user.neetcode_repo_name
    if neetcode_repo_owner is not None:
        next_repo_owner = neetcode_repo_owner.strip()
    if neetcode_repo_name is not None:
        next_repo_name = neetcode_repo_name.strip()
    if (next_repo_owner is None) != (next_repo_name is None):
        raise InvalidSettingsError(
            "NeetCode repository owner and name must be provided together."
        )
    repository_changed = (
        next_repo_owner != user.neetcode_repo_owner
        or next_repo_name != user.neetcode_repo_name
    )
    if repository_changed and next_repo_owner and not neetcode_accepted_only_confirmed:
        raise InvalidSettingsError(
            "Confirm that NeetCode GitHub Sync is configured for accepted submissions only."
        )

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
    user.neetcode_repo_owner = next_repo_owner
    user.neetcode_repo_name = next_repo_name
    if submission_source is not None:
        user.submission_source = submission_source

    session.commit()
    session.refresh(user)
    return user
