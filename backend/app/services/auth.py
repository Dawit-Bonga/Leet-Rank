from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

import httpx


class InvalidAccessTokenError(Exception):
    pass


class AuthServiceUnavailableError(Exception):
    pass


class AuthBadResponseError(Exception):
    pass


@dataclass(frozen=True)
class AuthIdentity:
    id: UUID
    email: str | None


class SupabaseAuthClient:
    def __init__(
        self,
        *,
        project_url: str,
        publishable_key: str,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=project_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "Accept": "application/json",
                "apikey": publishable_key,
                "User-Agent": "LeetClimb/0.1",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SupabaseAuthClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_identity(self, access_token: str) -> AuthIdentity:
        try:
            response = self._client.get(
                "/auth/v1/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.RequestError as exc:
            raise AuthServiceUnavailableError(
                "Could not reach the authentication service."
            ) from exc

        if response.status_code in {401, 403}:
            raise InvalidAccessTokenError("Access token is invalid or expired.")
        if response.status_code >= 500:
            raise AuthServiceUnavailableError(
                "The authentication service is currently unavailable."
            )
        if response.status_code != 200:
            raise AuthBadResponseError(
                "The authentication service returned an unexpected status."
            )

        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            raise AuthBadResponseError(
                "The authentication service returned invalid JSON."
            ) from exc
        if not isinstance(body, dict):
            raise AuthBadResponseError(
                "The authentication service response is malformed."
            )

        try:
            auth_user_id = UUID(str(body["id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthBadResponseError(
                "The authentication service response is missing a valid user ID."
            ) from exc
        email = body.get("email")
        if email is not None and not isinstance(email, str):
            raise AuthBadResponseError(
                "The authentication service response contains an invalid email."
            )
        return AuthIdentity(id=auth_user_id, email=email)
