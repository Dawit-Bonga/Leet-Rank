from fastapi.testclient import TestClient

from app.main import app
from app.services import leetcode
import app.routes.users as users_route


client = TestClient(app)


def test_get_user_submissions_success(monkeypatch):
    def fake_fetch_recent_accepted_submissions(username: str, limit: int = 20, timeout_seconds: float = 10.0):
        assert username == "alice"
        return [{"title": "Two Sum", "timestamp": 1723160000}]

    monkeypatch.setattr(users_route, "fetch_recent_accepted_submissions", fake_fetch_recent_accepted_submissions)

    response = client.get("/users/alice/submissions")

    assert response.status_code == 200
    assert response.json() == {
        "username": "alice",
        "submissions": [{"title": "Two Sum", "timestamp": 1723160000}],
    }


def test_get_user_submissions_user_not_found(monkeypatch):
    def fake_fetch_recent_accepted_submissions(username: str, limit: int = 20, timeout_seconds: float = 10.0):
        raise leetcode.UserNotFoundError("LeetCode user does not exist.")

    monkeypatch.setattr(users_route, "fetch_recent_accepted_submissions", fake_fetch_recent_accepted_submissions)

    response = client.get("/users/missing_user/submissions")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "user_not_found"


def test_get_user_submissions_upstream_unavailable(monkeypatch):
    def fake_fetch_recent_accepted_submissions(username: str, limit: int = 20, timeout_seconds: float = 10.0):
        raise leetcode.UpstreamUnavailableError("Could not reach LeetCode.")

    monkeypatch.setattr(users_route, "fetch_recent_accepted_submissions", fake_fetch_recent_accepted_submissions)

    response = client.get("/users/alice/submissions")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "upstream_unavailable"


def test_get_user_submissions_upstream_bad_response(monkeypatch):
    def fake_fetch_recent_accepted_submissions(username: str, limit: int = 20, timeout_seconds: float = 10.0):
        raise leetcode.UpstreamBadResponseError("Unexpected status from LeetCode.")

    monkeypatch.setattr(users_route, "fetch_recent_accepted_submissions", fake_fetch_recent_accepted_submissions)

    response = client.get("/users/alice/submissions")

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "upstream_bad_response"
