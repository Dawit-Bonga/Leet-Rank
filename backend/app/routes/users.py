from collections.abc import Generator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ActivityItem,
    ActivityProblem,
    ErrorResponse,
    PeriodScore,
    ScorePeriods,
    UserActivityResponse,
    UserOnboardingRequest,
    UserResponse,
    UserScoresResponse,
    UserSubmissionsResponse,
    UserSyncResponse,
)
from app.services.leetcode import (
    LeetCodeGraphQLClient,
    UpstreamBadResponseError,
    UpstreamRateLimitedError,
    UpstreamUnavailableError,
    UserNotFoundError,
    fetch_recent_accepted_submissions,
)
from app.services.onboarding import (
    LeetCodeUsernameTakenError,
    LeetRankUsernameTakenError,
    create_onboarded_user,
)
from app.services.score_reads import ScoreUserNotFoundError, get_user_activity, get_user_scores
from app.services.submission_sync import (
    SyncAlreadyRunningError,
    SyncUserNotFoundError,
    sync_user_submissions,
)


router = APIRouter(prefix="/users", tags=["users"])


def get_leetcode_client() -> Generator[LeetCodeGraphQLClient, None, None]:
    with LeetCodeGraphQLClient() as client:
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
    leetcode_client: LeetCodeGraphQLClient = Depends(get_leetcode_client),
) -> UserResponse:
    try:
        user, sync_state = create_onboarded_user(
            session,
            leetcode_client,
            username=request.username,
            display_name=request.display_name,
            leetcode_username=request.leetcode_username,
            primary_goal=request.primary_goal.value,
            leetcode_experience=request.leetcode_experience.value,
            weekly_problem_goal=request.weekly_problem_goal,
        )
    except LeetRankUsernameTakenError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "username_taken", "message": str(exc)},
        ) from exc
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
        username=user.username,
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
    leetcode_client: LeetCodeGraphQLClient = Depends(get_leetcode_client),
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
    "/{user_id}/scores",
    response_model=UserScoresResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_scores(
    user_id: UUID,
    session: Session = Depends(get_db),
) -> UserScoresResponse:
    try:
        result = get_user_scores(session, user_id=user_id)
    except ScoreUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc

    return UserScoresResponse(
        user_id=result.user_id,
        as_of=result.as_of,
        scores=ScorePeriods(
            week=PeriodScore(**result.week.__dict__),
            month=PeriodScore(**result.month.__dict__),
            all_time=PeriodScore(**result.all_time.__dict__),
        ),
    )


@router.get(
    "/{user_id}/activity",
    response_model=UserActivityResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_activity(
    user_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> UserActivityResponse:
    try:
        result = get_user_activity(
            session,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
    except ScoreUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc

    return UserActivityResponse(
        items=[
            ActivityItem(
                id=item.id,
                problem=ActivityProblem(
                    title=item.problem_title,
                    slug=item.problem_slug,
                    difficulty=item.difficulty,
                ),
                points=item.points,
                reason=item.reason,
                earned_at=item.earned_at,
            )
            for item in result.items
        ],
        limit=result.limit,
        offset=result.offset,
        has_more=result.has_more,
    )


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
