import httpx
import pytest
from datetime import timedelta

from app.jobs.sync_due_users import _positive_minutes_from_env, _wake_backend


def test_wake_backend_returns_true_for_successful_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, request=request))

    assert _wake_backend("https://api.example.test/health", transport=transport)


def test_wake_backend_returns_false_for_error_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503, request=request))

    assert not _wake_backend("https://api.example.test/health", transport=transport)


def test_wake_backend_returns_false_for_network_error() -> None:
    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unavailable", request=request)

    assert not _wake_backend(
        "https://api.example.test/health",
        transport=httpx.MockTransport(unavailable),
    )


def test_positive_minutes_from_env_uses_default_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("SYNC_INTERVAL_MINUTES", raising=False)
    assert (
        _positive_minutes_from_env("SYNC_INTERVAL_MINUTES", default=timedelta(minutes=15)).total_seconds()
        == 900
    )


def test_positive_minutes_from_env_rejects_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("SYNC_INTERVAL_MINUTES", "abc")
    with pytest.raises(ValueError):
        _positive_minutes_from_env("SYNC_INTERVAL_MINUTES", default=timedelta(minutes=15))

    monkeypatch.setenv("SYNC_INTERVAL_MINUTES", "0")
    with pytest.raises(ValueError):
        _positive_minutes_from_env("SYNC_INTERVAL_MINUTES", default=timedelta(minutes=15))
