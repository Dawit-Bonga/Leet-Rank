from collections.abc import Generator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ErrorResponse, UserOnboardingRequest, UserResponse, UserSubmissionsResponse, UserSyncResponse
from app.services.leetcode import (
    AlfaLeetCodeClient,
    UpstreamBadResponseError,
    UpstreamRateLimitedError,
    UpstreamUnavailableError,
    UserNotFoundError,
    fetch_recent_accepted_submissions,
)
from app.services.onboarding import LeetCodeUsernameTakenError, create_onboarded_user
from app.services.submission_sync import (
    SyncAlreadyRunningError,
    SyncUserNotFoundError,
    sync_user_submissions,
)


router = APIRouter(prefix="/users", tags=["users"])


def get_leetcode_client() -> Generator[AlfaLeetCodeClient, None, None]:
    with AlfaLeetCodeClient() as client:
        yield client


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def create_user(
    request: UserOnboardingRequest,
    session: Session = Depends(get_db),
    leetcode_client: AlfaLeetCodeClient = Depends(get_leetcode_client),
) -> UserResponse:
    try:
        user, sync_state = create_onboarded_user(
            session,
            leetcode_client,
            display_name=request.display_name,
            leetcode_username=request.leetcode_username,
            primary_goal=request.primary_goal.value,
            leetcode_experience=request.leetcode_experience.value,
            weekly_problem_goal=request.weekly_problem_goal,
        )
    except LeetCodeUsernameTakenError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "leetcode_username_taken", "message": str(exc)},
        ) from exc
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_leetcode_username", "message": str(exc)},
        ) from exc
    except UpstreamRateLimitedError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "upstream_rate_limited", "message": str(exc)},
        ) from exc
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "upstream_unavailable", "message": str(exc)},
        ) from exc
    except UpstreamBadResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_bad_response", "message": str(exc)},
        ) from exc

    return UserResponse(
        id=user.id,
        display_name=user.display_name,
        leetcode_username=user.leetcode_username,
        primary_goal=user.primary_goal,
        leetcode_experience=user.leetcode_experience,
        weekly_problem_goal=user.weekly_problem_goal,
        scoring_started_at=user.scoring_started_at,
        onboarding_completed_at=user.onboarding_completed_at,
        sync_status=sync_state.sync_status,
    )


@router.post(
    "/{user_id}/sync",
    response_model=UserSyncResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def sync_user(
    user_id: UUID,
    session: Session = Depends(get_db),
    leetcode_client: AlfaLeetCodeClient = Depends(get_leetcode_client),
) -> UserSyncResponse:
    try:
        result = sync_user_submissions(
            session,
            leetcode_client,
            user_id=user_id,
        )
    except SyncUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc
    except SyncAlreadyRunningError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "sync_already_running", "message": str(exc)},
        ) from exc
    except UpstreamRateLimitedError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "upstream_rate_limited", "message": str(exc)},
        ) from exc
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "upstream_unavailable", "message": str(exc)},
        ) from exc
    except UpstreamBadResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_bad_response", "message": str(exc)},
        ) from exc

    return UserSyncResponse(**result.__dict__)


@router.get(
    "/{username}/submissions",
    response_model=UserSubmissionsResponse,
    responses={
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def get_user_submissions(username: str) -> UserSubmissionsResponse:
    try:
        submissions = fetch_recent_accepted_submissions(username=username)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "upstream_unavailable", "message": str(exc)},
        ) from exc
    except UpstreamBadResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "upstream_bad_response", "message": str(exc)},
        ) from exc

    return UserSubmissionsResponse(username=username, submissions=submissions)
