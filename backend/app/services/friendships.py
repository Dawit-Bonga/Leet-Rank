from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import FriendRequest, Friendship, User


FRIEND_LIMIT = 20


class FriendshipUserNotFoundError(Exception):
    pass


class CannotFriendSelfError(Exception):
    pass


class AlreadyFriendsError(Exception):
    pass


class FriendRequestAlreadyExistsError(Exception):
    pass


class FriendRequestNotFoundError(Exception):
    pass


class FriendRequestForbiddenError(Exception):
    pass


class FriendshipNotFoundError(Exception):
    pass


class FriendLimitReachedError(Exception):
    pass


@dataclass(frozen=True)
class FriendsOverviewResult:
    friends: list[User]
    incoming: list[tuple[FriendRequest, User]]
    outgoing: list[tuple[FriendRequest, User]]
    as_of: datetime


def create_friend_request(
    session: Session,
    *,
    requester_id: UUID,
    target_username: str,
) -> tuple[FriendRequest, User]:
    requester = session.get(User, requester_id)
    if requester is None:
        raise FriendshipUserNotFoundError("User does not exist.")

    normalized_username = target_username.strip().lower()
    target = session.scalar(select(User).where(User.username == normalized_username))
    if target is None:
        raise FriendshipUserNotFoundError("No LeetRank user has that username.")
    if target.id == requester.id:
        raise CannotFriendSelfError("You cannot send a friend request to yourself.")

    existing_friendship = session.get(Friendship, (requester.id, target.id))
    if existing_friendship is not None:
        raise AlreadyFriendsError("You are already friends with that user.")

    existing_request = session.scalar(
        select(FriendRequest).where(
            or_(
                and_(
                    FriendRequest.requester_id == requester.id,
                    FriendRequest.addressee_id == target.id,
                ),
                and_(
                    FriendRequest.requester_id == target.id,
                    FriendRequest.addressee_id == requester.id,
                ),
            )
        )
    )
    if existing_request is not None:
        raise FriendRequestAlreadyExistsError(
            "A friend request already exists between these users."
        )

    friend_request = FriendRequest(
        requester_id=requester.id,
        addressee_id=target.id,
    )
    try:
        session.add(friend_request)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise FriendRequestAlreadyExistsError(
            "A friend request already exists between these users."
        ) from exc

    session.refresh(friend_request)
    return friend_request, target


def list_friend_requests(
    session: Session,
    *,
    user_id: UUID,
) -> tuple[list[tuple[FriendRequest, User]], list[tuple[FriendRequest, User]]]:
    if session.get(User, user_id) is None:
        raise FriendshipUserNotFoundError("User does not exist.")

    incoming = list(
        session.execute(
            select(FriendRequest, User)
            .join(User, User.id == FriendRequest.requester_id)
            .where(FriendRequest.addressee_id == user_id)
            .order_by(FriendRequest.created_at.desc())
        ).all()
    )
    outgoing = list(
        session.execute(
            select(FriendRequest, User)
            .join(User, User.id == FriendRequest.addressee_id)
            .where(FriendRequest.requester_id == user_id)
            .order_by(FriendRequest.created_at.desc())
        ).all()
    )
    return incoming, outgoing


def accept_friend_request(
    session: Session,
    *,
    user_id: UUID,
    request_id: UUID,
) -> User:
    if session.get(User, user_id) is None:
        raise FriendshipUserNotFoundError("User does not exist.")

    friend_request = session.get(FriendRequest, request_id)
    if friend_request is None:
        raise FriendRequestNotFoundError("Friend request does not exist.")
    if friend_request.addressee_id != user_id:
        raise FriendRequestForbiddenError(
            "Only the recipient can accept this friend request."
        )

    friend = session.get(User, friend_request.requester_id)
    if friend is None:
        raise FriendshipUserNotFoundError("Requesting user does not exist.")

    # Lock both user rows in a consistent order so simultaneous acceptances
    # cannot push either account past the limit on PostgreSQL.
    session.execute(
        select(User.id)
        .where(User.id.in_([user_id, friend.id]))
        .order_by(User.id)
        .with_for_update()
    ).all()
    friend_counts = dict(
        session.execute(
            select(Friendship.user_id, func.count())
            .where(Friendship.user_id.in_([user_id, friend.id]))
            .group_by(Friendship.user_id)
        ).all()
    )
    limit_reached = any(
        friend_counts.get(account_id, 0) >= FRIEND_LIMIT
        for account_id in (user_id, friend.id)
    )
    if limit_reached:
        raise FriendLimitReachedError(
            "One of these users has reached the 20-friend limit."
        )

    session.add_all(
        [
            Friendship(user_id=user_id, friend_id=friend.id),
            Friendship(user_id=friend.id, friend_id=user_id),
        ]
    )
    session.delete(friend_request)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise AlreadyFriendsError("These users are already friends.") from exc
    return friend


def delete_friend_request(
    session: Session,
    *,
    user_id: UUID,
    request_id: UUID,
) -> None:
    if session.get(User, user_id) is None:
        raise FriendshipUserNotFoundError("User does not exist.")

    friend_request = session.get(FriendRequest, request_id)
    if friend_request is None:
        raise FriendRequestNotFoundError("Friend request does not exist.")
    if user_id not in (friend_request.requester_id, friend_request.addressee_id):
        raise FriendRequestForbiddenError(
            "Only the sender or recipient can delete this friend request."
        )

    session.delete(friend_request)
    session.commit()


def list_friends(session: Session, *, user_id: UUID) -> list[User]:
    if session.get(User, user_id) is None:
        raise FriendshipUserNotFoundError("User does not exist.")

    return list(
        session.scalars(
            select(User)
            .join(Friendship, Friendship.friend_id == User.id)
            .where(Friendship.user_id == user_id)
            .order_by(User.username)
        ).all()
    )


def get_friends_overview(
    session: Session,
    *,
    user_id: UUID,
) -> FriendsOverviewResult:
    friends = list_friends(session, user_id=user_id)
    incoming, outgoing = list_friend_requests(session, user_id=user_id)
    return FriendsOverviewResult(
        friends=friends,
        incoming=incoming,
        outgoing=outgoing,
        as_of=datetime.now(UTC),
    )


def remove_friend(
    session: Session,
    *,
    user_id: UUID,
    friend_id: UUID,
) -> None:
    if session.get(User, user_id) is None:
        raise FriendshipUserNotFoundError("User does not exist.")
    if session.get(Friendship, (user_id, friend_id)) is None:
        raise FriendshipNotFoundError("That user is not in your friends list.")

    session.execute(
        delete(Friendship).where(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id),
            )
        )
    )
    session.commit()
