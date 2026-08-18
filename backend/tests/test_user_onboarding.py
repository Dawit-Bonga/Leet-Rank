from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, UserSyncState
from app.routes.users import get_leetcode_client
from app.services.leetcode import LeetCodeUser, UpstreamUnavailableError, UserNotFoundError


class FakeLeetCodeClient:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.requested_usernames: list[str] = []

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

    response = client.post("/users", json=onboarding_payload())

    assert response.status_code == 201
    assert response.json()["username"] == "alice"
    assert response.json()["leetcode_username"] == "alicelc"
    assert response.json()["sync_status"] == "IDLE"
    assert response.json()["primary_goal"] == "CONSISTENCY"
    assert provider.requested_usernames == ["alicelc"]
    assert session.scalar(select(func.count()).select_from(User)) == 1
    assert session.scalar(select(func.count()).select_from(UserSyncState)) == 1


def test_duplicate_leetcode_username_is_rejected_without_second_provider_call(onboarding_client):
    client, session, provider = onboarding_client
    assert client.post("/users", json=onboarding_payload()).status_code == 201

    response = client.post(
        "/users",
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
    assert client.post("/users", json=onboarding_payload()).status_code == 201

    response = client.post(
        "/users",
        json={
            **onboarding_payload(),
            "leetcode_username": "other-lc",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "username_taken"
    assert provider.requested_usernames == ["alicelc"]
    assert session.scalar(select(func.count()).select_from(User)) == 1


def test_missing_leetcode_user_does_not_create_local_user(onboarding_client):
    client, session, _ = onboarding_client
    provider = FakeLeetCodeClient(error=UserNotFoundError("LeetCode user does not exist."))
    app.dependency_overrides[get_leetcode_client] = lambda: provider

    response = client.post("/users", json=onboarding_payload())

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_leetcode_username"
    assert session.scalar(select(func.count()).select_from(User)) == 0


def test_provider_outage_is_retryable_and_does_not_create_user(onboarding_client):
    client, session, _ = onboarding_client
    provider = FakeLeetCodeClient(error=UpstreamUnavailableError("Provider unavailable."))
    app.dependency_overrides[get_leetcode_client] = lambda: provider

    response = client.post("/users", json=onboarding_payload())

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

    response = client.post("/users", json={**onboarding_payload(), field: value})

    assert response.status_code == 422
    assert provider.requested_usernames == []
    assert session.scalar(select(func.count()).select_from(User)) == 0


def test_sync_endpoint_returns_not_found_for_unknown_user(onboarding_client):
    client, _, _ = onboarding_client

    response = client.post(f"/users/{uuid4()}/sync")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "user_not_found"


def test_new_user_has_zero_score_snapshot_and_empty_activity(onboarding_client):
    client, _, _ = onboarding_client
    created = client.post("/users", json=onboarding_payload()).json()

    scores = client.get(f"/users/{created['id']}/scores")
    activity = client.get(f"/users/{created['id']}/activity")

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
    client, _, _ = onboarding_client
    alice = client.post("/users", json=onboarding_payload()).json()
    bob = client.post(
        "/users",
        json={
            **onboarding_payload(),
            "username": "bob",
            "display_name": "Bob",
            "leetcode_username": "bob-lc",
        },
    ).json()

    sent = client.post(
        f"/users/{alice['id']}/friend-requests",
        json={"username": "BoB"},
    )
    assert sent.status_code == 201
    assert sent.json()["user"]["username"] == "bob"

    pending = client.get(f"/users/{bob['id']}/friend-requests")
    assert pending.status_code == 200
    assert pending.json()["incoming"][0]["user"]["username"] == "alice"

    accepted = client.post(
        f"/users/{bob['id']}/friend-requests/{sent.json()['id']}/accept"
    )
    assert accepted.status_code == 200
    assert accepted.json()["username"] == "alice"

    alice_friends = client.get(f"/users/{alice['id']}/friends")
    assert alice_friends.status_code == 200
    assert alice_friends.json()["friends"][0]["username"] == "bob"

    leaderboard = client.get(f"/users/{alice['id']}/leaderboard?period=week")
    assert leaderboard.status_code == 200
    assert leaderboard.json()["period"] == "week"
    assert [entry["user"]["username"] for entry in leaderboard.json()["entries"]] == [
        "alice",
        "bob",
    ]
    assert all(entry["rank"] == 1 for entry in leaderboard.json()["entries"])

    removed = client.delete(f"/users/{alice['id']}/friends/{bob['id']}")
    assert removed.status_code == 204
    assert client.get(f"/users/{bob['id']}/friends").json() == {"friends": []}
