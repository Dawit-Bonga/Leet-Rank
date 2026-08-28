from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import timedelta

import httpx

from app.database import SessionLocal
from app.services.automatic_sync import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_STALE_AFTER,
    DEFAULT_SYNC_INTERVAL,
    sync_due_users,
)
from app.services.leetcode import LeetCodeGraphQLClient
from app.services.neetcode import GitHubNeetCodeClient


def _positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if value < 1:
        raise ValueError(f"{name} must be at least one.")
    return value


def _positive_minutes_from_env(name: str, default: timedelta) -> timedelta:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        minutes = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer number of minutes.") from exc
    if minutes < 1:
        raise ValueError(f"{name} must be at least one minute.")
    return timedelta(minutes=minutes)


def _wake_backend(
    url: str,
    *,
    timeout_seconds: float = 90.0,
    transport: httpx.BaseTransport | None = None,
) -> bool:
    try:
        with httpx.Client(
            timeout=timeout_seconds,
            transport=transport,
            follow_redirects=True,
            headers={"User-Agent": "LeetRank-Sync/0.1"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPError:
        return False
    return True


def main() -> int:
    backend_health_url = os.getenv("BACKEND_HEALTH_URL")
    if backend_health_url:
        print(
            json.dumps(
                {
                    "backend_wakeup": (
                        "succeeded" if _wake_backend(backend_health_url) else "failed"
                    )
                },
                sort_keys=True,
            )
        )

    batch_size = _positive_int_from_env("SYNC_BATCH_SIZE", DEFAULT_BATCH_SIZE)
    sync_interval = _positive_minutes_from_env(
        "SYNC_INTERVAL_MINUTES",
        DEFAULT_SYNC_INTERVAL,
    )
    stale_after = _positive_minutes_from_env(
        "SYNC_STALE_AFTER_MINUTES",
        DEFAULT_STALE_AFTER,
    )
    with (
        SessionLocal() as session,
        LeetCodeGraphQLClient() as leetcode_provider,
        GitHubNeetCodeClient() as neetcode_provider,
    ):
        result = sync_due_users(
            session,
            leetcode_provider,
            neetcode_provider=neetcode_provider,
            batch_size=batch_size,
            sync_interval=sync_interval,
            stale_after=stale_after,
        )

    print(json.dumps(asdict(result), default=str, sort_keys=True))
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
