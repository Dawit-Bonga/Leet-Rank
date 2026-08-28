import { useEffect, useState } from "react";
import { Award, CalendarDays, Check, Code2, Settings, Share2, Target, Zap } from "lucide-react";
import { Link } from "react-router";

import { ApiError, getActivity, getFriends, getScores } from "../lib/api";
import { countRecentActivity, formatDate, readableLabel } from "../lib/format";
import type {
  ActivityResponse,
  FriendsResponse,
  ScoresResponse,
  UserProfile,
} from "../types/api";
import { ActivityFeed } from "./ActivityFeed";
import { SyncStatus } from "./SyncStatus";
import { UserAvatar } from "./UserAvatar";
import { WeeklyGoalProgress } from "./WeeklyGoalProgress";

interface ProfilePageProps {
  accessToken: string;
  profile: UserProfile;
}

function ProfileDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/6 bg-slate-950/35 px-4 py-3">
      <dt className="text-[0.65rem] font-extrabold uppercase tracking-[0.13em] text-slate-600">
        {label}
      </dt>
      <dd className="mt-1.5 truncate text-sm font-bold text-slate-200">{value}</dd>
    </div>
  );
}

export function ProfilePage({ accessToken, profile }: ProfilePageProps) {
  const [scores, setScores] = useState<ScoresResponse | null>(null);
  const [activity, setActivity] = useState<ActivityResponse | null>(null);
  const [friends, setFriends] = useState<FriendsResponse | null>(null);
  const [scoresLoading, setScoresLoading] = useState(true);
  const [scoresFailed, setScoresFailed] = useState(false);
  const [activityLoading, setActivityLoading] = useState(true);
  const [activityFailed, setActivityFailed] = useState(false);
  const [friendsLoading, setFriendsLoading] = useState(true);
  const [friendsFailed, setFriendsFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shareNotice, setShareNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);

    function reportError(caughtError: unknown) {
      if (!active) return;
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Could not load all profile details.",
      );
    }

    setScoresLoading(true);
    setScoresFailed(false);
    void getScores(accessToken)
      .then((result) => {
        if (active) setScores(result);
      })
      .catch((caughtError) => {
        if (active) setScoresFailed(true);
        reportError(caughtError);
      })
      .finally(() => {
        if (active) setScoresLoading(false);
      });

    setActivityLoading(true);
    setActivityFailed(false);
    void getActivity(accessToken, 100)
      .then((result) => {
        if (active) setActivity(result);
      })
      .catch((caughtError) => {
        if (active) setActivityFailed(true);
        reportError(caughtError);
      })
      .finally(() => {
        if (active) setActivityLoading(false);
      });

    setFriendsLoading(true);
    setFriendsFailed(false);
    void getFriends(accessToken)
      .then((result) => {
        if (active) setFriends(result);
      })
      .catch((caughtError) => {
        if (active) setFriendsFailed(true);
        reportError(caughtError);
      })
      .finally(() => {
        if (active) setFriendsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [accessToken]);

  const weeklyCompleted = countRecentActivity(
    activity?.items.map((item) => item.earned_at) ?? [],
    7,
    scores?.as_of,
  );
  const submissionInputLabel =
    profile.neetcode_repo_owner && profile.neetcode_repo_name
      ? "LeetCode + NeetCode"
      : "LeetCode only";

  async function shareProfile() {
    const url = `${window.location.origin}/u/${profile.username}`;
    try {
      if (navigator.share) {
        await navigator.share({ url });
        setShareNotice("Profile shared.");
      } else {
        await navigator.clipboard.writeText(url);
        setShareNotice("Profile link copied.");
      }
      window.setTimeout(() => setShareNotice(null), 2_500);
    } catch (caughtError) {
      if (!(caughtError instanceof Error && caughtError.name === "AbortError")) {
        setShareNotice("Could not share the profile link.");
      }
    }
  }

  return (
    <main className="page-container">
      <section className="panel panel-accent flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:p-6">
        <UserAvatar highlighted name={profile.display_name} size="lg" />
        <div className="min-w-0 flex-1">
          <p className="eyebrow">Your profile</p>
          <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1 className="truncate text-2xl font-black tracking-tight text-white sm:text-3xl">
              {profile.display_name}
            </h1>
            <p className="text-sm font-semibold text-slate-500">@{profile.username}</p>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="rounded-full border border-white/7 bg-white/4 px-2.5 py-1 text-[0.68rem] font-bold text-slate-400">
              {readableLabel(profile.primary_goal)}
            </span>
            <span className="rounded-full border border-white/7 bg-white/4 px-2.5 py-1 text-[0.68rem] font-bold text-slate-400">
              {readableLabel(profile.leetcode_experience)}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button className="secondary-button px-3 py-2" type="button" onClick={() => void shareProfile()}>
            {shareNotice === "Profile link copied." || shareNotice === "Profile shared." ? (
              <Check aria-hidden="true" size={15} />
            ) : (
              <Share2 aria-hidden="true" size={15} />
            )}
            {shareNotice ?? "Share profile"}
          </button>
          <SyncStatus profile={profile} />
        </div>
      </section>

      {error && <div className="error-banner mt-4">{error}</div>}

      <section className="mt-5 grid gap-3 md:grid-cols-[1.35fr_0.825fr_0.825fr]">
        <div className="metric-card metric-card-primary min-h-36">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="metric-label">Past week</p>
              {scoresLoading ? (
                <div className="mt-3 h-9 w-24 animate-pulse rounded-lg bg-white/5" />
              ) : (
                <p className="metric-value">
                  {scoresFailed ? "—" : (scores?.scores.week.points ?? 0)}
                  <span className="ml-1 text-sm text-slate-500">pts</span>
                </p>
              )}
            </div>
            <span className="icon-chip icon-chip-orange">
              <Zap aria-hidden="true" size={18} />
            </span>
          </div>
          <div className="mt-4 border-t border-white/6 pt-4">
            {activityLoading ? (
              <div className="h-10 animate-pulse rounded-lg bg-white/4" />
            ) : activityFailed ? (
              <p className="text-xs text-slate-500">Weekly progress unavailable</p>
            ) : (
              <WeeklyGoalProgress
                compact
                completed={weeklyCompleted}
                goal={profile.weekly_problem_goal}
              />
            )}
          </div>
        </div>

        <div className="metric-card min-h-36">
          <CalendarDays aria-hidden="true" className="absolute right-4 top-4 text-slate-600" size={25} />
          <p className="metric-label">Past month</p>
          {scoresLoading ? (
            <div className="mt-3 h-9 w-20 animate-pulse rounded-lg bg-white/5" />
          ) : activityFailed ? (
            <div className="empty-compact">Recent activity is temporarily unavailable.</div>
          ) : (
            <p className="metric-value">
              {scoresFailed ? "—" : (scores?.scores.month.points ?? 0)}
              <span className="ml-1 text-sm text-slate-500">pts</span>
            </p>
          )}
          <p className="mt-3 text-xs text-slate-500">Rolling 30-day score</p>
        </div>

        <div className="metric-card min-h-36">
          <Award aria-hidden="true" className="absolute right-4 top-4 text-orange-400/25" size={26} />
          <p className="metric-label">All time</p>
          {scoresLoading ? (
            <div className="mt-3 h-9 w-20 animate-pulse rounded-lg bg-white/5" />
          ) : (
            <p className="metric-value">
              {scoresFailed ? "—" : (scores?.scores.all_time.points ?? 0)}
              <span className="ml-1 text-sm text-slate-500">pts</span>
            </p>
          )}
          <p className="mt-3 text-xs text-slate-500">Since joining LeetRank</p>
        </div>
      </section>

      <div className="mt-5 grid items-start gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <section className="panel">
          <div className="panel-header">
            <div className="flex items-center gap-3">
              <span className="icon-chip">
                <Code2 aria-hidden="true" size={18} />
              </span>
              <div>
                <h2 className="section-heading">Profile details</h2>
                <p className="section-kicker">Your goals and connected account</p>
              </div>
            </div>
          </div>
          <dl className="grid gap-2.5 p-4 sm:grid-cols-2">
            <ProfileDetail label="LeetCode" value={`@${profile.leetcode_username}`} />
            <ProfileDetail label="Submission inputs" value={submissionInputLabel} />
            <ProfileDetail label="Weekly goal" value={`${profile.weekly_problem_goal} problems`} />
            <ProfileDetail label="Primary goal" value={readableLabel(profile.primary_goal)} />
            <ProfileDetail label="Experience" value={readableLabel(profile.leetcode_experience)} />
            {profile.neetcode_repo_owner && profile.neetcode_repo_name && (
              <ProfileDetail
                label="NeetCode repo"
                value={
                  `${profile.neetcode_repo_owner}/${profile.neetcode_repo_name}`
                }
              />
            )}
            <ProfileDetail
              label="Friends"
              value={
                friendsLoading
                  ? "Loading…"
                  : friendsFailed
                    ? "Unavailable"
                    : `${friends?.friends.length ?? 0} / 20`
              }
            />
            <ProfileDetail label="Scoring since" value={formatDate(profile.scoring_started_at)} />
          </dl>
          <div className="flex items-center justify-between gap-4 border-t border-white/6 px-5 py-3.5">
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <Target aria-hidden="true" size={14} />
              <span>Account actions</span>
            </div>
            <Link className="text-button inline-flex items-center gap-2" to="/settings">
              <Settings aria-hidden="true" size={15} />
              Edit settings
            </Link>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="section-heading">Recent activity</h2>
              <p className="section-kicker">Your latest scored submissions</p>
            </div>
            <Zap aria-hidden="true" className="text-orange-400/60" size={18} />
          </div>
          {activityLoading ? (
            <div className="space-y-3 p-4">
              {[0, 1, 2, 3].map((item) => (
                <div className="h-12 animate-pulse rounded-lg bg-white/4" key={item} />
              ))}
            </div>
          ) : (
            <ActivityFeed
              emptyMessage="Your accepted solves will appear here after automatic sync."
              items={activity?.items ?? []}
              limit={8}
            />
          )}
        </section>
      </div>
    </main>
  );
}
