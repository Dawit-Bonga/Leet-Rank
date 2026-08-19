from __future__ import annotations

import json
import os
from dataclasses import asdict

import httpx

from app.database import SessionLocal
from app.services.automatic_sync import DEFAULT_BATCH_SIZE, sync_due_users
from app.services.leetcode import LeetCodeGraphQLClient


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
    with SessionLocal() as session, LeetCodeGraphQLClient() as provider:
        result = sync_due_users(session, provider, batch_size=batch_size)

    print(json.dumps(asdict(result), default=str, sort_keys=True))
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
