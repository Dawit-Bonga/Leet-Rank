from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Submission(BaseModel):
    title: str
    timestamp: int


class UserSubmissionsResponse(BaseModel):
    username: str
    submissions: list[Submission]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail


class PrimaryGoal(StrEnum):
    ACCOUNTABILITY = "ACCOUNTABILITY"
    CONSISTENCY = "CONSISTENCY"
    COMPETITION = "COMPETITION"
    INTERVIEW_PREP = "INTERVIEW_PREP"
    LEARNING = "LEARNING"


class LeetCodeExperience(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class UserOnboardingRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=30,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_]*$",
    )
    display_name: str = Field(min_length=1, max_length=100)
    leetcode_username: str = Field(min_length=1, max_length=64)
    primary_goal: PrimaryGoal
    leetcode_experience: LeetCodeExperience
    weekly_problem_goal: int = Field(ge=1, le=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    display_name: str
    leetcode_username: str
    primary_goal: PrimaryGoal
    leetcode_experience: LeetCodeExperience
    weekly_problem_goal: int
    scoring_started_at: datetime
    onboarding_completed_at: datetime
    sync_status: str


class UserSyncResponse(BaseModel):
    status: str
    fetched: int
    new_submissions: int
    duplicate_submissions: int
    ignored_before_signup: int
    points_awarded: int


class PeriodScore(BaseModel):
    points: int
    starts_at: datetime


class ScorePeriods(BaseModel):
    week: PeriodScore
    month: PeriodScore
    all_time: PeriodScore


class UserScoresResponse(BaseModel):
    user_id: UUID
    as_of: datetime
    scores: ScorePeriods


class ActivityProblem(BaseModel):
    title: str
    slug: str
    difficulty: str


class ActivityItem(BaseModel):
    id: UUID
    problem: ActivityProblem
    points: int
    reason: str
    earned_at: datetime


class UserActivityResponse(BaseModel):
    items: list[ActivityItem]
    limit: int
    offset: int
    has_more: bool


class FriendRequestCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=30,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_]*$",
    )


class PublicUserSummary(BaseModel):
    id: UUID
    username: str
    display_name: str


class FriendRequestItem(BaseModel):
    id: UUID
    user: PublicUserSummary
    created_at: datetime


class FriendRequestsResponse(BaseModel):
    incoming: list[FriendRequestItem]
    outgoing: list[FriendRequestItem]


class FriendsResponse(BaseModel):
    friends: list[PublicUserSummary]


class LeaderboardPeriod(StrEnum):
    WEEK = "week"
    MONTH = "month"
    ALL_TIME = "all_time"


class LeaderboardEntry(BaseModel):
    rank: int
    user: PublicUserSummary
    points: int
    is_current_user: bool


class LeaderboardResponse(BaseModel):
    period: LeaderboardPeriod
    as_of: datetime
    starts_at: datetime | None
    entries: list[LeaderboardEntry]
