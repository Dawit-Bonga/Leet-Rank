from datetime import UTC, datetime

import httpx
import pytest

from app.services.leetcode import (
    UpstreamBadResponseError,
    UpstreamRateLimitedError,
    UpstreamUnavailableError,
)
from app.services.neetcode import GitHubNeetCodeClient


def _client(response: httpx.Response, *, token: str | None = "test-token"):
    def handler(request: httpx.Request) -> httpx.Response:
        if token:
            assert request.headers["Authorization"] == f"Bearer {token}"
        return response

    return GitHubNeetCodeClient(token=token, transport=httpx.MockTransport(handler))


def test_github_client_reports_authentication_failure():
    with _client(httpx.Response(401, json={"message": "Bad credentials"})) as client:
        with pytest.raises(UpstreamBadResponseError, match="authentication failed.*401"):
            client.get_recent_accepted_submissions(owner="alice", repo="solutions")


def test_github_client_distinguishes_rate_limit_from_permission_denial():
    rate_limited = httpx.Response(
        403,
        json={"message": "API rate limit exceeded"},
        headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "12345"},
    )
    with _client(rate_limited) as client:
        with pytest.raises(UpstreamRateLimitedError, match="12345"):
            client.get_recent_accepted_submissions(owner="alice", repo="solutions")

    denied = httpx.Response(403, json={"message": "Resource not accessible"})
    with _client(denied) as client:
        with pytest.raises(UpstreamBadResponseError, match="denied repository access"):
            client.get_recent_accepted_submissions(owner="alice", repo="solutions")


def test_github_client_explains_missing_or_invalid_repository():
    with _client(httpx.Response(404, json={"message": "Not Found"})) as client:
        with pytest.raises(UpstreamBadResponseError, match="not found.*404"):
            client.get_recent_accepted_submissions(owner="alice", repo="missing")

    with _client(httpx.Response(422, json={"message": "Validation Failed"})) as client:
        with pytest.raises(UpstreamBadResponseError, match="rejected.*422"):
            client.get_recent_accepted_submissions(owner="bad owner", repo="bad repo")


def test_empty_github_repository_returns_no_submissions():
    with _client(httpx.Response(409, json={"message": "Git Repository is empty."})) as client:
        assert client.get_recent_accepted_submissions(owner="alice", repo="empty") == []


def test_github_client_sends_incremental_since_timestamp():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["since"] == "2026-09-01T12:30:00Z"
        assert request.url.params["per_page"] == "100"
        return httpx.Response(200, json=[])

    with GitHubNeetCodeClient(
        token="test-token",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.get_recent_accepted_submissions(
            owner="alice",
            repo="solutions",
            since=datetime(2026, 9, 1, 12, 30, tzinfo=UTC),
        ) == []


def test_github_client_reports_service_failure():
    with _client(httpx.Response(503, text="unavailable")) as client:
        with pytest.raises(UpstreamUnavailableError, match="503"):
            client.get_recent_accepted_submissions(owner="alice", repo="solutions")
