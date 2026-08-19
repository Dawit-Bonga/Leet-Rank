import { lazy, useCallback, useEffect, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { Navigate, Route, Routes } from "react-router";

import { AppShell } from "./components/AppShell";
import { AuthForm } from "./components/AuthForm";
import { Brand } from "./components/Brand";
import { LeaderboardDashboard } from "./components/LeaderboardDashboard";
import { OnboardingForm } from "./components/OnboardingForm";
import { ResetPasswordForm } from "./components/ResetPasswordForm";
import { FriendsDataProvider } from "./context/FriendsDataContext";
import { ApiError, getCurrentUser, warmBackend } from "./lib/api";
import { supabase } from "./lib/supabase";
import type { CurrentUser } from "./types/api";

const FriendsPage = lazy(() =>
  import("./components/FriendsPage").then((module) => ({ default: module.FriendsPage })),
);
const FriendProfilePage = lazy(() =>
  import("./components/FriendProfilePage").then((module) => ({
    default: module.FriendProfilePage,
  })),
);
const ProfilePage = lazy(() =>
  import("./components/ProfilePage").then((module) => ({ default: module.ProfilePage })),
);
const SettingsPage = lazy(() =>
  import("./components/SettingsPage").then((module) => ({ default: module.SettingsPage })),
);

function FullPageLoading({ backendStarting = false }: { backendStarting?: boolean }) {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 px-5">
      <div className="text-center">
        <div className="mx-auto mb-5 size-10 animate-spin rounded-full border-2 border-slate-700 border-t-orange-400" />
        <Brand />
        <p className="mt-4 text-sm text-slate-500">
          {backendStarting ? "Starting LeetRank…" : "Loading your account…"}
        </p>
        {backendStarting && (
          <p className="mt-2 text-xs text-slate-600">
            The server is waking up. This can take up to a minute.
          </p>
        )}
      </div>
    </main>
  );
}

export default function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [account, setAccount] = useState<CurrentUser | null>(null);
  const [accountLoading, setAccountLoading] = useState(false);
  const [accountSlow, setAccountSlow] = useState(false);
  const [accountError, setAccountError] = useState<string | null>(null);
  const accountLoadSequence = useRef(0);
  const [passwordRecoveryActive, setPasswordRecoveryActive] = useState(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1));
    return hash.get("type") === "recovery";
  });
  const [authNotice, setAuthNotice] = useState<string | null>(null);
  const passwordRecoveryPath = window.location.pathname === "/reset-password";
  const recoveryParameters = new URLSearchParams(window.location.hash.slice(1));
  const recoveryError =
    recoveryParameters.get("error_description")?.replaceAll("+", " ") ?? null;

  useEffect(() => {
    void warmBackend();
  }, []);

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (event === "PASSWORD_RECOVERY") setPasswordRecoveryActive(true);
      setSession(nextSession);
      if (!nextSession) {
        setAccount(null);
        setAccountError(null);
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  const loadAccount = useCallback(async () => {
    if (!session) return;
    const requestId = ++accountLoadSequence.current;
    setAccountLoading(true);
    setAccountSlow(false);
    setAccountError(null);
    const slowTimer = window.setTimeout(() => {
      if (accountLoadSequence.current === requestId) setAccountSlow(true);
    }, 2_000);
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
      window.clearTimeout(slowTimer);
      if (accountLoadSequence.current === requestId) {
        setAccountLoading(false);
        setAccountSlow(false);
      }
    }
  }, [session]);

  useEffect(() => {
    if (session && !passwordRecoveryPath) void loadAccount();
  }, [session, loadAccount, passwordRecoveryPath]);

  async function signOut() {
    await supabase.auth.signOut();
  }

  async function finishPasswordRecovery() {
    setAuthNotice("Password updated. Sign in with your new password.");
    const { error } = await supabase.auth.signOut({ scope: "local" });
    if (error) {
      setAuthNotice(null);
      throw error;
    }
    window.history.replaceState({}, "", "/");
    setPasswordRecoveryActive(false);
  }

  if (session === undefined) {
    return <FullPageLoading />;
  }
  if (passwordRecoveryPath) {
    return (
      <ResetPasswordForm
        recoveryReady={Boolean(session && passwordRecoveryActive && !recoveryError)}
        recoveryError={recoveryError}
        onComplete={finishPasswordRecovery}
      />
    );
  }
  if (session && accountLoading && !account) {
    return <FullPageLoading backendStarting={accountSlow} />;
  }
  if (!session) {
    return <AuthForm initialNotice={authNotice} />;
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
    <FriendsDataProvider accessToken={session.access_token}>
      <Routes>
        <Route element={<AppShell onSignOut={signOut} profile={account.profile} />}>
          <Route
            index
            element={
              <LeaderboardDashboard
                accessToken={session.access_token}
                profile={account.profile}
              />
            }
          />
          <Route
            path="friends"
            element={<FriendsPage accessToken={session.access_token} />}
          />
          <Route
            path="friends/:friendId"
            element={<FriendProfilePage accessToken={session.access_token} />}
          />
          <Route
            path="profile"
            element={
              <ProfilePage
                accessToken={session.access_token}
                profile={account.profile}
              />
            }
          />
          <Route
            path="settings"
            element={
              <SettingsPage
                accessToken={session.access_token}
                profile={account.profile}
                onSaved={loadAccount}
              />
            }
          />
        </Route>
        <Route path="*" element={<Navigate replace to="/" />} />
      </Routes>
    </FriendsDataProvider>
  );
}
