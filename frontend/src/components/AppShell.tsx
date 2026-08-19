import { Suspense, useEffect, useRef, useState } from "react";
import { ChevronDown, LayoutDashboard, LogOut, Settings, UserRound, UsersRound, type LucideIcon } from "lucide-react";
import { Link, NavLink, Outlet, useLocation } from "react-router";

import { useFriendsData } from "../context/FriendsDataContext";
import type { UserProfile } from "../types/api";
import { Brand } from "./Brand";
import { UserAvatar } from "./UserAvatar";

interface AppShellProps {
  profile: UserProfile;
  onSignOut: () => Promise<void>;
}

const navigation: Array<{
  to: string;
  label: string;
  icon: LucideIcon;
  end: boolean;
}> = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/friends", label: "Friends", icon: UsersRound, end: false },
  { to: "/profile", label: "Profile", icon: UserRound, end: false },
];

export function AppShell({ profile, onSignOut }: AppShellProps) {
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const { overview } = useFriendsData();
  const pendingRequests = overview?.incoming.length ?? 0;

  useEffect(() => {
    setAccountMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!accountMenuOpen) return;

    function handlePointerDown(event: MouseEvent) {
      if (!accountMenuRef.current?.contains(event.target as Node)) {
        setAccountMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setAccountMenuOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [accountMenuOpen]);

  return (
    <div className="app-background min-h-screen text-white">
      <header className="sticky top-0 z-30 border-b border-white/6 bg-[#030712]/86 px-5 py-3.5 backdrop-blur-xl sm:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6">
          <NavLink aria-label="LeetRank dashboard" className="rounded-xl focus:outline-none focus:ring-4 focus:ring-orange-400/15" to="/">
            <Brand compact />
          </NavLink>

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

          <div className="relative" ref={accountMenuRef}>
            <button
              aria-expanded={accountMenuOpen}
              aria-haspopup="menu"
              className={`group flex items-center gap-3 rounded-xl px-2 py-1.5 transition hover:bg-white/5 focus:outline-none focus:ring-4 focus:ring-white/5 ${accountMenuOpen ? "bg-white/5" : ""}`}
              type="button"
              onClick={() => setAccountMenuOpen((open) => !open)}
            >
              <div className="hidden text-right sm:block">
                <p className="text-sm font-semibold text-white group-hover:text-orange-300">
                  {profile.display_name}
                </p>
                <p className="text-xs text-slate-500">@{profile.username}</p>
              </div>
              <UserAvatar highlighted name={profile.display_name} size="sm" />
              <ChevronDown
                aria-hidden="true"
                className={`hidden text-slate-600 transition sm:block ${accountMenuOpen ? "rotate-180" : ""}`}
                size={15}
              />
            </button>

            {accountMenuOpen && (
              <div
                className="absolute right-0 top-[calc(100%+0.65rem)] z-40 w-56 overflow-hidden rounded-xl border border-white/10 bg-slate-900/98 p-1.5 shadow-2xl shadow-black/40 backdrop-blur-xl"
                role="menu"
              >
                <div className="border-b border-white/6 px-3 py-2.5 sm:hidden">
                  <p className="truncate text-sm font-bold text-white">{profile.display_name}</p>
                  <p className="truncate text-xs text-slate-500">@{profile.username}</p>
                </div>
                <Link className="account-menu-item" role="menuitem" to="/profile">
                  <UserRound aria-hidden="true" size={16} />
                  View profile
                </Link>
                <Link className="account-menu-item" role="menuitem" to="/settings">
                  <Settings aria-hidden="true" size={16} />
                  Settings
                </Link>
                <div className="my-1 border-t border-white/6" />
                <button
                  className="account-menu-item w-full text-red-300 hover:bg-red-400/8 hover:text-red-200"
                  role="menuitem"
                  type="button"
                  onClick={() => void onSignOut()}
                >
                  <LogOut aria-hidden="true" size={16} />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <Suspense
        fallback={
          <main className="page-container">
            <div className="h-9 w-48 animate-pulse rounded-lg bg-white/5" />
            <div className="mt-6 grid gap-5 lg:grid-cols-2">
              <div className="h-72 animate-pulse rounded-2xl bg-white/4" />
              <div className="h-72 animate-pulse rounded-2xl bg-white/4" />
            </div>
          </main>
        }
      >
        <Outlet />
      </Suspense>

      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 border-t border-white/8 bg-slate-950/95 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur md:hidden">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              className={({ isActive }) =>
                `mobile-nav-link ${isActive ? "mobile-nav-link-active" : ""}`
              }
              end={item.end}
              key={item.to}
              to={item.to}
            >
              <span className="relative">
                <Icon aria-hidden="true" size={19} strokeWidth={2.2} />
                {item.label === "Friends" && pendingRequests > 0 && (
                  <span className="absolute -right-3 -top-1 grid size-4 place-items-center rounded-full bg-orange-500 text-[0.6rem] font-black text-slate-950">
                    {pendingRequests}
                  </span>
                )}
              </span>
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}
