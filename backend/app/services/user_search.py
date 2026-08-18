from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import FriendRequest, Friendship, User
from app.services.friendships import FriendshipUserNotFoundError


USER_SEARCH_LIMIT = 10


@dataclass(frozen=True)
class UserSearchResult:
    user: User
    relationship: str
    friend_request_id: UUID | None


def search_users(
    session: Session,
    *,
    user_id: UUID,
    username_prefix: str,
    limit: int = USER_SEARCH_LIMIT,
) -> list[UserSearchResult]:
    if session.get(User, user_id) is None:
        raise FriendshipUserNotFoundError("User does not exist.")
    if limit < 1 or limit > USER_SEARCH_LIMIT:
        raise ValueError(f"Search limit must be between 1 and {USER_SEARCH_LIMIT}.")

    normalized_prefix = username_prefix.strip().lower()
    if not normalized_prefix:
        return []

    users = list(
        session.scalars(
            select(User)
            .where(
                User.id != user_id,
                User.username.startswith(normalized_prefix, autoescape=True),
            )
            .order_by(User.username)
            .limit(limit)
        ).all()
    )
    if not users:
        return []

    candidate_ids = [user.id for user in users]
    friend_ids = set(
        session.scalars(
            select(Friendship.friend_id).where(
                Friendship.user_id == user_id,
                Friendship.friend_id.in_(candidate_ids),
            )
        ).all()
    )
    requests = list(
        session.scalars(
            select(FriendRequest).where(
                or_(
                    and_(
                        FriendRequest.requester_id == user_id,
                        FriendRequest.addressee_id.in_(candidate_ids),
                    ),
                    and_(
                        FriendRequest.addressee_id == user_id,
                        FriendRequest.requester_id.in_(candidate_ids),
                    ),
                )
            )
        ).all()
    )
    request_by_user: dict[UUID, FriendRequest] = {}
    for request in requests:
        other_id = (
            request.addressee_id if request.requester_id == user_id else request.requester_id
        )
        request_by_user[other_id] = request

    results: list[UserSearchResult] = []
    for user in users:
        request = request_by_user.get(user.id)
        if user.id in friend_ids:
            relationship = "FRIEND"
        elif request is not None and request.requester_id == user_id:
            relationship = "OUTGOING"
        elif request is not None:
            relationship = "INCOMING"
        else:
            relationship = "NONE"
        results.append(
            UserSearchResult(
                user=user,
                relationship=relationship,
                friend_request_id=request.id if request is not None else None,
            )
        )
    return results
