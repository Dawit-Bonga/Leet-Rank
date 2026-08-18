import { useCallback, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { Navigate, Route, Routes } from "react-router";

import { AppShell } from "./components/AppShell";
import { AuthForm } from "./components/AuthForm";
import { Brand } from "./components/Brand";
import { FriendsPage } from "./components/FriendsPage";
import { LeaderboardDashboard } from "./components/LeaderboardDashboard";
import { OnboardingForm } from "./components/OnboardingForm";
import { ProfilePage } from "./components/ProfilePage";
import { ApiError, getCurrentUser, getFriendRequests } from "./lib/api";
import { supabase } from "./lib/supabase";
import type { CurrentUser } from "./types/api";

function FullPageLoading() {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 px-5">
      <div className="text-center">
        <div className="mx-auto mb-5 size-10 animate-spin rounded-full border-2 border-slate-700 border-t-orange-400" />
        <Brand />
        <p className="mt-4 text-sm text-slate-500">Loading your account…</p>
      </div>
    </main>
  );
}

export default function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [account, setAccount] = useState<CurrentUser | null>(null);
  const [accountLoading, setAccountLoading] = useState(false);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [pendingRequests, setPendingRequests] = useState(0);

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      if (!nextSession) {
        setAccount(null);
        setAccountError(null);
        setPendingRequests(0);
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  const loadAccount = useCallback(async () => {
    if (!session) return;
    setAccountLoading(true);
    setAccountError(null);
    try {
      setAccount(await getCurrentUser(session.access_token));
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 401) {
        await supabase.auth.signOut();
      } else {
        setAccountError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Could not load your LeetRank account.",
        );
      }
    } finally {
      setAccountLoading(false);
    }
  }, [session]);

  useEffect(() => {
    if (session) void loadAccount();
  }, [session, loadAccount]);

  useEffect(() => {
    if (!session || !account?.onboarding_completed) return;
    let active = true;
    void getFriendRequests(session.access_token)
      .then((requests) => {
        if (active) setPendingRequests(requests.incoming.length);
      })
      .catch(() => {
        // The Friends page surfaces request errors; the shell badge is best-effort.
      });
    return () => {
      active = false;
    };
  }, [account?.onboarding_completed, session]);

  async function signOut() {
    await supabase.auth.signOut();
  }

  if (session === undefined || (session && accountLoading && !account)) {
    return <FullPageLoading />;
  }
  if (!session) {
    return <AuthForm />;
  }
  if (accountError && !account) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-950 px-5">
        <div className="w-full max-w-md rounded-2xl border border-red-400/15 bg-slate-900 p-7 text-center">
          <p className="text-lg font-bold text-white">We couldn’t load your account.</p>
          <p className="mt-2 text-sm text-slate-400">{accountError}</p>
          <div className="mt-6 flex justify-center gap-3">
            <button className="secondary-button" onClick={() => void loadAccount()}>
              Try again
            </button>
            <button className="text-button" onClick={() => void signOut()}>
              Sign out
            </button>
          </div>
        </div>
      </main>
    );
  }
  if (!account) {
    return <FullPageLoading />;
  }
  if (!account.onboarding_completed || !account.profile) {
    return (
      <OnboardingForm
        accessToken={session.access_token}
        email={account.email}
        onComplete={loadAccount}
        onSignOut={signOut}
      />
    );
  }
  return (
    <Routes>
      <Route
        element={
          <AppShell
            profile={account.profile}
            pendingRequests={pendingRequests}
            onSignOut={signOut}
          />
        }
      >
        <Route
          index
          element={
            <LeaderboardDashboard accessToken={session.access_token} profile={account.profile} />
          }
        />
        <Route
          path="friends"
          element={
            <FriendsPage
              accessToken={session.access_token}
              onPendingCountChange={setPendingRequests}
            />
          }
        />
        <Route
          path="profile"
          element={
            <ProfilePage
              accessToken={session.access_token}
              profile={account.profile}
              onSignOut={signOut}
            />
          }
        />
      </Route>
      <Route path="*" element={<Navigate replace to="/" />} />
    </Routes>
  );
}
