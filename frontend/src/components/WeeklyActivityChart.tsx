import { BarChart3, Target } from "lucide-react";

import type { ActivityItem } from "../types/api";

interface WeeklyActivityChartProps {
  items: ActivityItem[];
  completed: number;
  goal: number;
  asOf?: string;
}

type Difficulty = ActivityItem["problem"]["difficulty"];

interface ActivityDay {
  key: string;
  label: string;
  dateLabel: string;
  solves: number;
  points: number;
  difficultyPoints: Record<Difficulty, number>;
}

const difficulties: Array<{
  value: Difficulty;
  label: string;
  segmentClass: string;
  dotClass: string;
}> = [
  {
    value: "EASY",
    label: "Easy",
    segmentClass: "weekly-chart-segment-easy",
    dotClass: "bg-teal-400",
  },
  {
    value: "MEDIUM",
    label: "Medium",
    segmentClass: "weekly-chart-segment-medium",
    dotClass: "bg-amber-400",
  },
  {
    value: "HARD",
    label: "Hard",
    segmentClass: "weekly-chart-segment-hard",
    dotClass: "bg-rose-400",
  },
];

function dateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildActivityDays(items: ActivityItem[], asOf?: string): ActivityDay[] {
  const end = asOf ? new Date(asOf) : new Date();
  const endTimestamp = end.getTime();
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(end);
    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() - (6 - index));
    return {
      key: dateKey(date),
      label: new Intl.DateTimeFormat(undefined, { weekday: "short" }).format(date),
      dateLabel: new Intl.DateTimeFormat(undefined, {
        weekday: "long",
        month: "short",
        day: "numeric",
      }).format(date),
      solves: 0,
      points: 0,
      difficultyPoints: { EASY: 0, MEDIUM: 0, HARD: 0 },
    } satisfies ActivityDay;
  });
  const daysByKey = new Map(days.map((day) => [day.key, day]));

  items.forEach((item) => {
    const earnedAt = new Date(item.earned_at);
    if (earnedAt.getTime() > endTimestamp) return;
    const day = daysByKey.get(dateKey(earnedAt));
    if (!day) return;
    day.solves += 1;
    day.points += item.points;
    day.difficultyPoints[item.problem.difficulty] += item.points;
  });
  return days;
}

export function WeeklyActivityChart({
  items,
  completed,
  goal,
  asOf,
}: WeeklyActivityChartProps) {
  const days = buildActivityDays(items, asOf);
  const maxPoints = Math.max(...days.map((day) => day.points), 1);
  const totalPoints = days.reduce((total, day) => total + day.points, 0);
  const goalPercentage = Math.min((completed / Math.max(goal, 1)) * 100, 100);
  const difficultySolves = Object.fromEntries(
    difficulties.map(({ value }) => [
      value,
      items.filter((item) => {
        const itemDate = new Date(item.earned_at);
        return itemDate.getTime() <= (asOf ? new Date(asOf).getTime() : Date.now())
          && days.some((day) => day.key === dateKey(itemDate))
          && item.problem.difficulty === value;
      }).length,
    ]),
  ) as Record<Difficulty, number>;

  return (
    <section className="panel mt-5">
      <div className="panel-header flex-col items-stretch sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <span className="icon-chip icon-chip-teal">
            <BarChart3 aria-hidden="true" size={18} />
          </span>
          <div>
            <h2 className="section-heading">Seven-day activity</h2>
            <p className="section-kicker">Daily points and difficulty mix</p>
          </div>
        </div>
        <div className="min-w-52">
          <div className="flex items-center justify-between gap-4 text-xs">
            <span className="flex items-center gap-1.5 font-bold text-slate-500">
              <Target aria-hidden="true" size={13} /> Weekly goal
            </span>
            <strong className="tabular-nums text-slate-200">
              {completed}<span className="text-slate-600">/{goal} solves</span>
            </strong>
          </div>
          <div
            aria-label={`${Math.min(completed, goal)} of ${goal} weekly solves completed`}
            aria-valuemax={goal}
            aria-valuemin={0}
            aria-valuenow={Math.min(completed, goal)}
            className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-950/80"
            role="progressbar"
          >
            <div
              className="h-full rounded-full bg-gradient-to-r from-teal-600 to-teal-300 shadow-[0_0_12px_rgba(45,212,191,0.25)] transition-[width] duration-500"
              style={{ width: `${goalPercentage}%` }}
            />
          </div>
        </div>
      </div>

      <div className="px-4 pb-4 pt-5 sm:px-6 sm:pb-5">
        <div className="grid h-48 grid-cols-7 gap-2 sm:gap-4" role="img" aria-label="Points earned on each of the last seven days">
          {days.map((day) => {
            const barHeight = day.points > 0
              ? Math.max((day.points / maxPoints) * 100, 12)
              : 0;
            const accessibleLabel = `${day.dateLabel}: ${day.solves} ${day.solves === 1 ? "solve" : "solves"}, ${day.points} points`;
            return (
              <div className="flex min-w-0 flex-col items-center" key={day.key}>
                <span className="mb-2 h-4 text-[0.6rem] font-black tabular-nums text-slate-500 sm:text-[0.68rem]">
                  {day.points > 0 ? `+${day.points}` : ""}
                </span>
                <div className="flex min-h-0 w-full flex-1 items-end justify-center">
                  <div
                    aria-label={accessibleLabel}
                    className={`weekly-chart-bar ${day.solves > 0 && day.points === 0 ? "weekly-chart-bar-zero" : ""}`}
                    role="group"
                    style={{ height: day.points > 0 ? `${barHeight}%` : undefined }}
                    title={accessibleLabel}
                  >
                    {difficulties.map(({ value, segmentClass }) => {
                      const points = day.difficultyPoints[value];
                      if (points === 0 || day.points === 0) return null;
                      return (
                        <span
                          className={segmentClass}
                          key={value}
                          style={{ height: `${(points / day.points) * 100}%` }}
                        />
                      );
                    })}
                  </div>
                </div>
                <p className="mt-2 text-[0.62rem] font-extrabold uppercase tracking-wide text-slate-500 sm:text-xs">
                  {day.label}
                </p>
                <p className="mt-0.5 text-[0.58rem] tabular-nums text-slate-700 sm:text-[0.65rem]">
                  {day.solves} {day.solves === 1 ? "solve" : "solves"}
                </p>
              </div>
            );
          })}
        </div>

        <div className="mt-5 flex flex-col gap-3 border-t border-white/6 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-4">
            {difficulties.map(({ value, label, dotClass }) => (
              <span className="flex items-center gap-1.5 text-[0.68rem] font-bold text-slate-500" key={value}>
                <span className={`size-1.5 rounded-full ${dotClass}`} />
                {label} <strong className="tabular-nums text-slate-300">{difficultySolves[value]}</strong>
              </span>
            ))}
          </div>
          <p className="text-xs font-bold text-slate-500">
            Seven-day total <strong className="ml-1 text-sm font-black tabular-nums text-white">{totalPoints} pts</strong>
          </p>
        </div>
      </div>
    </section>
  );
}
