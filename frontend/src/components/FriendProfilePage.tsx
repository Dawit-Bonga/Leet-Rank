import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Award,
  CalendarDays,
  ExternalLink,
  ShieldCheck,
  Trophy,
  Zap,
} from "lucide-react";
import { Link, useParams } from "react-router";

import { ApiError, getFriendProfile, getLeaderboard } from "../lib/api";
import { countRecentActivity, formatDate } from "../lib/format";
import type { FriendProfileResponse, LeaderboardEntry } from "../types/api";
import { ActivityFeed } from "./ActivityFeed";
import { UserAvatar } from "./UserAvatar";
import { WeeklyGoalProgress } from "./WeeklyGoalProgress";

interface FriendProfilePageProps {
  accessToken: string;
}

export function FriendProfilePage({ accessToken }: FriendProfilePageProps) {
  const { friendId } = useParams<{ friendId: string }>();
  const [profile, setProfile] = useState<FriendProfileResponse | null>(null);
  const [rankEntry, setRankEntry] = useState<LeaderboardEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!friendId) {
      setError("Friend profile does not exist.");
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    void getFriendProfile(accessToken, friendId)
      .then((result) => {
        if (active) setProfile(result);
      })
      .catch((caughtError) => {
        if (!active) return;
        setProfile(null);
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Could not load this friend’s profile.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    // Rank is supplemental. The profile remains useful if this request fails.
    void getLeaderboard(accessToken, "week")
      .then((leaderboard) => {
        if (active) {
          setRankEntry(
            leaderboard.entries.find((entry) => entry.user.id === friendId) ?? null,
          );
        }
      })
      .catch(() => {
        if (active) setRankEntry(null);
      });

    return () => {
      active = false;
    };
  }, [accessToken, friendId]);

  if (loading && !profile) {
    return (
      <main className="page-container">
        <div className="h-44 animate-pulse rounded-2xl bg-white/4" />
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div className="h-32 animate-pulse rounded-2xl bg-white/4" key={item} />
          ))}
        </div>
      </main>
    );
  }

  if (!profile || error) {
    return (
      <main className="page-container">
        <section className="panel mx-auto max-w-xl p-7 text-center">
          <p className="text-xl font-black text-white">Friend profile unavailable</p>
          <p className="mt-2 text-sm text-slate-400">
            {error ?? "This profile is no longer available to you."}
          </p>
          <Link className="secondary-button mt-6" to="/friends">
            <ArrowLeft aria-hidden="true" size={16} />
            Back to friends
          </Link>
        </section>
      </main>
    );
  }

  const weeklyCompleted = countRecentActivity(
    profile.recent_activity.map((item) => item.earned_at),
    7,
    profile.as_of,
  );
  const leetcodeUrl = `https://leetcode.com/u/${encodeURIComponent(profile.user.leetcode_username)}/`;

  return (
    <main className="page-container">
      <Link
        className="mb-4 inline-flex items-center gap-2 text-sm font-bold text-slate-500 transition hover:text-white"
        to="/friends"
      >
        <ArrowLeft aria-hidden="true" size={16} />
        Back to friends
      </Link>

      <section className="panel panel-accent flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:p-6">
        <UserAvatar highlighted name={profile.user.display_name} size="lg" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="eyebrow">Friend profile</p>
            <ShieldCheck aria-label="Visible to friends" className="text-orange-400/70" size={14} />
          </div>
          <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1 className="truncate text-2xl font-black tracking-tight text-white sm:text-3xl">
              {profile.user.display_name}
            </h1>
            <p className="text-sm font-semibold text-slate-500">@{profile.user.username}</p>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Friends since {formatDate(profile.friend_since)}
          </p>
        </div>
        <a
          className="secondary-button shrink-0"
          href={leetcodeUrl}
          rel="noreferrer"
          target="_blank"
        >
          @{profile.user.leetcode_username}
          <ExternalLink aria-hidden="true" size={15} />
        </a>
      </section>

      <section className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="metric-card metric-card-primary">
          <Trophy aria-hidden="true" className="absolute right-4 top-4 text-orange-400/35" size={27} />
          <p className="metric-label">Friend rank</p>
          <p className="metric-value">{rankEntry ? `#${rankEntry.rank}` : "—"}</p>
          <p className="mt-1 text-xs text-slate-500">In your weekly circle</p>
        </div>
        <div className="metric-card">
          <Zap aria-hidden="true" className="absolute right-4 top-4 text-orange-400/30" size={26} />
          <p className="metric-label">Past week</p>
          <p className="metric-value">
            {profile.scores.week.points}<span className="ml-1 text-sm text-slate-500">pts</span>
          </p>
          <p className="mt-1 text-xs text-slate-500">Rolling seven-day score</p>
        </div>
        <div className="metric-card">
          <CalendarDays aria-hidden="true" className="absolute right-4 top-4 text-slate-600" size={25} />
          <p className="metric-label">Past month</p>
          <p className="metric-value">
            {profile.scores.month.points}<span className="ml-1 text-sm text-slate-500">pts</span>
          </p>
          <p className="mt-1 text-xs text-slate-500">Rolling 30-day score</p>
        </div>
        <div className="metric-card">
          <Award aria-hidden="true" className="absolute right-4 top-4 text-orange-400/25" size={26} />
          <p className="metric-label">All time</p>
          <p className="metric-value">
            {profile.scores.all_time.points}<span className="ml-1 text-sm text-slate-500">pts</span>
          </p>
          <p className="mt-1 text-xs text-slate-500">Since joining LeetRank</p>
        </div>
      </section>

      <div className="mt-5 grid items-start gap-5 lg:grid-cols-[19rem_minmax(0,1fr)]">
        <WeeklyGoalProgress
          completed={weeklyCompleted}
          goal={profile.user.weekly_problem_goal}
        />
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="section-heading">Recent activity</h2>
              <p className="section-kicker">Latest scored submissions</p>
            </div>
            <Zap aria-hidden="true" className="text-orange-400/60" size={18} />
          </div>
          <ActivityFeed
            emptyMessage={`${profile.user.display_name} has no scored activity yet.`}
            items={profile.recent_activity}
            limit={8}
          />
        </section>
      </div>

      <p className="mt-5 flex items-center justify-end gap-2 text-[0.68rem] text-slate-600">
        <ShieldCheck aria-hidden="true" size={13} />
        This limited performance profile is visible because you’re friends.
      </p>
    </main>
  );
}
