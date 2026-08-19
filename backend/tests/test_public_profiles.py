from datetime import UTC, datetime
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.services.public_profiles import PublicProfileNotFoundError, get_public_profile


@pytest.fixture
def public_profile_client() -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.clear()
        session.close()


def add_user(session: Session) -> User:
    user = User(
        username="dawit",
        display_name="Dawit",
        leetcode_username="dawit101",
        primary_goal="CONSISTENCY",
        leetcode_experience="INTERMEDIATE",
        weekly_problem_goal=5,
        scoring_started_at=datetime.now(UTC),
        onboarding_completed_at=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    return user


def test_public_profile_service_finds_username_case_insensitively(public_profile_client):
    _, session = public_profile_client
    user = add_user(session)

    assert get_public_profile(session, username=" DAWIT ").id == user.id


def test_public_profile_service_rejects_unknown_username(public_profile_client):
    _, session = public_profile_client

    with pytest.raises(PublicProfileNotFoundError):
        get_public_profile(session, username="missing")


def test_public_profile_api_returns_only_shareable_fields(public_profile_client):
    client, session = public_profile_client
    add_user(session)

    response = client.get("/users/public/DAWIT")

    assert response.status_code == 200
    assert set(response.json()) == {
        "id",
        "username",
        "display_name",
        "leetcode_username",
        "weekly_problem_goal",
        "joined_at",
    }
    assert response.json()["username"] == "dawit"


def test_public_profile_api_returns_structured_not_found(public_profile_client):
    client, _ = public_profile_client

    response = client.get("/users/public/missing")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "profile_not_found"
