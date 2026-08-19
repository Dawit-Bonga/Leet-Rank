from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ErrorResponse, SharedProfileResponse
from app.services.public_profiles import PublicProfileNotFoundError, get_public_profile


router = APIRouter(prefix="/users/public", tags=["public profiles"])


@router.get(
    "/{username}",
    response_model=SharedProfileResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_shared_profile(
    username: str = Path(
        min_length=3,
        max_length=30,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_]*$",
    ),
    session: Session = Depends(get_db),
) -> SharedProfileResponse:
    try:
        user = get_public_profile(session, username=username)
    except PublicProfileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "profile_not_found", "message": str(exc)},
        ) from exc

    return SharedProfileResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        leetcode_username=user.leetcode_username,
        weekly_problem_goal=user.weekly_problem_goal,
        joined_at=user.created_at,
    )
