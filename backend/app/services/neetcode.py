from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

import httpx

from app.services.leetcode import (
    UpstreamBadResponseError,
    UpstreamRateLimitedError,
    UpstreamUnavailableError,
)
from app.services.neetcode_sync import NEETCODE_PROVIDER, NeetCodeSubmissionEvent


GITHUB_API_BASE_URL = "https://api.github.com"


class GitHubNeetCodeClient:
    provider_name = NEETCODE_PROVIDER

    def __init__(
        self,
        *,
        token: str | None = None,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        resolved_token = token or os.getenv("GITHUB_TOKEN")
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "LeetClimb/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if resolved_token:
            headers["Authorization"] = f"Bearer {resolved_token}"
        self._client = httpx.Client(
            base_url=GITHUB_API_BASE_URL,
            timeout=timeout_seconds,
            transport=transport,
            headers=headers,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GitHubNeetCodeClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _error_message(response: httpx.Response) -> str | None:
        try:
            body = response.json()
        except json.JSONDecodeError:
            return None
        message = body.get("message") if isinstance(body, dict) else None
        return message if isinstance(message, str) else None

    def _get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        empty_on_conflict: bool = False,
    ) -> Any:
        try:
            response = self._client.get(path, params=params)
        except httpx.RequestError as exc:
            raise UpstreamUnavailableError("Could not reach GitHub.") from exc

        status = response.status_code
        message = self._error_message(response)
        if status == 409 and empty_on_conflict:
            return []
        if status == 401:
            raise UpstreamBadResponseError(
                "GitHub authentication failed (401). Check the cron job's GITHUB_TOKEN."
            )
        if status == 429 or (
            status == 403 and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            reset = response.headers.get("x-ratelimit-reset")
            reset_detail = f" Reset timestamp: {reset}." if reset else ""
            raise UpstreamRateLimitedError(
                f"GitHub API rate limit reached ({status}).{reset_detail}"
            )
        if status == 403:
            raise UpstreamBadResponseError(
                f"GitHub denied repository access (403). {message or 'Check token permissions.'}"
            )
        if status == 404:
            raise UpstreamBadResponseError(
                "GitHub repository or commit was not found (404). Check the owner, "
                "repository name, visibility, and token access."
            )
        if status == 422:
            raise UpstreamBadResponseError(
                f"GitHub rejected the repository request (422). {message or 'Check the owner and repository name.'}"
            )
        if status >= 500:
            raise UpstreamUnavailableError(f"GitHub is currently unavailable ({status}).")
        if status != 200:
            raise UpstreamBadResponseError(
                f"Unexpected response from GitHub ({status}). {message or 'No error details were returned.'}"
            )
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise UpstreamBadResponseError("GitHub returned invalid JSON.") from exc

    def _extract_problem_slug(self, path: str) -> str | None:
        parts = [item for item in path.split("/") if item]
        if len(parts) < 2:
            return None
        filename = parts[-1].lower()
        if "submission" not in filename:
            return None
        return parts[-2]

    def get_recent_accepted_submissions(
        self,
        *,
        owner: str,
        repo: str,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[NeetCodeSubmissionEvent]:
        per_page = min(max(limit, 1), 100)
        params: dict[str, Any] = {"per_page": per_page}
        if since is not None:
            normalized_since = since if since.tzinfo else since.replace(tzinfo=UTC)
            params["since"] = normalized_since.astimezone(UTC).isoformat().replace(
                "+00:00", "Z"
            )
        commits = self._get_json(
            f"/repos/{owner}/{repo}/commits",
            params=params,
            empty_on_conflict=True,
        )
        if not isinstance(commits, list):
            raise UpstreamBadResponseError("GitHub commits payload is malformed.")

        events: list[NeetCodeSubmissionEvent] = []
        for commit in commits:
            if not isinstance(commit, dict):
                continue
            sha = commit.get("sha")
            commit_obj = commit.get("commit")
            if not isinstance(sha, str) or not isinstance(commit_obj, dict):
                continue
            author_obj = commit_obj.get("author")
            if not isinstance(author_obj, dict):
                continue
            authored_at = author_obj.get("date")
            if not isinstance(authored_at, str):
                continue
            try:
                submitted_at = datetime.fromisoformat(authored_at.replace("Z", "+00:00"))
            except ValueError:
                continue

            commit_details = self._get_json(f"/repos/{owner}/{repo}/commits/{sha}")
            files = commit_details.get("files") if isinstance(commit_details, dict) else None
            if not isinstance(files, list):
                continue

            for file_obj in files:
                if not isinstance(file_obj, dict):
                    continue
                path = file_obj.get("filename")
                if not isinstance(path, str):
                    continue
                slug = self._extract_problem_slug(path)
                if not slug:
                    continue
                provider_submission_id = f"github:{owner}/{repo}:{sha}:{path}"
                title = slug.replace("-", " ").replace("_", " ").title()
                events.append(
                    NeetCodeSubmissionEvent(
                        provider_submission_id=provider_submission_id,
                        problem_slug=slug,
                        problem_title=title,
                        submitted_at=submitted_at,
                        repository=f"{owner}/{repo}",
                        commit_sha=sha,
                        file_path=path,
                    )
                )
                if len(events) >= limit:
                    return events
        return events
