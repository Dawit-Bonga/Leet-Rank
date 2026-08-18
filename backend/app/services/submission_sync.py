from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Problem, ScoreEvent, Submission, User, UserProblemStats
from app.services.scoring import ProblemStatsSnapshot, calculate_score


@dataclass(frozen=True)
class AcceptedSubmission:
    external_id: str
    problem_slug: str
    problem_title: str
    submitted_at: datetime


@dataclass(frozen=True)
class ProblemDetails:
    slug: str
    title: str
    difficulty: str


@dataclass(frozen=True)
class IngestionResult:
    status: str
    points: int = 0
    reason: str | None = None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def ingest_submission(
    session: Session,
    *,
    user_id: uuid.UUID,
    submission: AcceptedSubmission,
    problem_details: ProblemDetails,
) -> IngestionResult:
    user = session.get(User, user_id)
    if user is None:
        raise ValueError("User does not exist.")

    submitted_at = _as_utc(submission.submitted_at)
    if submitted_at < _as_utc(user.scoring_started_at):
        return IngestionResult(status="ignored_before_signup")

    existing = session.scalar(
        select(Submission).where(
            Submission.user_id == user_id,
            Submission.external_submission_id == submission.external_id,
        )
    )
    if existing is not None:
        return IngestionResult(status="duplicate")

    problem = session.scalar(select(Problem).where(Problem.leetcode_slug == problem_details.slug))
    if problem is None:
        problem = Problem(
            leetcode_slug=problem_details.slug,
            title=problem_details.title,
            difficulty=problem_details.difficulty.upper(),
        )
        session.add(problem)
        session.flush()

    stats = session.scalar(
        select(UserProblemStats)
        .where(UserProblemStats.user_id == user_id, UserProblemStats.problem_id == problem.id)
        .with_for_update()
    )
    snapshot = None
    if stats is not None:
        snapshot = ProblemStatsSnapshot(
            first_solved_at=_as_utc(stats.first_solved_at),
            last_solved_at=_as_utc(stats.last_solved_at),
            last_rewarded_at=_as_utc(stats.last_rewarded_at),
            rewarded_solve_count=stats.rewarded_solve_count,
        )

    decision = calculate_score(problem.difficulty, submitted_at, snapshot)
    stored_submission = Submission(
        user_id=user_id,
        problem_id=problem.id,
        external_submission_id=submission.external_id,
        submitted_at=submitted_at,
    )
    session.add(stored_submission)
    session.flush()
    session.add(
        ScoreEvent(
            user_id=user_id,
            problem_id=problem.id,
            submission_id=stored_submission.id,
            points=decision.points,
            reason=decision.reason.value,
            earned_at=submitted_at,
        )
    )

    if stats is None:
        stats = UserProblemStats(user_id=user_id, problem_id=problem.id)
        session.add(stats)
    stats.first_solved_at = decision.stats.first_solved_at
    stats.last_solved_at = decision.stats.last_solved_at
    stats.last_rewarded_at = decision.stats.last_rewarded_at
    stats.rewarded_solve_count = decision.stats.rewarded_solve_count

    session.commit()
    return IngestionResult(status="scored", points=decision.points, reason=decision.reason.value)
