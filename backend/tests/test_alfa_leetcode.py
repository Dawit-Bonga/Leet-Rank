from datetime import UTC, datetime

import httpx
import pytest

from app.services.leetcode import AlfaLeetCodeClient, UpstreamRateLimitedError


def test_normalizes_accepted_submissions():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["limit"] == "50"
        return httpx.Response(
            200,
            json={
                "submission": [
                    {
                        "id": "123",
                        "title": "Two Sum",
                        "titleSlug": "two-sum",
                        "timestamp": "1767225600",
                    }
                ]
            },
        )

    with AlfaLeetCodeClient(transport=httpx.MockTransport(handler)) as client:
        submissions = client.get_accepted_submissions("alice")

    assert submissions[0].external_id == "123"
    assert submissions[0].problem_slug == "two-sum"
    assert submissions[0].submitted_at == datetime.fromtimestamp(1767225600, tz=UTC)


def test_rate_limit_is_distinct_from_other_upstream_failures():
    transport = httpx.MockTransport(lambda request: httpx.Response(429, json={}))

    with AlfaLeetCodeClient(transport=transport) as client:
        with pytest.raises(UpstreamRateLimitedError):
            client.get_user("alice")
