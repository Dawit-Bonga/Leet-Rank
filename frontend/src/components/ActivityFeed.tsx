import { Check, Code2, GitCommitHorizontal } from "lucide-react";

import { formatTimestamp, readableLabel } from "../lib/format";
import type { ActivityItem } from "../types/api";
import { EmptyState } from "./EmptyState";

interface ActivityFeedProps {
  items: ActivityItem[];
  limit?: number;
  emptyMessage?: string;
}

const difficultyStyles = {
  EASY: "difficulty-easy",
  MEDIUM: "difficulty-medium",
  HARD: "difficulty-hard",
};

export function ActivityFeed({
  items,
  limit = 6,
  emptyMessage = "No scored activity yet.",
}: ActivityFeedProps) {
  const visibleItems = items.slice(0, limit);
  if (visibleItems.length === 0) {
    return (
      <EmptyState
        compact
        description={emptyMessage}
        icon={Code2}
        title="No scored solves yet"
      />
    );
  }

  return (
    <div className="activity-feed">
      {visibleItems.map((item) => (
        <div className="activity-item" key={item.id}>
          <div className="activity-marker">
            {item.points > 0 ? (
              <Check aria-hidden="true" size={13} strokeWidth={3} />
            ) : (
              <Code2 aria-hidden="true" size={13} strokeWidth={2.4} />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 items-center gap-2">
              <p className="truncate text-sm font-bold text-slate-100">{item.problem.title}</p>
              <span className={`difficulty-badge ${difficultyStyles[item.problem.difficulty]}`}>
                {readableLabel(item.problem.difficulty)}
              </span>
              <span
                className="source-badge"
                title={item.provider === "github_neetcode" ? "GitHub / NeetCode" : "LeetCode"}
              >
                {item.provider === "github_neetcode" ? (
                  <GitCommitHorizontal aria-hidden="true" size={10} />
                ) : (
                  <Code2 aria-hidden="true" size={10} />
                )}
                {item.provider === "github_neetcode" ? "GitHub" : "LeetCode"}
              </span>
            </div>
            <p className="mt-1 text-[0.7rem] text-slate-500">
              {readableLabel(item.reason)} · {formatTimestamp(item.earned_at)}
            </p>
          </div>
          <p className={`shrink-0 text-sm font-black tabular-nums ${item.points > 0 ? "text-orange-300" : "text-slate-600"}`}>
            {item.points > 0 ? "+" : ""}{item.points}
          </p>
        </div>
      ))}
    </div>
  );
}
