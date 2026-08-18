from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserSyncState


@dataclass(frozen=True)
class CurrentAccountResult:
    user: User | None
    sync_status: str | None


def get_current_account(
    session: Session,
    *,
    auth_user_id: UUID,
) -> CurrentAccountResult:
    row = session.execute(
        select(User, UserSyncState.sync_status)
        .outerjoin(UserSyncState, UserSyncState.user_id == User.id)
        .where(User.auth_user_id == auth_user_id)
    ).one_or_none()
    if row is None:
        return CurrentAccountResult(user=None, sync_status=None)
    user, sync_status = row
    return CurrentAccountResult(user=user, sync_status=sync_status or "IDLE")
