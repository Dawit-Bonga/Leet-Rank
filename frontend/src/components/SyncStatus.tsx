import { CircleAlert, Clock3, RefreshCw, Wifi } from "lucide-react";

import { formatTimestamp } from "../lib/format";
import type { UserProfile } from "../types/api";

interface SyncStatusProps {
  profile: UserProfile;
  compact?: boolean;
}

export function SyncStatus({ profile, compact = false }: SyncStatusProps) {
  const config =
    profile.sync_status === "RUNNING"
      ? { Icon: RefreshCw, label: "Updating now", iconClass: "animate-spin" }
      : profile.sync_status === "FAILED"
        ? { Icon: CircleAlert, label: "Retry scheduled", iconClass: "" }
        : profile.last_successful_sync_at
          ? {
              Icon: Wifi,
              label: `Synced ${formatTimestamp(profile.last_successful_sync_at)}`,
              iconClass: "",
            }
          : { Icon: Clock3, label: "First sync pending", iconClass: "" };

  return (
    <div className={`sync-status ${compact ? "sync-status-compact" : ""}`}>
      <config.Icon aria-hidden="true" className={config.iconClass} size={14} strokeWidth={2.2} />
      <span>{config.label}</span>
    </div>
  );
}
