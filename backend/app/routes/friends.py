from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ErrorResponse,
    FriendRequestCreate,
    FriendRequestItem,
    FriendRequestsResponse,
    FriendsResponse,
    LeaderboardEntry,
    LeaderboardPeriod,
    LeaderboardResponse,
    PublicUserSummary,
)
from app.services.friendships import (
    AlreadyFriendsError,
    CannotFriendSelfError,
    FriendLimitReachedError,
    FriendRequestAlreadyExistsError,
    FriendRequestForbiddenError,
    FriendRequestNotFoundError,
    FriendshipNotFoundError,
    FriendshipUserNotFoundError,
    accept_friend_request,
    create_friend_request,
    delete_friend_request,
    list_friend_requests,
    list_friends,
    remove_friend,
)
from app.services.leaderboards import LeaderboardUserNotFoundError, get_friends_leaderboard


router = APIRouter(prefix="/users/{user_id}", tags=["friends"])


def _summary(user) -> PublicUserSummary:
    return PublicUserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
    )


@router.post(
    "/friend-requests",
    response_model=FriendRequestItem,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def send_friend_request(
    user_id: UUID,
    request: FriendRequestCreate,
    session: Session = Depends(get_db),
) -> FriendRequestItem:
    try:
        friend_request, target = create_friend_request(
            session,
            requester_id=user_id,
            target_username=request.username,
        )
    except FriendshipUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc
    except CannotFriendSelfError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "cannot_friend_self", "message": str(exc)},
        ) from exc
    except AlreadyFriendsError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "already_friends", "message": str(exc)},
        ) from exc
    except FriendRequestAlreadyExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "friend_request_exists", "message": str(exc)},
        ) from exc

    return FriendRequestItem(
        id=friend_request.id,
        user=_summary(target),
        created_at=friend_request.created_at,
    )


@router.get(
    "/friend-requests",
    response_model=FriendRequestsResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_friend_requests(
    user_id: UUID,
    session: Session = Depends(get_db),
) -> FriendRequestsResponse:
    try:
        incoming, outgoing = list_friend_requests(session, user_id=user_id)
    except FriendshipUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc

    return FriendRequestsResponse(
        incoming=[
            FriendRequestItem(id=item.id, user=_summary(user), created_at=item.created_at)
            for item, user in incoming
        ],
        outgoing=[
            FriendRequestItem(id=item.id, user=_summary(user), created_at=item.created_at)
            for item, user in outgoing
        ],
    )


@router.post(
    "/friend-requests/{request_id}/accept",
    response_model=PublicUserSummary,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def accept_request(
    user_id: UUID,
    request_id: UUID,
    session: Session = Depends(get_db),
) -> PublicUserSummary:
    try:
        friend = accept_friend_request(session, user_id=user_id, request_id=request_id)
    except FriendshipUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc
    except FriendRequestNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "friend_request_not_found", "message": str(exc)},
        ) from exc
    except FriendRequestForbiddenError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "friend_request_forbidden", "message": str(exc)},
        ) from exc
    except AlreadyFriendsError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "already_friends", "message": str(exc)},
        ) from exc
    except FriendLimitReachedError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "friend_limit_reached", "message": str(exc)},
        ) from exc
    return _summary(friend)


@router.delete(
    "/friend-requests/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def decline_or_cancel_request(
    user_id: UUID,
    request_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    try:
        delete_friend_request(session, user_id=user_id, request_id=request_id)
    except FriendshipUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc
    except FriendRequestNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "friend_request_not_found", "message": str(exc)},
        ) from exc
    except FriendRequestForbiddenError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "friend_request_forbidden", "message": str(exc)},
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/friends",
    response_model=FriendsResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_friends(
    user_id: UUID,
    session: Session = Depends(get_db),
) -> FriendsResponse:
    try:
        friends = list_friends(session, user_id=user_id)
    except FriendshipUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc
    return FriendsResponse(friends=[_summary(friend) for friend in friends])


@router.delete(
    "/friends/{friend_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
def delete_friend(
    user_id: UUID,
    friend_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    try:
        remove_friend(session, user_id=user_id, friend_id=friend_id)
    except FriendshipUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc
    except FriendshipNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "friendship_not_found", "message": str(exc)},
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_leaderboard(
    user_id: UUID,
    period: LeaderboardPeriod = LeaderboardPeriod.WEEK,
    session: Session = Depends(get_db),
) -> LeaderboardResponse:
    try:
        result = get_friends_leaderboard(
            session,
            user_id=user_id,
            period=period.value,
        )
    except LeaderboardUserNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": str(exc)},
        ) from exc

    return LeaderboardResponse(
        period=period,
        as_of=result.as_of,
        starts_at=result.starts_at,
        entries=[
            LeaderboardEntry(
                rank=entry.rank,
                user=PublicUserSummary(
                    id=entry.user_id,
                    username=entry.username,
                    display_name=entry.display_name,
                ),
                points=entry.points,
                is_current_user=entry.is_current_user,
            )
            for entry in result.entries
        ],
    )
