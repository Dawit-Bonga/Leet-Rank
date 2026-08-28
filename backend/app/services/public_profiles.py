from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class PublicProfileNotFoundError(Exception):
    pass


def get_public_profile(session: Session, *, username: str) -> User:
    normalized_username = username.strip().lower()
    user = session.scalar(select(User).where(User.username == normalized_username))
    if user is None:
        raise PublicProfileNotFoundError("No LeetClimb user has that username.")
    return user
