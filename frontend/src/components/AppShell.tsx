import { NavLink, Outlet } from "react-router";

import type { UserProfile } from "../types/api";
import { initials } from "../lib/format";
import { Brand } from "./Brand";

interface AppShellProps {
  profile: UserProfile;
  pendingRequests: number;
  onSignOut: () => Promise<void>;
}

const navigation = [
  { to: "/", label: "Dashboard", icon: "▥", end: true },
  { to: "/friends", label: "Friends", icon: "◎", end: false },
  { to: "/profile", label: "Profile", icon: "◉", end: false },
];

export function AppShell({ profile, pendingRequests, onSignOut }: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="sticky top-0 z-30 border-b border-white/6 bg-slate-950/90 px-5 py-4 backdrop-blur sm:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6">
          <Brand compact />

          <nav className="hidden items-center gap-1 rounded-xl bg-white/3 p-1 md:flex">
            {navigation.slice(0, 2).map((item) => (
              <NavLink
                className={({ isActive }) =>
                  `desktop-nav-link ${isActive ? "desktop-nav-link-active" : ""}`
                }
                end={item.end}
                key={item.to}
                to={item.to}
              >
                {item.label}
                {item.label === "Friends" && pendingRequests > 0 && (
                  <span className="notification-badge">{pendingRequests}</span>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <NavLink
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-2 py-1.5 transition hover:bg-white/5 ${isActive ? "bg-white/5" : ""}`
              }
              to="/profile"
            >
              <div className="hidden text-right sm:block">
                <p className="text-sm font-semibold text-white group-hover:text-orange-300">
                  {profile.display_name}
                </p>
                <p className="text-xs text-slate-500">@{profile.username}</p>
              </div>
              <div className="grid size-10 place-items-center rounded-full border border-orange-400/20 bg-orange-400/10 text-sm font-bold text-orange-300">
                {initials(profile.display_name)}
              </div>
            </NavLink>
            <button
              className="hidden text-button sm:block"
              type="button"
              onClick={() => void onSignOut()}
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <Outlet />

      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 border-t border-white/8 bg-slate-950/95 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur md:hidden">
        {navigation.map((item) => (
          <NavLink
            className={({ isActive }) =>
              `mobile-nav-link ${isActive ? "mobile-nav-link-active" : ""}`
            }
            end={item.end}
            key={item.to}
            to={item.to}
          >
            <span className="relative text-lg">
              {item.icon}
              {item.label === "Friends" && pendingRequests > 0 && (
                <span className="absolute -right-3 -top-1 grid size-4 place-items-center rounded-full bg-orange-500 text-[0.6rem] font-black text-slate-950">
                  {pendingRequests}
                </span>
              )}
            </span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
