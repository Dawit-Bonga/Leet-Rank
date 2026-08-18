export type PrimaryGoal =
  | "ACCOUNTABILITY"
  | "CONSISTENCY"
  | "COMPETITION"
  | "INTERVIEW_PREP"
  | "LEARNING";

export type LeetCodeExperience = "BEGINNER" | "INTERMEDIATE" | "ADVANCED";
export type LeaderboardPeriod = "week" | "month" | "all_time";

export interface UserProfile {
  id: string;
  username: string;
  display_name: string;
  leetcode_username: string;
  primary_goal: PrimaryGoal;
  leetcode_experience: LeetCodeExperience;
  weekly_problem_goal: number;
  scoring_started_at: string;
  onboarding_completed_at: string;
  sync_status: string;
  last_sync_attempted_at: string | null;
  last_successful_sync_at: string | null;
}

export interface CurrentUser {
  email: string | null;
  onboarding_completed: boolean;
  profile: UserProfile | null;
}

export interface OnboardingPayload {
  username: string;
  display_name: string;
  leetcode_username: string;
  primary_goal: PrimaryGoal;
  leetcode_experience: LeetCodeExperience;
  weekly_problem_goal: number;
}

export interface LeaderboardEntry {
  rank: number;
  user: {
    id: string;
    username: string;
    display_name: string;
  };
  points: number;
  is_current_user: boolean;
}

export interface LeaderboardResponse {
  period: LeaderboardPeriod;
  as_of: string;
  starts_at: string | null;
  entries: LeaderboardEntry[];
}

export interface PublicUserSummary {
  id: string;
  username: string;
  display_name: string;
}

export interface FriendRequestItem {
  id: string;
  user: PublicUserSummary;
  created_at: string;
}

export interface FriendRequestsResponse {
  incoming: FriendRequestItem[];
  outgoing: FriendRequestItem[];
}

export interface FriendsResponse {
  friends: PublicUserSummary[];
}

export interface PeriodScore {
  points: number;
  starts_at: string;
}

export interface ScoresResponse {
  user_id: string;
  as_of: string;
  scores: {
    week: PeriodScore;
    month: PeriodScore;
    all_time: PeriodScore;
  };
}

export interface ActivityItem {
  id: string;
  problem: {
    title: string;
    slug: string;
    difficulty: "EASY" | "MEDIUM" | "HARD";
  };
  points: number;
  reason: "FIRST_SOLVE" | "REVIEW" | "COOLDOWN";
  earned_at: string;
}

export interface ActivityResponse {
  items: ActivityItem[];
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface FriendProfileResponse {
  user: {
    id: string;
    username: string;
    display_name: string;
    leetcode_username: string;
    weekly_problem_goal: number;
    scoring_started_at: string;
  };
  friend_since: string;
  as_of: string;
  scores: {
    week: PeriodScore;
    month: PeriodScore;
    all_time: PeriodScore;
  };
  recent_activity: ActivityItem[];
  activity_has_more: boolean;
}
