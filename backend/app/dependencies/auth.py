from __future__ import annotations

import os
from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import (
    AuthBadResponseError,
    AuthIdentity,
    AuthServiceUnavailableError,
    InvalidAccessTokenError,
    SupabaseAuthClient,
)


bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_client() -> Generator[SupabaseAuthClient, None, None]:
    project_url = os.getenv("SUPABASE_URL")
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if not project_url or not publishable_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "auth_not_configured",
                "message": "Supabase authentication is not configured.",
            },
        )
    with SupabaseAuthClient(
        project_url=project_url,
        publishable_key=publishable_key,
    ) as client:
        yield client


def get_auth_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_client: SupabaseAuthClient = Depends(get_auth_client),
) -> AuthIdentity:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "Sign in is required."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return auth_client.get_identity(credentials.credentials)
    except InvalidAccessTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_access_token", "message": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AuthServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "auth_unavailable", "message": str(exc)},
        ) from exc
    except AuthBadResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "auth_bad_response", "message": str(exc)},
        ) from exc


def get_current_user(
    identity: AuthIdentity = Depends(get_auth_identity),
    session: Session = Depends(get_db),
) -> User:
    user = session.scalar(select(User).where(User.auth_user_id == identity.id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "onboarding_required",
                "message": "Complete LeetClimb onboarding before using this endpoint.",
            },
        )
    return user
