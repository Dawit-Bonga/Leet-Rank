from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx


LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
ALFA_API_URL = "https://alfa-leetcode-api.onrender.com"

USER_SUBMISSIONS_QUERY = """
query userSubmissions($username: String!, $limit: Int!) {
  matchedUser(username: $username) {
    username
  }
  recentAcSubmissionList(username: $username, limit: $limit) {
    title
    timestamp
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


class AlfaLeetCodeClient:
    def __init__(
        self,
        *,
        base_url: str = ALFA_API_URL,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AlfaLeetCodeClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _get_json(self, path: str, *, params: dict[str, int | str] | None = None) -> Any:
        try:
            response = self._client.get(path, params=params)
        except httpx.RequestError as exc:
            raise UpstreamUnavailableError("Could not reach the LeetCode provider.") from exc

        if response.status_code == 404:
            raise UserNotFoundError("LeetCode user or problem does not exist.")
        if response.status_code == 429:
            raise UpstreamRateLimitedError("LeetCode provider rate limit reached.")
        if response.status_code >= 500:
            raise UpstreamUnavailableError("LeetCode provider is currently unavailable.")
        if response.status_code != 200:
            raise UpstreamBadResponseError("Unexpected status from LeetCode provider.")
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise UpstreamBadResponseError("LeetCode provider returned invalid JSON.") from exc

    def get_user(self, username: str) -> LeetCodeUser:
        body = self._get_json(f"/{username}")
        if not isinstance(body, dict):
            raise UpstreamBadResponseError("LeetCode profile payload is malformed.")
        canonical_username = body.get("username")
        if not isinstance(canonical_username, str) or not canonical_username:
            raise UpstreamBadResponseError("LeetCode profile is missing a username.")
        return LeetCodeUser(username=canonical_username)

    def get_accepted_submissions(self, username: str, limit: int = 50) -> list[AcceptedSubmission]:
        body = self._get_json(f"/{username}/acSubmission", params={"limit": limit})
        if not isinstance(body, dict):
            raise UpstreamBadResponseError("Accepted submissions payload is malformed.")
        raw_submissions = body.get("submission")
        if not isinstance(raw_submissions, list):
            raise UpstreamBadResponseError("Accepted submissions list is missing.")

        submissions: list[AcceptedSubmission] = []
        for item in raw_submissions:
            if not isinstance(item, dict):
                raise UpstreamBadResponseError("Accepted submission entry is malformed.")
            try:
                external_id = str(item["id"])
                title = item["title"]
                slug = item["titleSlug"]
                timestamp = int(item["timestamp"])
            except (KeyError, TypeError, ValueError) as exc:
                raise UpstreamBadResponseError("Accepted submission fields are malformed.") from exc
            if not external_id or not isinstance(title, str) or not isinstance(slug, str):
                raise UpstreamBadResponseError("Accepted submission fields are malformed.")
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
        body = self._get_json("/select", params={"titleSlug": title_slug})
        if not isinstance(body, dict):
            raise UpstreamBadResponseError("Problem payload is malformed.")
        title = body.get("questionTitle") or body.get("title")
        slug = body.get("titleSlug") or title_slug
        difficulty = body.get("difficulty")
        if not isinstance(title, str) or not isinstance(slug, str) or difficulty not in {"Easy", "Medium", "Hard", "EASY", "MEDIUM", "HARD"}:
            raise UpstreamBadResponseError("Problem fields are malformed.")
        return ProblemDetails(slug=slug, title=title, difficulty=difficulty.upper())


def fetch_recent_accepted_submissions(
    username: str,
    limit: int = 20,
    timeout_seconds: float = 10.0,
) -> list[dict[str, int | str]]:
    payload = {
        "query": USER_SUBMISSIONS_QUERY,
        "variables": {"username": username, "limit": limit},
    }

    try:
        response = httpx.post(
            LEETCODE_GRAPHQL_URL,
            json=payload,
            timeout=timeout_seconds,
            headers={"Content-Type": "application/json"},
        )
    except httpx.RequestError as exc:
        raise UpstreamUnavailableError("Could not reach LeetCode.") from exc

    if response.status_code >= 500:
        raise UpstreamUnavailableError("LeetCode is currently unavailable.")

    if response.status_code != 200:
        raise UpstreamBadResponseError("Unexpected status from LeetCode.")

    try:
        body = response.json()
    except json.JSONDecodeError as exc:
        raise UpstreamBadResponseError("LeetCode returned invalid JSON.") from exc

    data = body.get("data")
    if not isinstance(data, dict):
        raise UpstreamBadResponseError("LeetCode response missing data object.")

    if data.get("matchedUser") is None:
        raise UserNotFoundError("LeetCode user does not exist.")

    raw_submissions = data.get("recentAcSubmissionList")
    if raw_submissions is None:
        return []
    if not isinstance(raw_submissions, list):
        raise UpstreamBadResponseError("LeetCode submissions payload is malformed.")

    parsed_submissions: list[dict[str, int | str]] = []
    for item in raw_submissions:
        if not isinstance(item, dict):
            raise UpstreamBadResponseError("Submission entry is malformed.")

        title = item.get("title")
        timestamp = item.get("timestamp")

        if not isinstance(title, str):
            raise UpstreamBadResponseError("Submission title is missing.")
        if timestamp is None:
            raise UpstreamBadResponseError("Submission timestamp is missing.")

        try:
            parsed_timestamp = int(timestamp)
        except (TypeError, ValueError) as exc:
            raise UpstreamBadResponseError("Submission timestamp is invalid.") from exc

        parsed_submissions.append({"title": title, "timestamp": parsed_timestamp})

    return parsed_submissions
