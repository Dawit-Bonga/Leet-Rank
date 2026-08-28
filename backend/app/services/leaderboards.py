from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Friendship, ScoreEvent, User


@dataclass(frozen=True)
class LeaderboardEntryResult:
    rank: int
    user_id: UUID
    username: str
    display_name: str
    points: int
    is_current_user: bool


@dataclass(frozen=True)
class LeaderboardResult:
    period: str
    as_of: datetime
    starts_at: datetime | None
    entries: list[LeaderboardEntryResult]


class LeaderboardUserNotFoundError(Exception):
    pass


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_friends_leaderboard(
    session: Session,
    *,
    user_id: UUID,
    period: str,
    as_of: datetime | None = None,
) -> LeaderboardResult:
    if session.get(User, user_id) is None:
        raise LeaderboardUserNotFoundError("LeetClimb user does not exist.")

    calculated_at = _as_utc(as_of or datetime.now(UTC))
    starts_at = {
        "week": calculated_at - timedelta(days=7),
        "month": calculated_at - timedelta(days=30),
        "all_time": None,
    }.get(period)
    if period not in {"week", "month", "all_time"}:
        raise ValueError("Unsupported leaderboard period.")

    friend_ids = list(
        session.scalars(
            select(Friendship.friend_id).where(Friendship.user_id == user_id)
        ).all()
    )
    participant_ids = [user_id, *friend_ids]
    users = list(
        session.scalars(select(User).where(User.id.in_(participant_ids))).all()
    )

    score_query = (
        select(ScoreEvent.user_id, func.coalesce(func.sum(ScoreEvent.points), 0))
        .where(
            ScoreEvent.user_id.in_(participant_ids),
            ScoreEvent.earned_at <= calculated_at,
        )
        .group_by(ScoreEvent.user_id)
    )
    if starts_at is not None:
        score_query = score_query.where(ScoreEvent.earned_at >= starts_at)
    points_by_user = {
        score_user_id: int(points)
        for score_user_id, points in session.execute(score_query).all()
    }

    ordered_users = sorted(
        users,
        key=lambda user: (-points_by_user.get(user.id, 0), user.username),
    )
    entries: list[LeaderboardEntryResult] = []
    previous_points: int | None = None
    current_rank = 0
    for position, user in enumerate(ordered_users, start=1):
        points = points_by_user.get(user.id, 0)
        if points != previous_points:
            current_rank = position
            previous_points = points
        entries.append(
            LeaderboardEntryResult(
                rank=current_rank,
                user_id=user.id,
                username=user.username,
                display_name=user.display_name,
                points=points,
                is_current_user=user.id == user_id,
            )
        )

    return LeaderboardResult(
        period=period,
        as_of=calculated_at,
        starts_at=starts_at,
        entries=entries,
    )
