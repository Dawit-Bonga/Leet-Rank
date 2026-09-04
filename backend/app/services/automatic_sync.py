from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import User, UserSyncState
from app.services.neetcode_sync import sync_user_neetcode_submissions
from app.services.submission_sync import SubmissionProvider, sync_user_submissions


DEFAULT_SYNC_INTERVAL = timedelta(minutes=15)
DEFAULT_STALE_AFTER = timedelta(minutes=30)
DEFAULT_BATCH_SIZE = 25


@dataclass(frozen=True)
class AutomaticSyncFailure:
    user_id: UUID
    username: str
    provider: str
    error: str


@dataclass(frozen=True)
class LeetCodeSyncSummary:
    fetched: int
    new: int
    duplicates: int
    ignored: int
    points: int


@dataclass(frozen=True)
class NeetCodeSyncSummary:
    fetched: int
    new: int
    duplicates: int
    ignored: int
    unmapped: int
    points: int


@dataclass(frozen=True)
class AutomaticUserSyncResult:
    user_id: UUID
    username: str
    status: str
    leetcode: LeetCodeSyncSummary | None
    neetcode: NeetCodeSyncSummary | None
    failed_provider: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class AutomaticSyncResult:
    attempted: int
    succeeded: int
    failed: int
    new_submissions: int
    points_awarded: int
    failures: tuple[AutomaticSyncFailure, ...]
    users: tuple[AutomaticUserSyncResult, ...]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def sync_due_users(
    session: Session,
    leetcode_provider: SubmissionProvider,
    *,
    neetcode_provider=None,
    now: datetime | None = None,
    sync_interval: timedelta = DEFAULT_SYNC_INTERVAL,
    stale_after: timedelta = DEFAULT_STALE_AFTER,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> AutomaticSyncResult:
    if sync_interval <= timedelta(0):
        raise ValueError("Sync interval must be positive.")
    if stale_after <= sync_interval:
        raise ValueError("Stale-running threshold must exceed the sync interval.")
    if batch_size < 1:
        raise ValueError("Batch size must be at least one.")

    calculated_at = _as_utc(now or datetime.now(UTC))
    due_before = calculated_at - sync_interval
    stale_before = calculated_at - stale_after

    due_accounts = list(
        session.execute(
            select(User, UserSyncState)
            .join(UserSyncState, UserSyncState.user_id == User.id)
            .where(
                or_(
                    and_(
                        UserSyncState.sync_status != "RUNNING",
                        or_(
                            UserSyncState.last_attempted_at.is_(None),
                            UserSyncState.last_attempted_at <= due_before,
                        ),
                    ),
                    and_(
                        UserSyncState.sync_status == "RUNNING",
                        UserSyncState.last_attempted_at <= stale_before,
                    ),
                )
            )
            .order_by(
                UserSyncState.last_attempted_at.asc().nulls_first(),
                User.id.asc(),
            )
            .limit(batch_size)
        ).all()
    )

    succeeded = 0
    new_submissions = 0
    points_awarded = 0
    failures: list[AutomaticSyncFailure] = []
    user_results: list[AutomaticUserSyncResult] = []

    for user, sync_state in due_accounts:
        if sync_state.sync_status == "RUNNING":
            sync_state.sync_status = "FAILED"
            sync_state.last_error = "Previous synchronization did not finish."
            session.commit()

        leetcode_summary: LeetCodeSyncSummary | None = None
        neetcode_summary: NeetCodeSyncSummary | None = None
        active_provider = "leetcode"
        try:
            result = sync_user_submissions(
                session,
                leetcode_provider,
                user_id=user.id,
                now=calculated_at,
            )
            leetcode_summary = LeetCodeSyncSummary(
                fetched=result.fetched,
                new=result.new_submissions,
                duplicates=result.duplicate_submissions,
                ignored=result.ignored_before_signup,
                points=result.points_awarded,
            )
            new_submissions += result.new_submissions
            points_awarded += result.points_awarded
            if neetcode_provider and user.neetcode_repo_owner and user.neetcode_repo_name:
                active_provider = "neetcode"
                neetcode_result = sync_user_neetcode_submissions(
                    session,
                    neetcode_provider,
                    user_id=user.id,
                    problem_provider=leetcode_provider,
                    now=calculated_at,
                )
                neetcode_summary = NeetCodeSyncSummary(
                    fetched=neetcode_result.fetched,
                    new=neetcode_result.new_submissions,
                    duplicates=neetcode_result.duplicate_submissions,
                    ignored=neetcode_result.ignored_before_signup,
                    unmapped=neetcode_result.unmapped_submissions,
                    points=neetcode_result.points_awarded,
                )
                new_submissions += neetcode_result.new_submissions
                points_awarded += neetcode_result.points_awarded
            succeeded += 1
            user_results.append(
                AutomaticUserSyncResult(
                    user_id=user.id,
                    username=user.username,
                    status="SUCCEEDED",
                    leetcode=leetcode_summary,
                    neetcode=neetcode_summary,
                )
            )
        except Exception as exc:
            error = str(exc)[:500]
            failures.append(
                AutomaticSyncFailure(
                    user_id=user.id,
                    username=user.username,
                    provider=active_provider,
                    error=error,
                )
            )
            user_results.append(
                AutomaticUserSyncResult(
                    user_id=user.id,
                    username=user.username,
                    status="FAILED",
                    leetcode=leetcode_summary,
                    neetcode=neetcode_summary,
                    failed_provider=active_provider,
                    error=error,
                )
            )

    return AutomaticSyncResult(
        attempted=len(due_accounts),
        succeeded=succeeded,
        failed=len(failures),
        new_submissions=new_submissions,
        points_awarded=points_awarded,
        failures=tuple(failures),
        users=tuple(user_results),
    )
