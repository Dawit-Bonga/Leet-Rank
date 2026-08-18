from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Friendship, User
from app.services.score_reads import (
    UserActivityResult,
    UserScoresResult,
    get_user_activity,
    get_user_scores,
)


FRIEND_PROFILE_ACTIVITY_LIMIT = 100


class FriendProfileNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class FriendProfileResult:
    user: User
    friend_since: datetime
    scores: UserScoresResult
    activity: UserActivityResult


def get_friend_profile(
    session: Session,
    *,
    viewer_id: UUID,
    friend_id: UUID,
    as_of: datetime | None = None,
) -> FriendProfileResult:
    friendship = session.get(Friendship, (viewer_id, friend_id))
    friend = session.get(User, friend_id) if friendship is not None else None
    if friend is None or friendship is None:
        # Use the same response for missing users and non-friends so this endpoint
        # cannot be used to discover private LeetRank accounts.
        raise FriendProfileNotFoundError("Friend profile does not exist.")

    calculated_at = as_of or datetime.now(UTC)
    return FriendProfileResult(
        user=friend,
        friend_since=friendship.created_at,
        scores=get_user_scores(session, user_id=friend.id, as_of=calculated_at),
        activity=get_user_activity(
            session,
            user_id=friend.id,
            limit=FRIEND_PROFILE_ACTIVITY_LIMIT,
        ),
    )
