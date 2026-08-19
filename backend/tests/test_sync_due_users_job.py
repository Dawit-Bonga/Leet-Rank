import httpx

from app.jobs.sync_due_users import _wake_backend


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
