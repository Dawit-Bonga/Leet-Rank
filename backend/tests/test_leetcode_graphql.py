from datetime import UTC, datetime
import json

import httpx
import pytest

from app.services.leetcode import (
    LeetCodeGraphQLClient,
    UpstreamBadResponseError,
    UpstreamRateLimitedError,
    UserNotFoundError,
)


def request_payload(request: httpx.Request) -> dict:
    return json.loads(request.content)


def test_normalizes_verified_accepted_submission_contract():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = request_payload(request)
        assert request.method == "POST"
        assert str(request.url) == "https://leetcode.com/graphql"
        assert payload["variables"] == {"username": "dawit101", "limit": 20}
        assert "recentAcSubmissionList" in payload["query"]
        return httpx.Response(
            200,
            json={
                "data": {
                    "matchedUser": {"username": "dawit101"},
                    "recentAcSubmissionList": [
                        {
                            "id": "2111139876",
                            "title": "Shortest Bridge",
                            "titleSlug": "shortest-bridge",
                            "timestamp": "1787041256",
                        }
                    ],
                }
            },
        )

    with LeetCodeGraphQLClient(transport=httpx.MockTransport(handler)) as client:
        submissions = client.get_accepted_submissions("dawit101")

    assert submissions[0].external_id == "2111139876"
    assert submissions[0].problem_slug == "shortest-bridge"
    assert submissions[0].submitted_at == datetime.fromtimestamp(1787041256, tz=UTC)


def test_get_user_returns_canonical_username():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"data": {"matchedUser": {"username": "CanonicalName"}}},
        )
    )

    with LeetCodeGraphQLClient(transport=transport) as client:
        user = client.get_user("canonicalname")

    assert user.username == "CanonicalName"


def test_get_problem_normalizes_difficulty():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": {
                    "question": {
                        "title": "Two Sum",
                        "titleSlug": "two-sum",
                        "difficulty": "Easy",
                    }
                }
            },
        )
    )

    with LeetCodeGraphQLClient(transport=transport) as client:
        problem = client.get_problem("two-sum")

    assert problem.slug == "two-sum"
    assert problem.difficulty == "EASY"


def test_missing_user_is_distinct_from_malformed_response():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"data": {"matchedUser": None}})
    )

    with LeetCodeGraphQLClient(transport=transport) as client:
        with pytest.raises(UserNotFoundError):
            client.get_user("missing")


def test_graphql_errors_are_rejected_even_with_http_200():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"errors": [{"message": "Query failed"}]})
    )

    with LeetCodeGraphQLClient(transport=transport) as client:
        with pytest.raises(UpstreamBadResponseError, match="GraphQL error"):
            client.get_user("alice")


def test_rate_limit_is_checked_before_parsing_non_json_body():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(429, text="Too many requests")
    )

    with LeetCodeGraphQLClient(transport=transport) as client:
        with pytest.raises(UpstreamRateLimitedError):
            client.get_user("alice")


def test_public_submission_limit_is_enforced_locally():
    transport = httpx.MockTransport(lambda request: httpx.Response(200))

    with LeetCodeGraphQLClient(transport=transport) as client:
        with pytest.raises(ValueError, match="between 1 and 20"):
            client.get_accepted_submissions("alice", limit=21)
