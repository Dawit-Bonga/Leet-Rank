from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Submission, UnmappedSubmission, User, UserSyncState
from app.services.leetcode import AcceptedSubmission, ProblemDetails
from app.services.problem_resolution import (
    ProblemDetailsProvider,
    queue_unmapped_submission,
    resolve_problem_by_slug,
    retry_unmapped_submissions,
)
from app.services.submission_sync import IngestionResult, SyncAlreadyRunningError, SyncUserNotFoundError, ingest_submission


NEETCODE_PROVIDER = "github_neetcode"
GITHUB_SYNC_OVERLAP = timedelta(minutes=5)


@dataclass(frozen=True)
class NeetCodeSubmissionEvent:
    provider_submission_id: str
    problem_slug: str
    problem_title: str
    submitted_at: datetime
    repository: str
    commit_sha: str
    file_path: str


@dataclass(frozen=True)
class NeetCodeSyncResult:
    status: str
    fetched: int
    new_submissions: int
    duplicate_submissions: int
    ignored_before_signup: int
    unmapped_submissions: int
    points_awarded: int


class NeetCodeSubmissionProvider(Protocol):
    provider_name: str

    def get_recent_accepted_submissions(
        self,
        *,
        owner: str,
        repo: str,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[NeetCodeSubmissionEvent]: ...


class NeetCodeIntegrationNotConfiguredError(Exception):
    pass


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_ingestion_result(
    session: Session,
    *,
    user_id: uuid.UUID,
    event: NeetCodeSubmissionEvent,
    problem_provider: ProblemDetailsProvider | None = None,
) -> IngestionResult | None:
    lookup = resolve_problem_by_slug(session, event.problem_slug)
    if lookup.problem is None and problem_provider is not None:
        try:
            details = problem_provider.get_problem(
                lookup.normalized_slug or event.problem_slug
            )
        except Exception:
            # Fall back to non-blocking unmapped queue when metadata resolution fails.
            pass
        else:
            return ingest_submission(
                session,
                user_id=user_id,
                submission=AcceptedSubmission(
                    external_id=event.provider_submission_id,
                    problem_slug=details.slug,
                    problem_title=details.title,
                    submitted_at=_as_utc(event.submitted_at),
                ),
                problem_details=details,
                provider=NEETCODE_PROVIDER,
                provider_submission_id=event.provider_submission_id,
            )

    if lookup.problem is None:
        queue_unmapped_submission(
            session,
            user_id=user_id,
            provider=NEETCODE_PROVIDER,
            provider_submission_id=event.provider_submission_id,
            problem_slug=lookup.normalized_slug or event.problem_slug,
            problem_title=event.problem_title,
            submitted_at=_as_utc(event.submitted_at),
            metadata={
                "repository": event.repository,
                "commit_sha": event.commit_sha,
                "file_path": event.file_path,
            },
        )
        return None

    return ingest_submission(
        session,
        user_id=user_id,
        submission=AcceptedSubmission(
            external_id=event.provider_submission_id,
            problem_slug=lookup.problem.leetcode_slug,
            problem_title=lookup.problem.title,
            submitted_at=_as_utc(event.submitted_at),
        ),
        problem_details=ProblemDetails(
            slug=lookup.problem.leetcode_slug,
            title=lookup.problem.title,
            difficulty=lookup.problem.difficulty,
        ),
        provider=NEETCODE_PROVIDER,
        provider_submission_id=event.provider_submission_id,
    )


def sync_user_neetcode_submissions(
    session: Session,
    provider: NeetCodeSubmissionProvider,
    *,
    user_id: uuid.UUID,
    problem_provider: ProblemDetailsProvider | None = None,
    limit: int = 100,
    now: datetime | None = None,
) -> NeetCodeSyncResult:
    user = session.get(User, user_id)
    if user is None:
        raise SyncUserNotFoundError("LeetClimb user does not exist.")
    if not user.neetcode_repo_owner or not user.neetcode_repo_name:
        raise NeetCodeIntegrationNotConfiguredError("NeetCode repository is not configured.")

    sync_state = session.get(UserSyncState, user_id)
    if sync_state is None:
        sync_state = UserSyncState(user_id=user_id, sync_status="IDLE")
        session.add(sync_state)
    if sync_state.sync_status == "RUNNING":
        raise SyncAlreadyRunningError("A synchronization is already running for this user.")

    attempted_at = _as_utc(now or datetime.now(UTC))
    sync_state.sync_status = "RUNNING"
    sync_state.last_attempted_at = attempted_at
    sync_state.last_error = None
    session.commit()

    try:
        latest_submission_at = session.scalar(
            select(func.max(Submission.submitted_at)).where(
                Submission.user_id == user_id,
                Submission.provider == NEETCODE_PROVIDER,
            )
        )
        latest_unmapped_at = session.scalar(
            select(func.max(UnmappedSubmission.submitted_at)).where(
                UnmappedSubmission.user_id == user_id,
                UnmappedSubmission.provider == NEETCODE_PROVIDER,
            )
        )
        known_timestamps = [
            _as_utc(value)
            for value in (latest_submission_at, latest_unmapped_at)
            if value is not None
        ]
        since = max(known_timestamps) - GITHUB_SYNC_OVERLAP if known_timestamps else None

        events = provider.get_recent_accepted_submissions(
            owner=user.neetcode_repo_owner,
            repo=user.neetcode_repo_name,
            limit=limit,
            since=since,
        )
        events.sort(key=lambda item: item.submitted_at)
        result_counts = {
            "new": 0,
            "duplicate": 0,
            "ignored": 0,
            "unmapped": 0,
            "points": 0,
        }

        for event in events:
            submitted_at = _as_utc(event.submitted_at)
            if submitted_at < _as_utc(user.scoring_started_at):
                result_counts["ignored"] += 1
                continue

            existing_submission = session.scalar(
                select(Submission.id).where(
                    Submission.provider == NEETCODE_PROVIDER,
                    Submission.provider_submission_id == event.provider_submission_id,
                )
            )
            if existing_submission is not None:
                result_counts["duplicate"] += 1
                continue

            ingestion = _to_ingestion_result(
                session,
                user_id=user_id,
                event=event,
                problem_provider=problem_provider,
            )
            if ingestion is None:
                result_counts["unmapped"] += 1
                continue
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
        # Retry older unmapped rows now that metadata provider is available.
        if problem_provider is not None:
            retry_unmapped_submissions(
                session,
                problem_provider=problem_provider,
                user_id=user_id,
            )
        session.commit()
        return NeetCodeSyncResult(
            status="SUCCEEDED",
            fetched=len(events),
            new_submissions=result_counts["new"],
            duplicate_submissions=result_counts["duplicate"],
            ignored_before_signup=result_counts["ignored"],
            unmapped_submissions=result_counts["unmapped"],
            points_awarded=result_counts["points"],
        )
    except Exception as exc:
        session.rollback()
        sync_state = session.get(UserSyncState, user_id)
        sync_state.sync_status = "FAILED"
        sync_state.last_error = str(exc)[:500]
        session.commit()
        raise
