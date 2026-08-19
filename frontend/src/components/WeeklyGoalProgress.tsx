import { Target } from "lucide-react";

interface WeeklyGoalProgressProps {
  completed: number;
  goal: number;
  compact?: boolean;
}

export function WeeklyGoalProgress({
  completed,
  goal,
  compact = false,
}: WeeklyGoalProgressProps) {
  const safeGoal = Math.max(goal, 1);
  const percentage = Math.min((completed / safeGoal) * 100, 100);
  const achieved = completed >= goal;

  return (
    <div className={compact ? "" : "panel panel-accent p-5"}>
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <span className="icon-chip icon-chip-teal">
            <Target aria-hidden="true" size={17} />
          </span>
          <div>
            <p className="text-sm font-extrabold text-white">Weekly goal</p>
            <p className="mt-0.5 text-xs text-slate-500">Rolling seven days</p>
          </div>
        </div>
        <p className="text-right text-lg font-black tabular-nums text-white">
          {completed}
          <span className="text-sm text-slate-500">/{goal}</span>
        </p>
      </div>
      <div
        aria-label={`${Math.min(completed, goal)} of ${goal} weekly solves completed`}
        aria-valuemax={goal}
        aria-valuemin={0}
        aria-valuenow={Math.min(completed, goal)}
        className="mt-4 h-2 overflow-hidden rounded-full bg-slate-950/80"
        role="progressbar"
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-teal-600 to-teal-300 shadow-[0_0_16px_rgba(45,212,191,0.28)] transition-[width] duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="mt-2.5 text-xs text-slate-500">
        {achieved
          ? "Goal reached. Keep the momentum going."
          : `${goal - completed} more ${goal - completed === 1 ? "solve" : "solves"} to hit your goal.`}
      </p>
    </div>
  );
}
