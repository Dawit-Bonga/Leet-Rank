import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, KeyRound } from "lucide-react";
import { Link, useNavigate } from "react-router";

import { supabase } from "../lib/supabase";
import { Brand } from "./Brand";

type AuthMode = "login" | "signup" | "forgot";

interface AuthFormProps {
  initialMode?: Exclude<AuthMode, "forgot">;
  initialNotice?: string | null;
  returnTo?: string | null;
}

export function AuthForm({
  initialMode = "login",
  initialNotice = null,
  returnTo = null,
}: AuthFormProps) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(initialNotice);

  useEffect(() => {
    if (initialNotice) setNotice(initialNotice);
  }, [initialNotice]);

  useEffect(() => {
    setMode(initialMode);
    setError(null);
  }, [initialMode]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setNotice(null);

    if (mode === "forgot") {
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password${
          returnTo ? `?next=${encodeURIComponent(returnTo)}` : ""
        }`,
      });
      if (resetError) {
        setError(resetError.message);
      } else {
        setNotice(
          "If an account exists for that email, a password reset link is on its way.",
        );
      }
    } else if (mode === "login") {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (signInError) {
        setError(signInError.message);
      }
    } else {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}${returnTo ?? "/"}`,
        },
      });
      if (signUpError) {
        setError(signUpError.message);
      } else if (!data.session) {
        setNotice("Check your email to confirm your account, then come back to sign in.");
      }
    }
    setLoading(false);
  }

  function changeMode(nextMode: AuthMode) {
    if (nextMode !== "forgot") {
      navigate(nextMode === "login" ? "/sign-in" : "/sign-up");
    }
    setMode(nextMode);
    setError(null);
    setNotice(null);
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden border-r border-white/5 bg-slate-950 p-12 lg:flex lg:flex-col lg:justify-between">
        <div className="absolute inset-0 auth-grid opacity-40" />
        <div className="absolute -left-32 top-1/3 size-96 rounded-full bg-orange-500/10 blur-3xl" />
        <Link className="relative z-10 w-fit rounded-xl focus:outline-none focus:ring-4 focus:ring-orange-400/20" to="/">
          <Brand />
        </Link>
        <div className="relative z-10 max-w-xl pb-16">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-orange-400/20 bg-orange-400/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-orange-300">
            Friendly accountability
          </div>
          <h1 className="text-5xl font-black leading-[1.06] tracking-tight text-white xl:text-6xl">
            Your practice deserves a little competition.
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-400">
            Turn accepted LeetCode solves into points, compare progress with friends, and
            make consistency visible.
          </p>
        </div>
        <p className="relative z-10 text-sm text-slate-600">Built for progress, not prestige.</p>
      </section>

      <section className="flex min-h-screen items-center justify-center bg-slate-900/78 px-5 py-12 sm:px-10">
        <div className="w-full max-w-md">
          <div className="mb-10 lg:hidden">
            <Link className="inline-block rounded-xl focus:outline-none focus:ring-4 focus:ring-orange-400/20" to="/">
              <Brand />
            </Link>
          </div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-orange-400">
            {mode === "login"
              ? "Welcome back"
              : mode === "signup"
                ? "Start your run"
                : "Account recovery"}
          </p>
          <h2 className="mt-3 text-4xl font-black tracking-tight text-white">
            {mode === "login"
              ? "Sign in to LeetRank"
              : mode === "signup"
                ? "Create your account"
                : "Reset your password"}
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            {mode === "login"
              ? "See where you stand and keep your momentum going."
              : mode === "signup"
                ? "You’ll connect your LeetCode profile in the next step."
                : "Enter your email and we’ll send you a secure recovery link."}
          </p>

          <form className="mt-9 space-y-5" onSubmit={handleSubmit}>
            <label className="block">
              <span className="field-label">Email address</span>
              <input
                className="field-input"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>
            {mode !== "forgot" && (
              <label className="block">
                <span className="field-label">Password</span>
                <input
                  className="field-input"
                  type="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  minLength={6}
                  placeholder="At least 6 characters"
                  required
                />
                {mode === "login" && (
                  <button
                    className="mt-2 block text-xs font-bold text-orange-400 transition hover:text-orange-300"
                    type="button"
                    onClick={() => changeMode("forgot")}
                  >
                    Forgot password?
                  </button>
                )}
              </label>
            )}

            {error && <div className="error-banner">{error}</div>}
            {notice && <div className="success-banner">{notice}</div>}

            <button className="primary-button w-full" type="submit" disabled={loading}>
              {loading ? (
                "Please wait…"
              ) : mode === "login" ? (
                "Sign in"
              ) : mode === "signup" ? (
                "Create account"
              ) : (
                <>
                  <KeyRound aria-hidden="true" size={16} /> Send reset link
                </>
              )}
            </button>
          </form>

          {mode === "forgot" ? (
            <button
              className="mx-auto mt-7 flex items-center gap-2 text-sm font-bold text-slate-400 transition hover:text-white"
              type="button"
              onClick={() => changeMode("login")}
            >
              <ArrowLeft aria-hidden="true" size={15} /> Back to sign in
            </button>
          ) : (
            <p className="mt-7 text-center text-sm text-slate-400">
              {mode === "login" ? "New to LeetRank?" : "Already have an account?"}{" "}
              <button
                className="font-semibold text-orange-400 transition hover:text-orange-300"
                type="button"
                onClick={() => changeMode(mode === "login" ? "signup" : "login")}
              >
                {mode === "login" ? "Create an account" : "Sign in"}
              </button>
            </p>
          )}
          <Link
            className="mx-auto mt-5 flex w-fit items-center gap-2 text-xs font-bold text-slate-600 transition hover:text-slate-300"
            to="/"
          >
            <ArrowLeft aria-hidden="true" size={13} /> Back to LeetRank
          </Link>
        </div>
      </section>
    </main>
  );
}
