from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import FriendRequest, Friendship, User
from app.services.friendships import (
    CannotFriendSelfError,
    FriendLimitReachedError,
    FriendRequestAlreadyExistsError,
    FriendRequestForbiddenError,
    accept_friend_request,
    create_friend_request,
    delete_friend_request,
    list_friend_requests,
    list_friends,
    remove_friend,
)
from app.services.user_search import search_users


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_user(session: Session, username: str) -> User:
    user = User(
        username=username,
        leetcode_username=f"{username}_lc",
        display_name=username.title(),
        scoring_started_at=datetime(2026, 8, 18, tzinfo=UTC),
    )
    session.add(user)
    session.commit()
    return user


def test_request_accept_list_and_remove_friendship():
    with make_session() as session:
        alice = add_user(session, "alice")
        bob = add_user(session, "bob")

        request, target = create_friend_request(
            session,
            requester_id=alice.id,
            target_username=" BOB ",
        )

        assert target.id == bob.id
        alice_incoming, alice_outgoing = list_friend_requests(session, user_id=alice.id)
        bob_incoming, bob_outgoing = list_friend_requests(session, user_id=bob.id)
        assert alice_incoming == []
        assert alice_outgoing[0][1].id == bob.id
        assert bob_incoming[0][1].id == alice.id
        assert bob_outgoing == []

        accepted_friend = accept_friend_request(
            session,
            user_id=bob.id,
            request_id=request.id,
        )

        assert accepted_friend.id == alice.id
        assert [friend.id for friend in list_friends(session, user_id=alice.id)] == [bob.id]
        assert [friend.id for friend in list_friends(session, user_id=bob.id)] == [alice.id]
        assert session.get(FriendRequest, request.id) is None
        assert session.get(Friendship, (alice.id, bob.id)) is not None
        assert session.get(Friendship, (bob.id, alice.id)) is not None

        remove_friend(session, user_id=alice.id, friend_id=bob.id)

        assert list_friends(session, user_id=alice.id) == []
        assert list_friends(session, user_id=bob.id) == []


def test_self_and_duplicate_requests_are_rejected():
    with make_session() as session:
        alice = add_user(session, "alice")
        bob = add_user(session, "bob")

        with pytest.raises(CannotFriendSelfError):
            create_friend_request(
                session,
                requester_id=alice.id,
                target_username="alice",
            )

        create_friend_request(
            session,
            requester_id=alice.id,
            target_username="bob",
        )
        with pytest.raises(FriendRequestAlreadyExistsError):
            create_friend_request(
                session,
                requester_id=bob.id,
                target_username="alice",
            )


def test_only_participants_can_accept_or_delete_request():
    with make_session() as session:
        alice = add_user(session, "alice")
        bob = add_user(session, "bob")
        carol = add_user(session, "carol")
        request, _ = create_friend_request(
            session,
            requester_id=alice.id,
            target_username="bob",
        )

        with pytest.raises(FriendRequestForbiddenError):
            accept_friend_request(
                session,
                user_id=carol.id,
                request_id=request.id,
            )
        with pytest.raises(FriendRequestForbiddenError):
            delete_friend_request(
                session,
                user_id=carol.id,
                request_id=request.id,
            )

        delete_friend_request(session, user_id=bob.id, request_id=request.id)
        assert session.get(FriendRequest, request.id) is None


def test_acceptance_is_rejected_when_either_user_has_twenty_friends():
    with make_session() as session:
        alice = add_user(session, "alice")
        bob = add_user(session, "bob")
        for index in range(20):
            existing_friend = add_user(session, f"f{index:02d}")
            session.add_all(
                [
                    Friendship(user_id=bob.id, friend_id=existing_friend.id),
                    Friendship(user_id=existing_friend.id, friend_id=bob.id),
                ]
            )
        session.commit()
        request, _ = create_friend_request(
            session,
            requester_id=alice.id,
            target_username="bob",
        )

        with pytest.raises(FriendLimitReachedError):
            accept_friend_request(
                session,
                user_id=bob.id,
                request_id=request.id,
            )

        assert session.get(FriendRequest, request.id) is not None
        assert session.get(Friendship, (alice.id, bob.id)) is None


def test_user_search_returns_prefix_matches_with_relationship_state():
    with make_session() as session:
        dawit = add_user(session, "dawit")
        david = add_user(session, "david")
        davina = add_user(session, "davina")
        davy = add_user(session, "davy")
        add_user(session, "alice")

        session.add_all(
            [
                Friendship(user_id=dawit.id, friend_id=david.id),
                Friendship(user_id=david.id, friend_id=dawit.id),
                FriendRequest(requester_id=dawit.id, addressee_id=davina.id),
                FriendRequest(requester_id=davy.id, addressee_id=dawit.id),
            ]
        )
        session.commit()

        results = search_users(session, user_id=dawit.id, username_prefix=" DAV ")

        assert [(result.user.username, result.relationship) for result in results] == [
            ("david", "FRIEND"),
            ("davina", "OUTGOING"),
            ("davy", "INCOMING"),
        ]
        assert results[0].friend_request_id is None
        assert results[1].friend_request_id is not None
        assert results[2].friend_request_id is not None
