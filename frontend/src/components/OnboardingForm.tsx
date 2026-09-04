import { useState, type FormEvent } from "react";

import { ApiError, completeOnboarding } from "../lib/api";
import type {
  LeetCodeExperience,
  OnboardingPayload,
  PrimaryGoal,
} from "../types/api";
import { Brand } from "./Brand";

interface OnboardingFormProps {
  accessToken: string;
  email: string | null;
  onComplete: () => Promise<void>;
  onSignOut: () => Promise<void>;
}

const goalOptions: Array<{ value: PrimaryGoal; label: string; description: string }> = [
  { value: "CONSISTENCY", label: "Build consistency", description: "Make practice a habit" },
  { value: "ACCOUNTABILITY", label: "Stay accountable", description: "Show up with friends" },
  { value: "COMPETITION", label: "Compete", description: "Turn progress into a game" },
  {
    value: "INTERVIEW_PREP",
    label: "Prepare for interviews",
    description: "Stay focused on the goal",
  },
  { value: "LEARNING", label: "Keep learning", description: "Grow problem-solving skills" },
];

const experienceOptions: Array<{ value: LeetCodeExperience; label: string }> = [
  { value: "BEGINNER", label: "Beginner" },
  { value: "INTERMEDIATE", label: "Intermediate" },
  { value: "ADVANCED", label: "Advanced" },
];

export function OnboardingForm({
  accessToken,
  email,
  onComplete,
  onSignOut,
}: OnboardingFormProps) {
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [leetcodeUsername, setLeetcodeUsername] = useState("");
  const [primaryGoal, setPrimaryGoal] = useState<PrimaryGoal>("CONSISTENCY");
  const [experience, setExperience] = useState<LeetCodeExperience>("INTERMEDIATE");
  const [weeklyGoal, setWeeklyGoal] = useState(5);
  const [connectNeetcode, setConnectNeetcode] = useState(false);
  const [neetcodeRepoOwner, setNeetcodeRepoOwner] = useState("");
  const [neetcodeRepoName, setNeetcodeRepoName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const payload: OnboardingPayload = {
      username,
      display_name: displayName,
      leetcode_username: leetcodeUsername,
      primary_goal: primaryGoal,
      leetcode_experience: experience,
      weekly_problem_goal: weeklyGoal,
      ...(connectNeetcode
        ? {
            neetcode_repo_owner: neetcodeRepoOwner.trim(),
            neetcode_repo_name: neetcodeRepoName.trim(),
          }
        : {}),
    };
    try {
      await completeOnboarding(accessToken, payload);
      await onComplete();
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Could not complete onboarding. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-background min-h-screen px-5 py-8 sm:px-8">
      <div className="mx-auto max-w-4xl">
        <header className="flex items-center justify-between">
          <Brand compact />
          <button className="text-button" type="button" onClick={() => void onSignOut()}>
            Sign out
          </button>
        </header>

        <section className="panel mt-12 rounded-3xl p-6 sm:p-10">
          <div className="max-w-2xl">
            <p className="eyebrow">One last step</p>
            <h1 className="mt-3 text-4xl font-black tracking-tight text-white">
              Make LeetClimb yours.
            </h1>
            <p className="mt-3 leading-7 text-slate-400">
              Connect your LeetCode profile and tell us what you’re working toward. Scoring
              starts only after this step is complete.
            </p>
            {email && <p className="mt-3 text-sm text-slate-500">Signed in as {email}</p>}
          </div>

          <form className="mt-10 space-y-9" onSubmit={handleSubmit}>
            <div className="grid gap-5 sm:grid-cols-2">
              <label>
                <span className="field-label">Display name</span>
                <input
                  className="field-input"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Dawit"
                  maxLength={100}
                  required
                />
              </label>
              <label>
                <span className="field-label">LeetClimb username</span>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">@</span>
                  <input
                    className="field-input field-input-leading"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    placeholder="dawit"
                    minLength={3}
                    maxLength={30}
                    pattern="[A-Za-z0-9][A-Za-z0-9_]*"
                    required
                  />
                </div>
              </label>
              <label className="sm:col-span-2">
                <span className="field-label">LeetCode username</span>
                <input
                  className="field-input"
                  value={leetcodeUsername}
                  onChange={(event) => setLeetcodeUsername(event.target.value)}
                  placeholder="Your exact LeetCode username"
                  maxLength={64}
                  required
                />
                <span className="mt-2 block text-xs text-slate-500">
                  We’ll verify that this public profile exists before scoring begins.
                </span>
              </label>
            </div>

            <fieldset>
              <legend className="field-label">Why are you joining?</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {goalOptions.map((option) => (
                  <label
                    className={`choice-card ${primaryGoal === option.value ? "choice-card-active" : ""}`}
                    key={option.value}
                  >
                    <input
                      className="sr-only"
                      type="radio"
                      name="primary-goal"
                      value={option.value}
                      checked={primaryGoal === option.value}
                      onChange={() => setPrimaryGoal(option.value)}
                    />
                    <span className="font-semibold text-white">{option.label}</span>
                    <span className="mt-1 block text-xs text-slate-500">{option.description}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="grid gap-8 sm:grid-cols-2">
              <fieldset>
                <legend className="field-label">LeetCode experience</legend>
                <div className="flex rounded-xl border border-white/8 bg-slate-950/50 p-1">
                  {experienceOptions.map((option) => (
                    <label className="flex-1" key={option.value}>
                      <input
                        className="peer sr-only"
                        type="radio"
                        name="experience"
                        checked={experience === option.value}
                        onChange={() => setExperience(option.value)}
                      />
                      <span className="block cursor-pointer rounded-lg px-2 py-2.5 text-center text-xs font-semibold text-slate-500 transition peer-checked:bg-slate-800 peer-checked:text-white">
                        {option.label}
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>

              <label>
                <span className="field-label">Weekly problem goal</span>
                <input
                  className="field-input"
                  type="number"
                  min={1}
                  max={100}
                  value={weeklyGoal}
                  onChange={(event) => setWeeklyGoal(Number(event.target.value))}
                  required
                />
              </label>
            </div>

            <fieldset>
              <legend className="field-label">Optional NeetCode integration</legend>
              <label
                className={`choice-card block ${connectNeetcode ? "choice-card-active" : ""}`}
              >
                <span className="flex items-start gap-3">
                  <input
                    className="mt-1 h-4 w-4 accent-orange-500"
                    type="checkbox"
                    checked={connectNeetcode}
                    onChange={(event) => setConnectNeetcode(event.target.checked)}
                  />
                  <span>
                    <span className="block font-semibold text-white">
                      Connect NeetCode GitHub Sync
                    </span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500">
                      Count accepted NeetCode submissions saved to your GitHub repository.
                      LeetCode synchronization always stays enabled.
                    </span>
                  </span>
                </span>
              </label>

              {connectNeetcode && (
                <div className="mt-4 grid gap-5 sm:grid-cols-2">
                  <label>
                    <span className="field-label">GitHub owner</span>
                    <input
                      className="field-input"
                      value={neetcodeRepoOwner}
                      onChange={(event) => setNeetcodeRepoOwner(event.target.value)}
                      placeholder="github-username"
                      maxLength={100}
                      required
                    />
                  </label>
                  <label>
                    <span className="field-label">GitHub repository</span>
                    <input
                      className="field-input"
                      value={neetcodeRepoName}
                      onChange={(event) => setNeetcodeRepoName(event.target.value)}
                      placeholder="neetcode-submissions"
                      maxLength={100}
                      required
                    />
                  </label>
                  <p className="text-xs leading-5 text-slate-500 sm:col-span-2">
                    This is optional. You can connect or change the repository later in
                    Settings. Scoring only includes submissions made after setup is complete.
                  </p>
                </div>
              )}
            </fieldset>

            {error && <div className="error-banner">{error}</div>}

            <div className="flex justify-end">
              <button className="primary-button w-full sm:w-auto" type="submit" disabled={loading}>
                {loading ? "Connecting LeetCode…" : "Complete setup"}
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
