from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import User, UserSyncState
from app.services.submission_sync import SubmissionProvider, sync_user_submissions


DEFAULT_SYNC_INTERVAL = timedelta(minutes=15)
DEFAULT_STALE_AFTER = timedelta(minutes=30)
DEFAULT_BATCH_SIZE = 25


@dataclass(frozen=True)
class AutomaticSyncFailure:
    user_id: UUID
    username: str
    error: str


@dataclass(frozen=True)
class AutomaticSyncResult:
    attempted: int
    succeeded: int
    failed: int
    new_submissions: int
    points_awarded: int
    failures: tuple[AutomaticSyncFailure, ...]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def sync_due_users(
    session: Session,
    provider: SubmissionProvider,
    *,
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
            .order_by(UserSyncState.last_attempted_at.asc(), User.id.asc())
            .limit(batch_size)
        ).all()
    )

    succeeded = 0
    new_submissions = 0
    points_awarded = 0
    failures: list[AutomaticSyncFailure] = []

    for user, sync_state in due_accounts:
        if sync_state.sync_status == "RUNNING":
            sync_state.sync_status = "FAILED"
            sync_state.last_error = "Previous synchronization did not finish."
            session.commit()

        try:
            result = sync_user_submissions(
                session,
                provider,
                user_id=user.id,
                now=calculated_at,
            )
            succeeded += 1
            new_submissions += result.new_submissions
            points_awarded += result.points_awarded
        except Exception as exc:
            failures.append(
                AutomaticSyncFailure(
                    user_id=user.id,
                    username=user.username,
                    error=str(exc)[:500],
                )
            )

    return AutomaticSyncResult(
        attempted=len(due_accounts),
        succeeded=succeeded,
        failed=len(failures),
        new_submissions=new_submissions,
        points_awarded=points_awarded,
        failures=tuple(failures),
    )
