from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx


LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
PUBLIC_SUBMISSION_LIMIT = 20

USER_PROFILE_QUERY = """
query userProfile($username: String!) {
  matchedUser(username: $username) {
    username
  }
}
"""

ACCEPTED_SUBMISSIONS_QUERY = """
query recentAcceptedSubmissions($username: String!, $limit: Int!) {
  matchedUser(username: $username) {
    username
  }
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
  }
}
"""

PROBLEM_DETAILS_QUERY = """
query problemDetails($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    title
    titleSlug
    difficulty
  }
}
"""


class UserNotFoundError(Exception):
    pass


class UpstreamUnavailableError(Exception):
    pass


class UpstreamBadResponseError(Exception):
    pass


class UpstreamRateLimitedError(Exception):
    pass


@dataclass(frozen=True)
class LeetCodeUser:
    username: str


@dataclass(frozen=True)
class AcceptedSubmission:
    external_id: str
    problem_slug: str
    problem_title: str
    submitted_at: datetime


@dataclass(frozen=True)
class ProblemDetails:
    slug: str
    title: str
    difficulty: str


class LeetCodeGraphQLClient:
    provider_name = "leetcode"

    def __init__(
        self,
        *,
        endpoint: str = LEETCODE_GRAPHQL_URL,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._client = httpx.Client(
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Referer": "https://leetcode.com/",
                "User-Agent": "LeetRank/0.1",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "LeetCodeGraphQLClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _graphql(self, query: str, variables: dict[str, int | str]) -> dict[str, Any]:
        try:
            response = self._client.post(
                self._endpoint,
                json={"query": query, "variables": variables},
            )
        except httpx.RequestError as exc:
            raise UpstreamUnavailableError("Could not reach LeetCode.") from exc

        if response.status_code == 429:
            raise UpstreamRateLimitedError("LeetCode rate limit reached.")
        if response.status_code >= 500:
            raise UpstreamUnavailableError("LeetCode is currently unavailable.")
        if response.status_code != 200:
            raise UpstreamBadResponseError("Unexpected status from LeetCode.")

        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            raise UpstreamBadResponseError("LeetCode returned invalid JSON.") from exc

        if not isinstance(body, dict):
            raise UpstreamBadResponseError("LeetCode response is malformed.")
        if body.get("errors"):
            raise UpstreamBadResponseError("LeetCode returned a GraphQL error.")
        data = body.get("data")
        if not isinstance(data, dict):
            raise UpstreamBadResponseError("LeetCode response missing data object.")
        return data

    def get_user(self, username: str) -> LeetCodeUser:
        data = self._graphql(USER_PROFILE_QUERY, {"username": username})
        matched_user = data.get("matchedUser")
        if matched_user is None:
            raise UserNotFoundError("LeetCode user does not exist.")
        if not isinstance(matched_user, dict):
            raise UpstreamBadResponseError("LeetCode profile payload is malformed.")
        canonical_username = matched_user.get("username")
        if not isinstance(canonical_username, str) or not canonical_username:
            raise UpstreamBadResponseError("LeetCode profile is missing a username.")
        return LeetCodeUser(username=canonical_username)

    def get_accepted_submissions(
        self,
        username: str,
        limit: int = PUBLIC_SUBMISSION_LIMIT,
    ) -> list[AcceptedSubmission]:
        if not 1 <= limit <= PUBLIC_SUBMISSION_LIMIT:
            raise ValueError(
                f"Public submission limit must be between 1 and {PUBLIC_SUBMISSION_LIMIT}."
            )

        data = self._graphql(
            ACCEPTED_SUBMISSIONS_QUERY,
            {"username": username, "limit": limit},
        )
        if data.get("matchedUser") is None:
            raise UserNotFoundError("LeetCode user does not exist.")
        raw_submissions = data.get("recentAcSubmissionList")
        if raw_submissions is None:
            return []
        if not isinstance(raw_submissions, list):
            raise UpstreamBadResponseError("LeetCode submissions payload is malformed.")

        submissions: list[AcceptedSubmission] = []
        for item in raw_submissions:
            if not isinstance(item, dict):
                raise UpstreamBadResponseError("LeetCode submission entry is malformed.")
            try:
                external_id = str(item["id"])
                title = item["title"]
                slug = item["titleSlug"]
                timestamp = int(item["timestamp"])
            except (KeyError, TypeError, ValueError) as exc:
                raise UpstreamBadResponseError("LeetCode submission fields are malformed.") from exc
            if not external_id or not isinstance(title, str) or not isinstance(slug, str):
                raise UpstreamBadResponseError("LeetCode submission fields are malformed.")
            submissions.append(
                AcceptedSubmission(
                    external_id=external_id,
                    problem_slug=slug,
                    problem_title=title,
                    submitted_at=datetime.fromtimestamp(timestamp, tz=UTC),
                )
            )
        return submissions

    def get_problem(self, title_slug: str) -> ProblemDetails:
        data = self._graphql(PROBLEM_DETAILS_QUERY, {"titleSlug": title_slug})
        question = data.get("question")
        if not isinstance(question, dict):
            raise UpstreamBadResponseError("LeetCode problem does not exist or is malformed.")
        title = question.get("title")
        slug = question.get("titleSlug")
        difficulty = question.get("difficulty")
        if (
            not isinstance(title, str)
            or not isinstance(slug, str)
            or difficulty not in {"Easy", "Medium", "Hard", "EASY", "MEDIUM", "HARD"}
        ):
            raise UpstreamBadResponseError("LeetCode problem fields are malformed.")
        return ProblemDetails(slug=slug, title=title, difficulty=difficulty.upper())


def fetch_recent_accepted_submissions(
    username: str,
    limit: int = PUBLIC_SUBMISSION_LIMIT,
    timeout_seconds: float = 10.0,
) -> list[dict[str, int | str]]:
    """Compatibility helper for the prototype submissions endpoint."""
    with LeetCodeGraphQLClient(timeout_seconds=timeout_seconds) as client:
        submissions = client.get_accepted_submissions(username, limit=limit)
    return [
        {
            "title": submission.problem_title,
            "timestamp": int(submission.submitted_at.timestamp()),
        }
        for submission in submissions
    ]
