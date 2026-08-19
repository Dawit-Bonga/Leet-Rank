import { useCallback, useEffect, useState } from "react";
import { Crown, Medal, RefreshCw, Sparkles, Trophy, TrendingUp, Zap } from "lucide-react";
import { Link } from "react-router";

import { ApiError, getActivity, getLeaderboard } from "../lib/api";
import { countRecentActivity, formatTimestamp } from "../lib/format";
import type {
  ActivityResponse,
  LeaderboardPeriod,
  LeaderboardResponse,
  UserProfile,
} from "../types/api";
import { ActivityFeed } from "./ActivityFeed";
import { SyncStatus } from "./SyncStatus";
import { UserAvatar } from "./UserAvatar";
import { WeeklyActivityChart } from "./WeeklyActivityChart";

interface LeaderboardDashboardProps {
  accessToken: string;
  profile: UserProfile;
}

const periods: Array<{ value: LeaderboardPeriod; label: string; shortLabel: string }> = [
  { value: "week", label: "Past week", shortLabel: "7-day" },
  { value: "month", label: "Past month", shortLabel: "30-day" },
  { value: "all_time", label: "All time", shortLabel: "All-time" },
];

export function LeaderboardDashboard({ accessToken, profile }: LeaderboardDashboardProps) {
  const [period, setPeriod] = useState<LeaderboardPeriod>("week");
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null);
  const [activity, setActivity] = useState<ActivityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activityLoading, setActivityLoading] = useState(true);
  const [activityFailed, setActivityFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadLeaderboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setLeaderboard(await getLeaderboard(accessToken, period));
    } catch (caughtError) {
      setLeaderboard(null);
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Could not load the leaderboard.",
      );
    } finally {
      setLoading(false);
    }
  }, [accessToken, period]);

  useEffect(() => {
    void loadLeaderboard();
  }, [loadLeaderboard]);

  useEffect(() => {
    let active = true;
    setActivityLoading(true);
    setActivityFailed(false);
    void getActivity(accessToken, 100)
      .then((result) => {
        if (active) setActivity(result);
      })
      .catch(() => {
        if (active) {
          setActivity(null);
          setActivityFailed(true);
        }
      })
      .finally(() => {
        if (active) setActivityLoading(false);
      });
    return () => {
      active = false;
    };
  }, [accessToken]);

  const currentEntry = leaderboard?.entries.find((entry) => entry.is_current_user);
  const leader = leaderboard?.entries[0];
  const gapToLeader =
    currentEntry && leader ? Math.max(leader.points - currentEntry.points, 0) : null;
  const displayedPeriod = leaderboard?.period ?? period;
  const selectedPeriod = periods.find((item) => item.value === displayedPeriod) ?? periods[0];
  const weeklyCompleted = countRecentActivity(
    activity?.items.map((item) => item.earned_at) ?? [],
    7,
    leaderboard?.as_of,
  );

  return (
    <main className="page-container">
      <section className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div>
          <p className="eyebrow">Friends leaderboard</p>
          <h1 className="page-title mt-2">Keep climbing, {profile.display_name.split(" ")[0]}.</h1>
          <p className="page-description">
            Your competition, weekly momentum, and latest scored solves in one place.
          </p>
        </div>
        <SyncStatus profile={profile} />
      </section>

      {error && <div className="error-banner mt-5">{error}</div>}

      <section className="mt-6 grid gap-3 sm:grid-cols-3">
        <div className="metric-card metric-card-primary">
          <Trophy aria-hidden="true" className="absolute right-4 top-4 text-orange-400/35" size={28} />
          <p className="metric-label">Your rank</p>
          <p className="metric-value">{currentEntry ? `#${currentEntry.rank}` : "—"}</p>
          <p className="mt-1 text-xs text-slate-500">
            Among {leaderboard?.entries.length ?? 0} players
          </p>
        </div>
        <div className="metric-card">
          <Zap aria-hidden="true" className="absolute right-4 top-4 text-orange-400/30" size={27} />
          <p className="metric-label">{selectedPeriod.shortLabel} score</p>
          <p className="metric-value">
            {currentEntry?.points ?? 0}
            <span className="ml-1 text-sm text-slate-500">pts</span>
          </p>
          <p className="mt-1 text-xs text-slate-500">Accepted solves and eligible reviews</p>
        </div>
        <div className="metric-card">
          <TrendingUp aria-hidden="true" className="absolute right-4 top-4 text-slate-600" size={27} />
          <p className="metric-label">Race to first</p>
          <p className="metric-value">
            {gapToLeader === null ? "—" : gapToLeader === 0 ? "Leading" : `${gapToLeader} pts`}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {gapToLeader === 0 ? "You set the pace." : "Gap to the current leader"}
          </p>
        </div>
      </section>

      {activityLoading ? (
        <div className="mt-5 h-72 animate-pulse rounded-2xl bg-white/4" />
      ) : activityFailed ? (
        <section className="panel mt-5 p-5 text-center text-xs text-slate-500">
          Seven-day activity is temporarily unavailable.
        </section>
      ) : (
        <WeeklyActivityChart
          asOf={leaderboard?.as_of}
          completed={weeklyCompleted}
          goal={profile.weekly_problem_goal}
          items={activity?.items ?? []}
        />
      )}

      <div className="mt-5 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_19rem]">
        <section className="panel" aria-busy={loading}>
          <div className="panel-header flex-col items-stretch sm:flex-row sm:items-center">
            <div className="flex rounded-xl border border-white/5 bg-slate-950/65 p-1">
              {periods.map((option) => (
                <button
                  className={`period-tab ${period === option.value ? "period-tab-active" : ""}`}
                  key={option.value}
                  type="button"
                  onClick={() => setPeriod(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <div className="flex items-center justify-end gap-2 text-xs text-slate-500">
              {loading && leaderboard && (
                <RefreshCw aria-label="Refreshing leaderboard" className="animate-spin" size={13} />
              )}
              {leaderboard && <span>Calculated {formatTimestamp(leaderboard.as_of)}</span>}
            </div>
          </div>

          <div className="grid grid-cols-[3rem_1fr_auto] gap-3 border-b border-white/6 bg-slate-950/22 px-5 py-2.5 text-[0.64rem] font-extrabold uppercase tracking-[0.16em] text-slate-600 sm:grid-cols-[4rem_1fr_8rem] sm:px-6">
            <span>Rank</span>
            <span>Player</span>
            <span className="text-right">Points</span>
          </div>

          {loading && !leaderboard ? (
            <div className="space-y-2 p-4 sm:p-5">
              {[0, 1, 2, 3].map((item) => (
                <div className="h-16 animate-pulse rounded-xl bg-white/4" key={item} />
              ))}
            </div>
          ) : leaderboard ? (
            <div
              className={`leaderboard-content-enter ${loading ? "opacity-70 transition-opacity" : "transition-opacity"}`}
              key={leaderboard.period}
            >
              {leaderboard.entries.map((entry) => (
                <Link
                  className={`leaderboard-row ${entry.rank <= 3 ? "leaderboard-row-top" : ""} ${entry.rank === 1 ? "leaderboard-row-first" : ""} ${entry.is_current_user ? "leaderboard-row-current" : ""}`}
                  key={entry.user.id}
                  to={entry.is_current_user ? "/profile" : `/friends/${entry.user.id}`}
                >
                  <div className="flex items-center">
                    <span className={`rank-badge ${entry.rank === 1 ? "rank-badge-first" : entry.rank === 2 ? "rank-badge-second" : entry.rank === 3 ? "rank-badge-third" : ""}`}>
                      {entry.rank === 1 ? <Crown aria-label="First place" size={16} /> : entry.rank}
                    </span>
                  </div>
                  <div className="flex min-w-0 items-center gap-3">
                    <UserAvatar highlighted={entry.is_current_user} name={entry.user.display_name} size="sm" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-extrabold text-white sm:text-base">
                          {entry.user.display_name}
                        </p>
                        {entry.rank > 1 && entry.rank <= 3 && (
                          <Medal aria-label={`Rank ${entry.rank}`} className="text-slate-500" size={14} />
                        )}
                        {entry.is_current_user && (
                          <span className="rounded-full bg-orange-400/10 px-2 py-0.5 text-[0.58rem] font-extrabold uppercase tracking-wider text-orange-300">
                            You
                          </span>
                        )}
                      </div>
                      <p className="truncate text-xs text-slate-500">@{entry.user.username}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xl font-black tabular-nums text-white">{entry.points}</span>
                    <span className="ml-1 text-xs text-slate-500">pts</span>
                  </div>
                </Link>
              ))}
              {leaderboard.entries.length === 1 && (
                <div className="flex flex-wrap items-center justify-center gap-2 border-t border-white/6 px-5 py-4 text-xs text-slate-500">
                  <Sparkles aria-hidden="true" size={14} />
                  <span>Add a friend to turn this into a competition.</span>
                  <Link className="font-bold text-orange-400 hover:text-orange-300" to="/friends">
                    Find friends
                  </Link>
                </div>
              )}
            </div>
          ) : activityFailed ? (
            <div className="panel p-5 text-xs text-slate-500">
              Weekly progress is temporarily unavailable.
            </div>
          ) : (
            <div className="empty-compact py-10">No leaderboard data available.</div>
          )}
        </section>

        <aside className="space-y-5">
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2 className="section-heading">Recent activity</h2>
                <p className="section-kicker">Latest scored submissions</p>
              </div>
              <Zap aria-hidden="true" className="text-orange-400/60" size={18} />
            </div>
            {activityLoading ? (
              <div className="space-y-3 p-4">
                {[0, 1, 2].map((item) => (
                  <div className="h-12 animate-pulse rounded-lg bg-white/4" key={item} />
                ))}
              </div>
            ) : activityFailed ? (
              <div className="empty-compact">Recent activity is temporarily unavailable.</div>
            ) : (
              <ActivityFeed
                emptyMessage="Your latest solve will appear here after automatic sync."
                items={activity?.items ?? []}
                limit={4}
              />
            )}
          </section>
        </aside>
      </div>

      <footer className="mt-5 text-right text-[0.68rem] text-slate-600">
        Scores count from {formatTimestamp(profile.scoring_started_at)}
      </footer>
    </main>
  );
}
