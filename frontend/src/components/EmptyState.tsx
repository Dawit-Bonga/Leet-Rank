import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  compact?: boolean;
}

export function EmptyState({ icon: Icon, title, description, compact = false }: EmptyStateProps) {
  return (
    <div className={`empty-state ${compact ? "empty-state-compact" : ""}`}>
      <span className="empty-state-icon">
        <Icon aria-hidden="true" size={compact ? 15 : 18} />
      </span>
      <div className={compact ? "text-left" : "text-center"}>
        <p className="text-xs font-extrabold text-slate-300">{title}</p>
        {description && <p className="mt-0.5 text-xs leading-5 text-slate-600">{description}</p>}
      </div>
    </div>
  );
}
