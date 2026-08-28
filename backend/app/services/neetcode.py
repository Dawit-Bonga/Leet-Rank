from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import httpx

from app.services.leetcode import UpstreamBadResponseError, UpstreamUnavailableError
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

    def _get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        try:
            response = self._client.get(path, params=params)
        except httpx.RequestError as exc:
            raise UpstreamUnavailableError("Could not reach GitHub.") from exc

        if response.status_code >= 500:
            raise UpstreamUnavailableError("GitHub is currently unavailable.")
        if response.status_code != 200:
            raise UpstreamBadResponseError("Unexpected status from GitHub.")
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
    ) -> list[NeetCodeSubmissionEvent]:
        per_page = min(max(limit, 1), 100)
        commits = self._get_json(
            f"/repos/{owner}/{repo}/commits",
            params={"per_page": per_page},
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
