from fastapi import APIRouter, HTTPException

from app.schemas import ErrorResponse, UserSubmissionsResponse
from app.services.leetcode import (
    UpstreamBadResponseError,
    UpstreamUnavailableError,
    UserNotFoundError,
    fetch_recent_accepted_submissions,
)


router = APIRouter(prefix="/users", tags=["users"])


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
