from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class SubmissionSource(StrEnum):
    LEETCODE = "leetcode"
    GITHUB_NEETCODE = "github_neetcode"


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
    last_sync_attempted_at: datetime | None
    last_successful_sync_at: datetime | None


class CurrentUserResponse(BaseModel):
    email: str | None
    onboarding_completed: bool
    profile: UserResponse | None


class UserSettingsUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    primary_goal: PrimaryGoal | None = None
    leetcode_experience: LeetCodeExperience | None = None
    weekly_problem_goal: int | None = Field(default=None, ge=1, le=100)
    submission_source: SubmissionSource | None = None
    neetcode_repo_owner: str | None = Field(default=None, min_length=1, max_length=100)
    neetcode_repo_name: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name cannot be empty.")
        return normalized

    @field_validator("neetcode_repo_owner", "neetcode_repo_name")
    @classmethod
    def normalize_repo_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Repository fields cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "UserSettingsUpdate":
        if all(
            value is None
            for value in (
                self.display_name,
                self.primary_goal,
                self.leetcode_experience,
                self.weekly_problem_goal,
                self.submission_source,
                self.neetcode_repo_owner,
                self.neetcode_repo_name,
            )
        ):
            raise ValueError("At least one setting must be provided.")
        return self


class UserSettingsResponse(BaseModel):
    display_name: str
    primary_goal: PrimaryGoal
    leetcode_experience: LeetCodeExperience
    weekly_problem_goal: int
    submission_source: SubmissionSource
    neetcode_repo_owner: str | None
    neetcode_repo_name: str | None


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


class SharedProfileResponse(BaseModel):
    id: UUID
    username: str
    display_name: str
    leetcode_username: str
    weekly_problem_goal: int
    joined_at: datetime


class FriendRequestItem(BaseModel):
    id: UUID
    user: PublicUserSummary
    created_at: datetime


class FriendRequestsResponse(BaseModel):
    incoming: list[FriendRequestItem]
    outgoing: list[FriendRequestItem]


class FriendsResponse(BaseModel):
    friends: list[PublicUserSummary]


class FriendsOverviewResponse(BaseModel):
    friends: list[PublicUserSummary]
    incoming: list[FriendRequestItem]
    outgoing: list[FriendRequestItem]
    as_of: datetime


class UserRelationship(StrEnum):
    NONE = "NONE"
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"
    FRIEND = "FRIEND"


class UserSearchItem(BaseModel):
    user: PublicUserSummary
    relationship: UserRelationship
    friend_request_id: UUID | None


class UserSearchResponse(BaseModel):
    users: list[UserSearchItem]


class FriendProfileUser(BaseModel):
    id: UUID
    username: str
    display_name: str
    leetcode_username: str
    weekly_problem_goal: int
    scoring_started_at: datetime


class FriendProfileResponse(BaseModel):
    user: FriendProfileUser
    friend_since: datetime
    as_of: datetime
    scores: ScorePeriods
    recent_activity: list[ActivityItem]
    activity_has_more: bool


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
