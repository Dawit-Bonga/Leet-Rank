from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "primary_goal IS NULL OR primary_goal IN "
            "('ACCOUNTABILITY', 'CONSISTENCY', 'COMPETITION', 'INTERVIEW_PREP', 'LEARNING')",
            name="ck_users_primary_goal",
        ),
        CheckConstraint(
            "leetcode_experience IS NULL OR leetcode_experience IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name="ck_users_leetcode_experience",
        ),
        CheckConstraint(
            "weekly_problem_goal IS NULL OR weekly_problem_goal BETWEEN 1 AND 100",
            name="ck_users_weekly_problem_goal",
        ),
        CheckConstraint("length(username) BETWEEN 3 AND 30", name="ck_users_username_length"),
        CheckConstraint("username = lower(username)", name="ck_users_username_lowercase"),
        CheckConstraint(
            "submission_source IN ('leetcode', 'github_neetcode')",
            name="ck_users_submission_source",
        ),
        CheckConstraint(
            "(neetcode_repo_owner IS NULL AND neetcode_repo_name IS NULL) "
            "OR (neetcode_repo_owner IS NOT NULL AND neetcode_repo_name IS NOT NULL)",
            name="ck_users_neetcode_repo_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    auth_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    leetcode_username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    primary_goal: Mapped[str | None] = mapped_column(String(24))
    leetcode_experience: Mapped[str | None] = mapped_column(String(16))
    weekly_problem_goal: Mapped[int | None] = mapped_column(Integer)
    submission_source: Mapped[str] = mapped_column(String(32), nullable=False, default="leetcode")
    neetcode_repo_owner: Mapped[str | None] = mapped_column(String(100))
    neetcode_repo_name: Mapped[str | None] = mapped_column(String(100))
    scoring_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (CheckConstraint("difficulty IN ('EASY', 'MEDIUM', 'HARD')", name="ck_problems_difficulty"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    leetcode_slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint("provider IN ('leetcode', 'github_neetcode')", name="ck_submissions_provider"),
        UniqueConstraint("provider", "provider_submission_id", name="uq_submissions_provider_event"),
        Index("ix_submissions_user_submitted_at", "user_id", "submitted_at"),
        Index("ix_submissions_provider_event", "provider", "provider_submission_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problems.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="leetcode")
    provider_submission_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_submission_id: Mapped[str] = mapped_column(String(64), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserProblemStats(Base):
    __tablename__ = "user_problem_stats"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    problem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    first_solved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_solved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_rewarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rewarded_solve_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ScoreEvent(Base):
    __tablename__ = "score_events"
    __table_args__ = (
        CheckConstraint("reason IN ('FIRST_SOLVE', 'REVIEW', 'COOLDOWN')", name="ck_score_events_reason"),
        CheckConstraint("points >= 0", name="ck_score_events_points_nonnegative"),
        Index("ix_score_events_user_earned_at", "user_id", "earned_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problems.id"), nullable=False)
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(16), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserSyncState(Base):
    __tablename__ = "user_sync_state"
    __table_args__ = (CheckConstraint("sync_status IN ('IDLE', 'RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_sync_status"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_status: Mapped[str] = mapped_column(String(16), nullable=False, default="IDLE")
    last_error: Mapped[str | None] = mapped_column(String(500))


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (CheckConstraint("user_id <> friend_id", name="ck_friendships_not_self"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    friend_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FriendRequest(Base):
    __tablename__ = "friend_requests"
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_friend_requests_direction"),
        CheckConstraint("requester_id <> addressee_id", name="ck_friend_requests_not_self"),
        Index("ix_friend_requests_addressee_created_at", "addressee_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    addressee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UnmappedSubmission(Base):
    __tablename__ = "unmapped_submissions"
    __table_args__ = (
        CheckConstraint("provider IN ('leetcode', 'github_neetcode')", name="ck_unmapped_submissions_provider"),
        UniqueConstraint("provider", "provider_submission_id", name="uq_unmapped_submissions_provider_event"),
        Index("ix_unmapped_submissions_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_submission_id: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_title: Mapped[str] = mapped_column(String(255), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(String(4000))
    last_error: Mapped[str | None] = mapped_column(String(500))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
