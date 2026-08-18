from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User, UserSyncState
from app.services.leetcode import LeetCodeUser


class LeetCodeUserProvider(Protocol):
    def get_user(self, username: str) -> LeetCodeUser: ...


class LeetCodeUsernameTakenError(Exception):
    pass


def create_onboarded_user(
    session: Session,
    provider: LeetCodeUserProvider,
    *,
    display_name: str,
    leetcode_username: str,
    primary_goal: str,
    leetcode_experience: str,
    weekly_problem_goal: int,
    now: datetime | None = None,
) -> tuple[User, UserSyncState]:
    normalized_input = leetcode_username.strip().lower()
    if not normalized_input:
        raise ValueError("LeetCode username cannot be blank.")

    duplicate = session.scalar(
        select(User).where(func.lower(User.leetcode_username) == normalized_input)
    )
    if duplicate is not None:
        raise LeetCodeUsernameTakenError("That LeetCode account is already connected to LeetRank.")

    leetcode_user = provider.get_user(normalized_input)
    canonical_username = leetcode_user.username.strip().lower()
    if not canonical_username:
        raise ValueError("LeetCode provider returned a blank username.")

    duplicate = session.scalar(
        select(User).where(func.lower(User.leetcode_username) == canonical_username)
    )
    if duplicate is not None:
        raise LeetCodeUsernameTakenError("That LeetCode account is already connected to LeetRank.")

    scoring_start = now or datetime.now(UTC)
    if scoring_start.tzinfo is None:
        scoring_start = scoring_start.replace(tzinfo=UTC)

    user = User(
        leetcode_username=canonical_username,
        display_name=display_name.strip(),
        primary_goal=primary_goal,
        leetcode_experience=leetcode_experience,
        weekly_problem_goal=weekly_problem_goal,
        scoring_started_at=scoring_start,
        onboarding_completed_at=scoring_start,
    )
    sync_state = UserSyncState(user_id=user.id, sync_status="IDLE")

    try:
        session.add(user)
        session.flush()
        sync_state.user_id = user.id
        session.add(sync_state)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise LeetCodeUsernameTakenError(
            "That LeetCode account is already connected to LeetRank."
        ) from exc

    session.refresh(user)
    return user, sync_state
