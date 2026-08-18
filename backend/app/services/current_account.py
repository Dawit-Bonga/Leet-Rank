from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserSyncState


@dataclass(frozen=True)
class CurrentAccountResult:
    user: User | None
    sync_status: str | None
    last_sync_attempted_at: datetime | None
    last_successful_sync_at: datetime | None


def get_current_account(
    session: Session,
    *,
    auth_user_id: UUID,
) -> CurrentAccountResult:
    row = session.execute(
        select(
            User,
            UserSyncState.sync_status,
            UserSyncState.last_attempted_at,
            UserSyncState.last_successful_at,
        )
        .outerjoin(UserSyncState, UserSyncState.user_id == User.id)
        .where(User.auth_user_id == auth_user_id)
    ).one_or_none()
    if row is None:
        return CurrentAccountResult(
            user=None,
            sync_status=None,
            last_sync_attempted_at=None,
            last_successful_sync_at=None,
        )
    user, sync_status, last_attempted_at, last_successful_at = row
    return CurrentAccountResult(
        user=user,
        sync_status=sync_status or "IDLE",
        last_sync_attempted_at=last_attempted_at,
        last_successful_sync_at=last_successful_at,
    )
