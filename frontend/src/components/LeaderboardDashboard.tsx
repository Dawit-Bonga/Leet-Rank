import { useCallback, useEffect, useState } from "react";

import { ApiError, getLeaderboard, syncLeetCode } from "../lib/api";
import type {
  LeaderboardPeriod,
  LeaderboardResponse,
  SyncResponse,
  UserProfile,
} from "../types/api";
import { Brand } from "./Brand";

interface LeaderboardDashboardProps {
  accessToken: string;
  email: string | null;
  profile: UserProfile;
  onSignOut: () => Promise<void>;
}

const periods: Array<{ value: LeaderboardPeriod; label: string }> = [
  { value: "week", label: "Past week" },
  { value: "month", label: "Past month" },
  { value: "all_time", label: "All time" },
];

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function LeaderboardDashboard({
  accessToken,
  email,
  profile,
  onSignOut,
}: LeaderboardDashboardProps) {
  const [period, setPeriod] = useState<LeaderboardPeriod>("week");
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const loadLeaderboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setLeaderboard(await getLeaderboard(accessToken, period));
    } catch (caughtError) {
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

  async function handleSync() {
    setSyncing(true);
    setError(null);
    setSyncMessage(null);
    try {
      const result: SyncResponse = await syncLeetCode(accessToken);
      const solveLabel = result.new_submissions === 1 ? "solve" : "solves";
      setSyncMessage(
        result.new_submissions > 0
          ? `${result.new_submissions} new ${solveLabel} found · ${result.points_awarded} points added`
          : "You’re already up to date.",
      );
      await loadLeaderboard();
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Sync failed. Try again.");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/6 bg-slate-950/90 px-5 py-4 backdrop-blur sm:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Brand compact />
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-white">{profile.display_name}</p>
              <p className="text-xs text-slate-500">@{profile.username}</p>
            </div>
            <div className="grid size-10 place-items-center rounded-full border border-orange-400/20 bg-orange-400/10 text-sm font-bold text-orange-300">
              {initials(profile.display_name)}
            </div>
            <button className="text-button" type="button" onClick={() => void onSignOut()}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
        <section className="flex flex-col justify-between gap-7 md:flex-row md:items-end">
          <div>
            <p className="eyebrow">Friends leaderboard</p>
            <h1 className="mt-3 text-4xl font-black tracking-tight sm:text-5xl">
              Keep climbing, {profile.display_name.split(" ")[0]}.
            </h1>
            <p className="mt-3 max-w-2xl text-slate-400">
              Every accepted solve after joining earns its place here. Your leaderboard
              includes you and all accepted friends.
            </p>
          </div>
          <button
            className="secondary-button shrink-0"
            type="button"
            onClick={() => void handleSync()}
            disabled={syncing}
          >
            <span className={syncing ? "inline-block animate-spin" : ""}>↻</span>
            {syncing ? "Syncing…" : "Sync LeetCode"}
          </button>
        </section>

        {syncMessage && <div className="success-banner mt-7">{syncMessage}</div>}
        {error && <div className="error-banner mt-7">{error}</div>}

        <section className="mt-9 overflow-hidden rounded-3xl border border-white/8 bg-slate-900/70 shadow-2xl shadow-black/20">
          <div className="flex flex-col gap-5 border-b border-white/8 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
            <div className="flex rounded-xl bg-slate-950/70 p-1">
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
            {leaderboard && (
              <p className="text-xs text-slate-500">
                Updated {formatTimestamp(leaderboard.as_of)}
              </p>
            )}
          </div>

          <div className="grid grid-cols-[3rem_1fr_auto] gap-3 border-b border-white/6 px-5 py-3 text-[0.68rem] font-bold uppercase tracking-[0.16em] text-slate-600 sm:grid-cols-[4rem_1fr_8rem] sm:px-7">
            <span>Rank</span>
            <span>Player</span>
            <span className="text-right">Points</span>
          </div>

          {loading ? (
            <div className="space-y-3 p-5 sm:p-7">
              {[0, 1, 2].map((item) => (
                <div className="h-16 animate-pulse rounded-xl bg-white/4" key={item} />
              ))}
            </div>
          ) : leaderboard ? (
            <div>
              {leaderboard.entries.map((entry) => (
                <div
                  className={`leaderboard-row ${entry.is_current_user ? "leaderboard-row-current" : ""}`}
                  key={entry.user.id}
                >
                  <div className="flex items-center">
                    <span
                      className={`rank-badge ${entry.rank === 1 ? "rank-badge-first" : ""}`}
                    >
                      {entry.rank}
                    </span>
                  </div>
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="grid size-10 shrink-0 place-items-center rounded-full bg-slate-800 text-xs font-bold text-slate-300">
                      {initials(entry.user.display_name)}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="truncate font-bold text-white">{entry.user.display_name}</p>
                        {entry.is_current_user && (
                          <span className="rounded-full bg-orange-400/10 px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wider text-orange-300">
                            You
                          </span>
                        )}
                      </div>
                      <p className="truncate text-xs text-slate-500">@{entry.user.username}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xl font-black tabular-nums text-white">
                      {entry.points}
                    </span>
                    <span className="ml-1 text-xs text-slate-500">pts</span>
                  </div>
                </div>
              ))}
              {leaderboard.entries.length === 1 && (
                <div className="border-t border-white/6 px-6 py-5 text-center text-sm text-slate-500">
                  Add a friend to turn this into a competition.
                </div>
              )}
            </div>
          ) : (
            <div className="p-10 text-center text-sm text-slate-500">
              No leaderboard data available.
            </div>
          )}
        </section>

        <footer className="mt-6 flex flex-col justify-between gap-2 text-xs text-slate-600 sm:flex-row">
          <span>Signed in as {email || profile.username}</span>
          <span>Scores count from {formatTimestamp(profile.scoring_started_at)}</span>
        </footer>
      </div>
    </main>
  );
}
