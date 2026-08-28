from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Problem, ScoreEvent, User


@dataclass(frozen=True)
class PeriodScoreResult:
    points: int
    starts_at: datetime


@dataclass(frozen=True)
class UserScoresResult:
    user_id: uuid.UUID
    as_of: datetime
    week: PeriodScoreResult
    month: PeriodScoreResult
    all_time: PeriodScoreResult


@dataclass(frozen=True)
class ActivityItemResult:
    id: uuid.UUID
    problem_title: str
    problem_slug: str
    difficulty: str
    points: int
    reason: str
    earned_at: datetime


@dataclass(frozen=True)
class UserActivityResult:
    items: list[ActivityItemResult]
    limit: int
    offset: int
    has_more: bool


class ScoreUserNotFoundError(Exception):
    pass


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_user_scores(
    session: Session,
    *,
    user_id: uuid.UUID,
    as_of: datetime | None = None,
) -> UserScoresResult:
    user = session.get(User, user_id)
    if user is None:
        raise ScoreUserNotFoundError("LeetClimb user does not exist.")

    calculated_at = _as_utc(as_of or datetime.now(UTC))
    week_start = calculated_at - timedelta(days=7)
    month_start = calculated_at - timedelta(days=30)

    totals = session.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            ScoreEvent.earned_at.between(week_start, calculated_at),
                            ScoreEvent.points,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            ScoreEvent.earned_at.between(month_start, calculated_at),
                            ScoreEvent.points,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (ScoreEvent.earned_at <= calculated_at, ScoreEvent.points),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(ScoreEvent.user_id == user_id)
    ).one()

    return UserScoresResult(
        user_id=user.id,
        as_of=calculated_at,
        week=PeriodScoreResult(points=int(totals[0]), starts_at=week_start),
        month=PeriodScoreResult(points=int(totals[1]), starts_at=month_start),
        all_time=PeriodScoreResult(
            points=int(totals[2]),
            starts_at=_as_utc(user.scoring_started_at),
        ),
    )


def get_user_activity(
    session: Session,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> UserActivityResult:
    if session.get(User, user_id) is None:
        raise ScoreUserNotFoundError("LeetClimb user does not exist.")

    rows = session.execute(
        select(ScoreEvent, Problem)
        .join(Problem, Problem.id == ScoreEvent.problem_id)
        .where(ScoreEvent.user_id == user_id)
        .order_by(ScoreEvent.earned_at.desc(), ScoreEvent.id.desc())
        .limit(limit + 1)
        .offset(offset)
    ).all()
    has_more = len(rows) > limit
    items = [
        ActivityItemResult(
            id=event.id,
            problem_title=problem.title,
            problem_slug=problem.leetcode_slug,
            difficulty=problem.difficulty,
            points=event.points,
            reason=event.reason,
            earned_at=_as_utc(event.earned_at),
        )
        for event, problem in rows[:limit]
    ]
    return UserActivityResult(
        items=items,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )
