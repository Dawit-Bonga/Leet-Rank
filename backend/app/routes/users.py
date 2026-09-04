from collections.abc import Generator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_auth_identity, get_current_user
from app.models import User
from app.schemas import (
    ActivityItem,
    ActivityProblem,
    CurrentUserResponse,
    ErrorResponse,
    PeriodScore,
    ScorePeriods,
    UserActivityResponse,
    UserOnboardingRequest,
    UserResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
    UserScoresResponse,
    UserSubmissionsResponse,
)
from app.services.leetcode import (
    LeetCodeGraphQLClient,
    UpstreamBadResponseError,
    UpstreamRateLimitedError,
    UpstreamUnavailableError,
    UserNotFoundError,
    fetch_recent_accepted_submissions,
)
from app.services.auth import AuthIdentity
from app.services.current_account import get_current_account
from app.services.onboarding import (
    AuthUserAlreadyOnboardedError,
    LeetCodeUsernameTakenError,
    LeetClimbUsernameTakenError,
    create_onboarded_user,
)
from app.services.score_reads import ScoreUserNotFoundError, get_user_activity, get_user_scores
from app.services.user_settings import (
    InvalidSettingsError,
    SettingsUserNotFoundError,
    update_user_settings,
)


router = APIRouter(prefix="/users", tags=["users"])


def get_leetcode_client() -> Generator[LeetCodeGraphQLClient, None, None]:
    with LeetCodeGraphQLClient() as client:
        yield client


def _user_response(
    user: User,
    *,
    sync_status: str,
    last_sync_attempted_at: datetime | None = None,
    last_successful_sync_at: datetime | None = None,
) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        leetcode_username=user.leetcode_username,
        primary_goal=user.primary_goal,
        leetcode_experience=user.leetcode_experience,
        weekly_problem_goal=user.weekly_problem_goal,
        submission_source=user.submission_source,
        neetcode_repo_owner=user.neetcode_repo_owner,
        neetcode_repo_name=user.neetcode_repo_name,
        scoring_started_at=user.scoring_started_at,
        onboarding_completed_at=user.onboarding_completed_at,
        sync_status=sync_status,
        last_sync_attempted_at=last_sync_attempted_at,
        last_successful_sync_at=last_successful_sync_at,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    responses={
        401: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_me(
    identity: AuthIdentity = Depends(get_auth_identity),
    session: Session = Depends(get_db),
) -> CurrentUserResponse:
    account = get_current_account(session, auth_user_id=identity.id)
    if account.user is None:
        return CurrentUserResponse(
            email=identity.email,
            onboarding_completed=False,
            profile=None,
        )
    return CurrentUserResponse(
        email=identity.email,
        onboarding_completed=True,
        profile=_user_response(
            account.user,
            sync_status=account.sync_status or "IDLE",
            last_sync_attempted_at=account.last_sync_attempted_at,
            last_successful_sync_at=account.last_successful_sync_at,
        ),
    )


@router.patch(
    "/me/settings",
    response_model=UserSettingsResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_settings(
    request: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> UserSettingsResponse:
    try:
        user = update_user_settings(
            session,
            user_id=current_user.id,
            display_name=request.display_name,
            primary_goal=request.primary_goal.value if request.primary_goal else None,
            leetcode_experience=(
                request.leetcode_experience.value if request.leetcode_experience else None
            ),
            weekly_problem_goal=request.weekly_problem_goal,
            submission_source=(
                request.submission_source.value if request.submission_source else None
            ),
            neetcode_repo_owner=request.neetcode_repo_owner,
            neetcode_repo_name=request.neetcode_repo_name,
            neetcode_accepted_only_confirmed=request.neetcode_accepted_only_confirmed,
        )
    except SettingsUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc
    except InvalidSettingsError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_settings", "message": str(exc)},
        ) from exc

    return UserSettingsResponse(
        display_name=user.display_name,
        primary_goal=user.primary_goal,
        leetcode_experience=user.leetcode_experience,
        weekly_problem_goal=user.weekly_problem_goal,
        submission_source=user.submission_source,
        neetcode_repo_owner=user.neetcode_repo_owner,
        neetcode_repo_name=user.neetcode_repo_name,
    )


@router.post(
    "/me/onboarding",
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
    identity: AuthIdentity = Depends(get_auth_identity),
) -> UserResponse:
    try:
        user, sync_state = create_onboarded_user(
            session,
            leetcode_client,
            auth_user_id=identity.id,
            username=request.username,
            display_name=request.display_name,
            leetcode_username=request.leetcode_username,
            primary_goal=request.primary_goal.value,
            leetcode_experience=request.leetcode_experience.value,
            weekly_problem_goal=request.weekly_problem_goal,
            neetcode_repo_owner=request.neetcode_repo_owner,
            neetcode_repo_name=request.neetcode_repo_name,
        )
    except AuthUserAlreadyOnboardedError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "profile_exists", "message": str(exc)},
        ) from exc
    except LeetClimbUsernameTakenError as exc:
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

    return _user_response(
        user,
        sync_status=sync_state.sync_status,
        last_sync_attempted_at=sync_state.last_attempted_at,
        last_successful_sync_at=sync_state.last_successful_at,
    )


@router.get(
    "/me/scores",
    response_model=UserScoresResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_scores(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> UserScoresResponse:
    try:
        result = get_user_scores(session, user_id=current_user.id)
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
    "/me/activity",
    response_model=UserActivityResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_activity(
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> UserActivityResponse:
    try:
        result = get_user_activity(
            session,
            user_id=current_user.id,
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
                provider=item.provider,
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
