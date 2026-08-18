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

export interface SyncResponse {
  status: string;
  fetched: number;
  new_submissions: number;
  duplicate_submissions: number;
  ignored_before_signup: number;
  points_awarded: number;
}
