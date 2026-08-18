import { useEffect, useState } from "react";

import { ApiError, getActivity, getFriends, getScores } from "../lib/api";
import { formatDate, formatTimestamp, initials } from "../lib/format";
import type {
  ActivityResponse,
  FriendsResponse,
  ScoresResponse,
  UserProfile,
} from "../types/api";

interface ProfilePageProps {
  accessToken: string;
  profile: UserProfile;
  onSignOut: () => Promise<void>;
}

function readableLabel(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

const difficultyStyles = {
  EASY: "bg-emerald-400/10 text-emerald-300",
  MEDIUM: "bg-amber-400/10 text-amber-300",
  HARD: "bg-red-400/10 text-red-300",
};

export function ProfilePage({ accessToken, profile, onSignOut }: ProfilePageProps) {
  const [scores, setScores] = useState<ScoresResponse | null>(null);
  const [activity, setActivity] = useState<ActivityResponse | null>(null);
  const [friends, setFriends] = useState<FriendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadProfileDetails() {
      setLoading(true);
      setError(null);
      try {
        const [scoreData, activityData, friendData] = await Promise.all([
          getScores(accessToken),
          getActivity(accessToken),
          getFriends(accessToken),
        ]);
        if (!active) return;
        setScores(scoreData);
        setActivity(activityData);
        setFriends(friendData);
      } catch (caughtError) {
        if (!active) return;
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Could not load your profile details.",
        );
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadProfileDetails();
    return () => {
      active = false;
    };
  }, [accessToken]);

  const scoreCards = scores
    ? [
        { label: "Past week", points: scores.scores.week.points },
        { label: "Past month", points: scores.scores.month.points },
        { label: "All time", points: scores.scores.all_time.points },
      ]
    : [];

  return (
    <main className="mx-auto max-w-6xl px-5 pb-28 pt-10 sm:px-8 sm:py-14">
      <section className="flex flex-col gap-6 rounded-3xl border border-white/8 bg-slate-900/70 p-6 sm:flex-row sm:items-center sm:p-8">
        <div className="grid size-20 shrink-0 place-items-center rounded-full border border-orange-400/20 bg-orange-400/10 text-2xl font-black text-orange-300">
          {initials(profile.display_name)}
        </div>
        <div className="min-w-0 flex-1">
          <p className="eyebrow">Your profile</p>
          <h1 className="mt-2 truncate text-3xl font-black tracking-tight sm:text-4xl">
            {profile.display_name}
          </h1>
          <p className="mt-1 text-sm text-slate-400">@{profile.username}</p>
        </div>
        <button className="secondary-button" type="button" onClick={() => void onSignOut()}>
          Sign out
        </button>
      </section>

      {error && <div className="error-banner mt-6">{error}</div>}

      {loading ? (
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div className="h-32 animate-pulse rounded-2xl bg-white/4" key={item} />
          ))}
        </div>
      ) : (
        <>
          <section className="mt-8 grid gap-4 sm:grid-cols-3">
            {scoreCards.map((score) => (
              <div className="stat-card" key={score.label}>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                  {score.label}
                </p>
                <p className="mt-3 text-3xl font-black tabular-nums text-white">
                  {score.points}
                  <span className="ml-1 text-sm font-semibold text-slate-500">pts</span>
                </p>
              </div>
            ))}
          </section>

          <div className="mt-6 grid items-start gap-6 lg:grid-cols-[0.85fr_1.15fr]">
            <section className="social-card">
              <div className="social-card-header">
                <div>
                  <h2 className="text-lg font-black text-white">LeetRank details</h2>
                  <p className="mt-1 text-xs text-slate-500">Your onboarding preferences</p>
                </div>
              </div>
              <dl className="divide-y divide-white/6 px-5">
                <div className="profile-detail-row">
                  <dt>LeetCode</dt>
                  <dd>@{profile.leetcode_username}</dd>
                </div>
                <div className="profile-detail-row">
                  <dt>Primary goal</dt>
                  <dd>{readableLabel(profile.primary_goal)}</dd>
                </div>
                <div className="profile-detail-row">
                  <dt>Experience</dt>
                  <dd>{readableLabel(profile.leetcode_experience)}</dd>
                </div>
                <div className="profile-detail-row">
                  <dt>Weekly goal</dt>
                  <dd>{profile.weekly_problem_goal} problems</dd>
                </div>
                <div className="profile-detail-row">
                  <dt>Friends</dt>
                  <dd>{friends?.friends.length ?? 0} / 20</dd>
                </div>
                <div className="profile-detail-row">
                  <dt>Scoring since</dt>
                  <dd>{formatDate(profile.scoring_started_at)}</dd>
                </div>
                <div className="profile-detail-row">
                  <dt>LeetCode sync</dt>
                  <dd>
                    {profile.sync_status === "RUNNING"
                      ? "Updating now"
                      : profile.sync_status === "FAILED"
                        ? "Retry scheduled"
                        : profile.last_successful_sync_at
                          ? formatTimestamp(profile.last_successful_sync_at)
                          : "Pending"}
                  </dd>
                </div>
              </dl>
            </section>

            <section className="social-card">
              <div className="social-card-header">
                <div>
                  <h2 className="text-lg font-black text-white">Recent activity</h2>
                  <p className="mt-1 text-xs text-slate-500">Your latest scored solves</p>
                </div>
              </div>
              <div className="divide-y divide-white/6 px-5">
                {activity?.items.length ? (
                  activity.items.map((item) => (
                    <div className="flex items-center gap-4 py-4" key={item.id}>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="truncate font-bold text-white">{item.problem.title}</p>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[0.65rem] font-bold ${difficultyStyles[item.problem.difficulty]}`}
                          >
                            {readableLabel(item.problem.difficulty)}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500">
                          {readableLabel(item.reason)} · {formatTimestamp(item.earned_at)}
                        </p>
                      </div>
                      <p className="shrink-0 font-black tabular-nums text-orange-300">
                        +{item.points} pts
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="py-10 text-center text-sm text-slate-500">
                    No scored activity yet. Sync after your next accepted solve.
                  </div>
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </main>
  );
}
