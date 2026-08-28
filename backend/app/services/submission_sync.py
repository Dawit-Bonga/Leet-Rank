from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Problem, ScoreEvent, Submission, User, UserProblemStats
from app.models import UserSyncState
from app.services.leetcode import AcceptedSubmission, ProblemDetails
from app.services.scoring import ProblemStatsSnapshot, calculate_score


@dataclass(frozen=True)
class IngestionResult:
    status: str
    points: int = 0
    reason: str | None = None


@dataclass(frozen=True)
class SyncResult:
    status: str
    fetched: int
    new_submissions: int
    duplicate_submissions: int
    ignored_before_signup: int
    points_awarded: int


class SubmissionProvider(Protocol):
    def get_accepted_submissions(self, username: str, limit: int = 20) -> list[AcceptedSubmission]: ...

    def get_problem(self, title_slug: str) -> ProblemDetails: ...


class SyncAlreadyRunningError(Exception):
    pass


class SyncUserNotFoundError(Exception):
    pass


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
    provider: str = "leetcode",
    provider_submission_id: str | None = None,
) -> IngestionResult:
    user = session.get(User, user_id)
    if user is None:
        raise SyncUserNotFoundError("LeetRank user does not exist.")

    submitted_at = _as_utc(submission.submitted_at)
    if submitted_at < _as_utc(user.scoring_started_at):
        return IngestionResult(status="ignored_before_signup")

    provider_event_id = provider_submission_id or submission.external_id
    existing = session.scalar(
        select(Submission).where(
            Submission.provider == provider,
            Submission.provider_submission_id == provider_event_id,
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
        provider=provider,
        provider_submission_id=provider_event_id,
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


def sync_user_submissions(
    session: Session,
    provider: SubmissionProvider,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
    now: datetime | None = None,
) -> SyncResult:
    user = session.get(User, user_id)
    if user is None:
        raise SyncUserNotFoundError("LeetRank user does not exist.")
    provider_name = getattr(provider, "provider_name", "leetcode")

    sync_state = session.get(UserSyncState, user_id)
    if sync_state is None:
        sync_state = UserSyncState(user_id=user_id, sync_status="IDLE")
        session.add(sync_state)
    if sync_state.sync_status == "RUNNING":
        raise SyncAlreadyRunningError("A synchronization is already running for this user.")

    attempted_at = now or datetime.now(UTC)
    if attempted_at.tzinfo is None:
        attempted_at = attempted_at.replace(tzinfo=UTC)
    sync_state.sync_status = "RUNNING"
    sync_state.last_attempted_at = attempted_at
    sync_state.last_error = None
    session.commit()

    try:
        fetched_submissions = provider.get_accepted_submissions(user.leetcode_username, limit=limit)
        fetched_submissions.sort(key=lambda item: item.submitted_at)
        result_counts = {
            "new": 0,
            "duplicate": 0,
            "ignored": 0,
            "points": 0,
        }
        problem_cache: dict[str, ProblemDetails] = {}

        for accepted in fetched_submissions:
            if _as_utc(accepted.submitted_at) < _as_utc(user.scoring_started_at):
                result_counts["ignored"] += 1
                continue

            existing_submission = session.scalar(
                select(Submission.id).where(
                    Submission.provider == provider_name,
                    Submission.provider_submission_id == accepted.external_id,
                )
            )
            if existing_submission is not None:
                result_counts["duplicate"] += 1
                continue

            details = problem_cache.get(accepted.problem_slug)
            if details is None:
                stored_problem = session.scalar(
                    select(Problem).where(Problem.leetcode_slug == accepted.problem_slug)
                )
                if stored_problem is not None:
                    details = ProblemDetails(
                        slug=stored_problem.leetcode_slug,
                        title=stored_problem.title,
                        difficulty=stored_problem.difficulty,
                    )
                else:
                    details = provider.get_problem(accepted.problem_slug)
                problem_cache[accepted.problem_slug] = details

            ingestion = ingest_submission(
                session,
                user_id=user_id,
                submission=accepted,
                problem_details=details,
                provider=provider_name,
                provider_submission_id=accepted.external_id,
            )
            if ingestion.status == "scored":
                result_counts["new"] += 1
                result_counts["points"] += ingestion.points
            elif ingestion.status == "duplicate":
                result_counts["duplicate"] += 1
            else:
                result_counts["ignored"] += 1

        sync_state = session.get(UserSyncState, user_id)
        sync_state.sync_status = "SUCCEEDED"
        sync_state.last_successful_at = attempted_at
        sync_state.last_error = None
        session.commit()
        return SyncResult(
            status="SUCCEEDED",
            fetched=len(fetched_submissions),
            new_submissions=result_counts["new"],
            duplicate_submissions=result_counts["duplicate"],
            ignored_before_signup=result_counts["ignored"],
            points_awarded=result_counts["points"],
        )
    except Exception as exc:
        session.rollback()
        sync_state = session.get(UserSyncState, user_id)
        sync_state.sync_status = "FAILED"
        sync_state.last_error = str(exc)[:500]
        session.commit()
        raise
