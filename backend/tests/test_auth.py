from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_auth_client
from app.main import app
from app.services.auth import (
    AuthBadResponseError,
    AuthServiceUnavailableError,
    InvalidAccessTokenError,
    SupabaseAuthClient,
)


PROJECT_URL = "https://example.supabase.co"
PUBLISHABLE_KEY = "test-publishable-key"


def test_auth_client_validates_token_and_returns_identity():
    auth_user_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == f"{PROJECT_URL}/auth/v1/user"
        assert request.headers["apikey"] == PUBLISHABLE_KEY
        assert request.headers["authorization"] == "Bearer valid-token"
        return httpx.Response(
            200,
            json={"id": str(auth_user_id), "email": "alice@example.com"},
        )

    with SupabaseAuthClient(
        project_url=PROJECT_URL,
        publishable_key=PUBLISHABLE_KEY,
        transport=httpx.MockTransport(handler),
    ) as client:
        identity = client.get_identity("valid-token")

    assert identity.id == auth_user_id
    assert identity.email == "alice@example.com"


@pytest.mark.parametrize("status_code", [401, 403])
def test_auth_client_rejects_invalid_or_expired_token(status_code):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status_code, json={"message": "invalid"})
    )

    with SupabaseAuthClient(
        project_url=PROJECT_URL,
        publishable_key=PUBLISHABLE_KEY,
        transport=transport,
    ) as client:
        with pytest.raises(InvalidAccessTokenError):
            client.get_identity("bad-token")


def test_auth_client_maps_upstream_failure_to_retryable_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, text="unavailable")
    )

    with SupabaseAuthClient(
        project_url=PROJECT_URL,
        publishable_key=PUBLISHABLE_KEY,
        transport=transport,
    ) as client:
        with pytest.raises(AuthServiceUnavailableError):
            client.get_identity("valid-token")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"id": "not-a-uuid"}),
        httpx.Response(200, json={"id": str(uuid4()), "email": 123}),
        httpx.Response(418, json={"message": "unexpected"}),
    ],
)
def test_auth_client_rejects_malformed_responses(response):
    transport = httpx.MockTransport(lambda request: response)

    with SupabaseAuthClient(
        project_url=PROJECT_URL,
        publishable_key=PUBLISHABLE_KEY,
        transport=transport,
    ) as client:
        with pytest.raises(AuthBadResponseError):
            client.get_identity("valid-token")


class FakeAuthClient:
    def get_identity(self, access_token: str):
        raise AssertionError("Missing credentials should be rejected before validation.")


def test_protected_endpoint_requires_bearer_token():
    app.dependency_overrides[get_auth_client] = lambda: FakeAuthClient()
    try:
        response = TestClient(app).get("/users/me/scores")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"]["code"] == "authentication_required"
