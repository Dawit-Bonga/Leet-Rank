from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies.auth import get_auth_identity
from app.main import app
from app.models import User, UserSyncState
from app.routes.users import get_leetcode_client
from app.services.auth import AuthIdentity
from app.services.leetcode import LeetCodeUser, UpstreamUnavailableError, UserNotFoundError


class FakeLeetCodeClient:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.requested_usernames: list[str] = []
        self.auth_user_id = uuid4()

    def get_user(self, username: str) -> LeetCodeUser:
        self.requested_usernames.append(username)
        if self.error is not None:
            raise self.error
        return LeetCodeUser(username=username)


@pytest.fixture
def onboarding_client() -> Generator[tuple[TestClient, Session, FakeLeetCodeClient], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    provider = FakeLeetCodeClient()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_leetcode_client] = lambda: provider
    app.dependency_overrides[get_auth_identity] = lambda: AuthIdentity(
        id=provider.auth_user_id,
        email="alice@example.com",
    )
    try:
        yield TestClient(app), session, provider
    finally:
        app.dependency_overrides.clear()
        session.close()


def onboarding_payload() -> dict[str, str | int]:
    return {
        "username": "Alice",
        "display_name": "Alice",
        "leetcode_username": " AliceLC ",
        "primary_goal": "CONSISTENCY",
        "leetcode_experience": "INTERMEDIATE",
        "weekly_problem_goal": 5,
    }


def test_onboarding_creates_user_and_idle_sync_state(onboarding_client):
    client, session, provider = onboarding_client

    response = client.post("/users/me/onboarding", json=onboarding_payload())

    assert response.status_code == 201
    assert response.json()["username"] == "alice"
    assert response.json()["leetcode_username"] == "alicelc"
    assert response.json()["sync_status"] == "IDLE"
    assert response.json()["primary_goal"] == "CONSISTENCY"
    assert provider.requested_usernames == ["alicelc"]
    assert session.scalar(select(func.count()).select_from(User)) == 1
    assert session.scalar(select(func.count()).select_from(UserSyncState)) == 1


def test_get_me_reports_onboarding_state_and_profile(onboarding_client):
    client, _, _ = onboarding_client

    before = client.get("/users/me")
    assert before.status_code == 200
    assert before.json() == {
        "email": "alice@example.com",
        "onboarding_completed": False,
        "profile": None,
    }

    assert client.post("/users/me/onboarding", json=onboarding_payload()).status_code == 201

    after = client.get("/users/me")
    assert after.status_code == 200
    assert after.json()["email"] == "alice@example.com"
    assert after.json()["onboarding_completed"] is True
    assert after.json()["profile"]["username"] == "alice"
    assert after.json()["profile"]["sync_status"] == "IDLE"
    assert after.json()["profile"]["last_sync_attempted_at"] is None
    assert after.json()["profile"]["last_successful_sync_at"] is None


def test_authenticated_user_can_update_profile_settings(onboarding_client):
    client, _, _ = onboarding_client
    client.post("/users/me/onboarding", json=onboarding_payload())

    response = client.patch(
        "/users/me/settings",
        json={
            "display_name": "  Alice Updated  ",
            "primary_goal": "COMPETITION",
            "leetcode_experience": "ADVANCED",
            "weekly_problem_goal": 9,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "display_name": "Alice Updated",
        "primary_goal": "COMPETITION",
        "leetcode_experience": "ADVANCED",
        "weekly_problem_goal": 9,
        "submission_source": "leetcode",
        "neetcode_repo_owner": None,
        "neetcode_repo_name": None,
    }
    profile = client.get("/users/me").json()["profile"]
    assert profile["display_name"] == "Alice Updated"
    assert profile["weekly_problem_goal"] == 9
    assert profile["username"] == "alice"
    assert profile["leetcode_username"] == "alicelc"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"display_name": "   "},
        {"weekly_problem_goal": 0},
        {"primary_goal": "FAME"},
    ],
)
def test_invalid_profile_settings_are_rejected(onboarding_client, payload):
    client, _, _ = onboarding_client
    client.post("/users/me/onboarding", json=onboarding_payload())

    response = client.patch("/users/me/settings", json=payload)

    assert response.status_code == 422


def test_duplicate_leetcode_username_is_rejected_without_second_provider_call(onboarding_client):
    client, session, provider = onboarding_client
    assert client.post("/users/me/onboarding", json=onboarding_payload()).status_code == 201
    provider.auth_user_id = uuid4()

    response = client.post(
        "/users/me/onboarding",
        json={
            **onboarding_payload(),
            "username": "other",
            "display_name": "Other",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "leetcode_username_taken"
    assert provider.requested_usernames == ["alicelc"]
    assert session.scalar(select(func.count()).select_from(User)) == 1


def test_duplicate_leetrank_username_is_rejected_without_provider_call(onboarding_client):
    client, session, provider = onboarding_client
    assert client.post("/users/me/onboarding", json=onboarding_payload()).status_code == 201
    provider.auth_user_id = uuid4()

    response = client.post(
        "/users/me/onboarding",
        json={
            **onboarding_payload(),
            "leetcode_username": "other-lc",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "username_taken"
    assert provider.requested_usernames == ["alicelc"]
    assert session.scalar(select(func.count()).select_from(User)) == 1


def test_authenticated_account_cannot_onboard_twice(onboarding_client):
    client, session, provider = onboarding_client
    assert client.post("/users/me/onboarding", json=onboarding_payload()).status_code == 201

    response = client.post(
        "/users/me/onboarding",
        json={
            **onboarding_payload(),
            "username": "other",
            "leetcode_username": "other-lc",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "profile_exists"
    assert provider.requested_usernames == ["alicelc"]
    assert session.scalar(select(func.count()).select_from(User)) == 1


def test_missing_leetcode_user_does_not_create_local_user(onboarding_client):
    client, session, _ = onboarding_client
    provider = FakeLeetCodeClient(error=UserNotFoundError("LeetCode user does not exist."))
    app.dependency_overrides[get_leetcode_client] = lambda: provider

    response = client.post("/users/me/onboarding", json=onboarding_payload())

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_leetcode_username"
    assert session.scalar(select(func.count()).select_from(User)) == 0


def test_provider_outage_is_retryable_and_does_not_create_user(onboarding_client):
    client, session, _ = onboarding_client
    provider = FakeLeetCodeClient(error=UpstreamUnavailableError("Provider unavailable."))
    app.dependency_overrides[get_leetcode_client] = lambda: provider

    response = client.post("/users/me/onboarding", json=onboarding_payload())

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "upstream_unavailable"
    assert session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("primary_goal", "FAME"),
        ("leetcode_experience", "EXPERT"),
        ("weekly_problem_goal", 0),
        ("weekly_problem_goal", 101),
        ("username", "not valid"),
    ],
)
def test_invalid_onboarding_choices_are_rejected(onboarding_client, field, value):
    client, session, provider = onboarding_client

    response = client.post(
        "/users/me/onboarding",
        json={**onboarding_payload(), field: value},
    )

    assert response.status_code == 422
    assert provider.requested_usernames == []
    assert session.scalar(select(func.count()).select_from(User)) == 0


def test_users_cannot_trigger_synchronization_through_the_public_api(onboarding_client):
    client, _, _ = onboarding_client

    response = client.post("/users/me/sync")

    assert response.status_code == 404


def test_new_user_has_zero_score_snapshot_and_empty_activity(onboarding_client):
    client, _, _ = onboarding_client
    client.post("/users/me/onboarding", json=onboarding_payload())

    scores = client.get("/users/me/scores")
    activity = client.get("/users/me/activity")

    assert scores.status_code == 200
    assert scores.json()["scores"]["week"]["points"] == 0
    assert scores.json()["scores"]["month"]["points"] == 0
    assert scores.json()["scores"]["all_time"]["points"] == 0
    assert scores.json()["as_of"].endswith("Z")
    assert activity.status_code == 200
    assert activity.json() == {
        "items": [],
        "limit": 20,
        "offset": 0,
        "has_more": False,
    }


def test_friend_request_api_flow(onboarding_client):
    client, _, provider = onboarding_client
    alice_auth_user_id = provider.auth_user_id
    client.post("/users/me/onboarding", json=onboarding_payload())
    provider.auth_user_id = uuid4()
    bob_auth_user_id = provider.auth_user_id
    bob = client.post(
        "/users/me/onboarding",
        json={
            **onboarding_payload(),
            "username": "bob",
            "display_name": "Bob",
            "leetcode_username": "bob-lc",
        },
    ).json()

    provider.auth_user_id = alice_auth_user_id
    search_before_send = client.get("/users/me/search?username=boB")
    assert search_before_send.status_code == 200
    assert search_before_send.json()["users"][0]["relationship"] == "NONE"
    sent = client.post(
        "/users/me/friend-requests",
        json={"username": "BoB"},
    )
    assert sent.status_code == 201
    assert sent.json()["user"]["username"] == "bob"
    search_after_send = client.get("/users/me/search?username=boB")
    assert search_after_send.status_code == 200
    assert search_after_send.json()["users"][0]["relationship"] == "OUTGOING"
    assert search_after_send.json()["users"][0]["friend_request_id"] == sent.json()["id"]
    pending_profile = client.get(f"/users/me/friends/{bob['id']}/profile")
    assert pending_profile.status_code == 404

    provider.auth_user_id = bob_auth_user_id
    pending = client.get("/users/me/friend-requests")
    assert pending.status_code == 200
    assert pending.json()["incoming"][0]["user"]["username"] == "alice"
    pending_overview = client.get("/users/me/friends/overview")
    assert pending_overview.status_code == 200
    assert pending_overview.json()["friends"] == []
    assert pending_overview.json()["incoming"][0]["user"]["username"] == "alice"
    assert pending_overview.json()["outgoing"] == []
    assert pending_overview.json()["as_of"].endswith("Z")

    accepted = client.post(
        f"/users/me/friend-requests/{sent.json()['id']}/accept"
    )
    assert accepted.status_code == 200
    assert accepted.json()["username"] == "alice"

    provider.auth_user_id = alice_auth_user_id
    search_after_accept = client.get("/users/me/search?username=bob")
    assert search_after_accept.json()["users"][0]["relationship"] == "FRIEND"
    alice_friends = client.get("/users/me/friends")
    assert alice_friends.status_code == 200
    assert alice_friends.json()["friends"][0]["username"] == "bob"
    alice_overview = client.get("/users/me/friends/overview")
    assert alice_overview.status_code == 200
    assert alice_overview.json()["friends"][0]["username"] == "bob"
    assert alice_overview.json()["incoming"] == []
    assert alice_overview.json()["outgoing"] == []

    leaderboard = client.get("/users/me/leaderboard?period=week")
    assert leaderboard.status_code == 200
    assert leaderboard.json()["period"] == "week"
    assert [entry["user"]["username"] for entry in leaderboard.json()["entries"]] == [
        "alice",
        "bob",
    ]
    assert all(entry["rank"] == 1 for entry in leaderboard.json()["entries"])

    friend_profile = client.get(f"/users/me/friends/{bob['id']}/profile")
    assert friend_profile.status_code == 200
    assert friend_profile.json()["user"] == {
        "id": bob["id"],
        "username": "bob",
        "display_name": "Bob",
        "leetcode_username": "bob-lc",
        "weekly_problem_goal": 5,
        "scoring_started_at": bob["scoring_started_at"],
    }
    assert friend_profile.json()["scores"]["week"]["points"] == 0
    assert friend_profile.json()["recent_activity"] == []

    removed = client.delete(f"/users/me/friends/{bob['id']}")
    assert removed.status_code == 204
    unavailable = client.get(f"/users/me/friends/{bob['id']}/profile")
    assert unavailable.status_code == 404
    assert unavailable.json()["detail"]["code"] == "friend_profile_not_found"
    provider.auth_user_id = bob_auth_user_id
    assert client.get("/users/me/friends").json() == {"friends": []}
