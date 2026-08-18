import { useState, type FormEvent } from "react";
import { ArrowLeft, KeyRound, LockKeyhole } from "lucide-react";

import { supabase } from "../lib/supabase";
import { Brand } from "./Brand";

interface ResetPasswordFormProps {
  recoveryReady: boolean;
  recoveryError: string | null;
  onComplete: () => Promise<void>;
}

export function ResetPasswordForm({
  recoveryReady,
  recoveryError,
  onComplete,
}: ResetPasswordFormProps) {
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) {
      setError(updateError.message);
      setLoading(false);
      return;
    }

    try {
      await onComplete();
    } catch {
      setError("Your password was updated, but we could not return to sign in.");
      setLoading(false);
    }
  }

  return (
    <main className="app-background grid min-h-screen place-items-center px-5 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Brand />
        </div>
        <section className="panel panel-accent p-6 sm:p-8">
          {!recoveryReady ? (
            <div className="text-center">
              <span className="icon-chip mx-auto">
                <LockKeyhole aria-hidden="true" size={18} />
              </span>
              <h1 className="mt-5 text-2xl font-black tracking-tight text-white">
                Reset link unavailable
              </h1>
              <p className="mt-3 text-sm leading-6 text-slate-400">
                {recoveryError ??
                  "This password reset link is invalid or has expired. Request a new one from the sign-in page."}
              </p>
              <a className="secondary-button mt-6" href="/">
                <ArrowLeft aria-hidden="true" size={16} /> Return to sign in
              </a>
            </div>
          ) : (
            <>
              <span className="icon-chip icon-chip-orange">
                <KeyRound aria-hidden="true" size={18} />
              </span>
              <p className="eyebrow mt-5">Secure recovery</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight text-white">
                Choose a new password
              </h1>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                Enter your new password twice to finish recovering your account.
              </p>

              <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
                <label className="block">
                  <span className="field-label">New password</span>
                  <input
                    autoComplete="new-password"
                    className="field-input"
                    type="password"
                    minLength={6}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="At least 6 characters"
                    required
                  />
                </label>
                <label className="block">
                  <span className="field-label">Confirm new password</span>
                  <input
                    autoComplete="new-password"
                    className="field-input"
                    type="password"
                    minLength={6}
                    value={confirmation}
                    onChange={(event) => setConfirmation(event.target.value)}
                    placeholder="Enter it again"
                    required
                  />
                </label>

                {error && <div className="error-banner">{error}</div>}

                <button className="primary-button w-full" type="submit" disabled={loading}>
                  <KeyRound aria-hidden="true" size={16} />
                  {loading ? "Updating password…" : "Update password"}
                </button>
              </form>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
