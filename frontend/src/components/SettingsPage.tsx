import { useEffect, useState, type FormEvent } from "react";
import {
  Check,
  Code2,
  LockKeyhole,
  Save,
  Settings2,
  Target,
  UserRound,
} from "lucide-react";
import { Link } from "react-router";

import { ApiError, updateSettings } from "../lib/api";
import type {
  LeetCodeExperience,
  PrimaryGoal,
  UserProfile,
  UserSettingsPayload,
} from "../types/api";

interface SettingsPageProps {
  accessToken: string;
  profile: UserProfile;
  onSaved: () => Promise<void>;
}

const goalOptions: Array<{ value: PrimaryGoal; label: string }> = [
  { value: "CONSISTENCY", label: "Build consistency" },
  { value: "ACCOUNTABILITY", label: "Stay accountable" },
  { value: "COMPETITION", label: "Compete" },
  { value: "INTERVIEW_PREP", label: "Interview preparation" },
  { value: "LEARNING", label: "Keep learning" },
];

const experienceOptions: Array<{ value: LeetCodeExperience; label: string }> = [
  { value: "BEGINNER", label: "Beginner" },
  { value: "INTERMEDIATE", label: "Intermediate" },
  { value: "ADVANCED", label: "Advanced" },
];

export function SettingsPage({ accessToken, profile, onSaved }: SettingsPageProps) {
  const [displayName, setDisplayName] = useState(profile.display_name);
  const [primaryGoal, setPrimaryGoal] = useState<PrimaryGoal>(profile.primary_goal);
  const [experience, setExperience] = useState<LeetCodeExperience>(
    profile.leetcode_experience,
  );
  const [weeklyGoal, setWeeklyGoal] = useState(profile.weekly_problem_goal);
  const [neetcodeRepoOwner, setNeetcodeRepoOwner] = useState(
    profile.neetcode_repo_owner ?? "",
  );
  const [neetcodeRepoName, setNeetcodeRepoName] = useState(
    profile.neetcode_repo_name ?? "",
  );
  const [acceptedOnlyConfirmed, setAcceptedOnlyConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setDisplayName(profile.display_name);
    setPrimaryGoal(profile.primary_goal);
    setExperience(profile.leetcode_experience);
    setWeeklyGoal(profile.weekly_problem_goal);
    setNeetcodeRepoOwner(profile.neetcode_repo_owner ?? "");
    setNeetcodeRepoName(profile.neetcode_repo_name ?? "");
    setAcceptedOnlyConfirmed(false);
  }, [profile]);

  const unchanged =
    displayName.trim() === profile.display_name &&
    primaryGoal === profile.primary_goal &&
    experience === profile.leetcode_experience &&
    weeklyGoal === profile.weekly_problem_goal &&
    neetcodeRepoOwner.trim() === (profile.neetcode_repo_owner ?? "") &&
    neetcodeRepoName.trim() === (profile.neetcode_repo_name ?? "");
  const repositoryChanged =
    neetcodeRepoOwner.trim() !== (profile.neetcode_repo_owner ?? "") ||
    neetcodeRepoName.trim() !== (profile.neetcode_repo_name ?? "");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if ((neetcodeRepoOwner.trim() && !neetcodeRepoName.trim()) || (!neetcodeRepoOwner.trim() && neetcodeRepoName.trim())) {
      setError("GitHub owner and repository are required for NeetCode sync.");
      return;
    }
    if (repositoryChanged && neetcodeRepoOwner.trim() && !acceptedOnlyConfirmed) {
      setError("Confirm that NeetCode GitHub Sync is configured for accepted submissions only.");
      return;
    }
    const payload: UserSettingsPayload = {
      display_name: displayName,
      primary_goal: primaryGoal,
      leetcode_experience: experience,
      weekly_problem_goal: weeklyGoal,
      neetcode_repo_owner: neetcodeRepoOwner.trim() || null,
      neetcode_repo_name: neetcodeRepoName.trim() || null,
      neetcode_accepted_only_confirmed:
        repositoryChanged && Boolean(neetcodeRepoOwner.trim())
          ? acceptedOnlyConfirmed
          : undefined,
    };
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await updateSettings(accessToken, payload);
      await onSaved();
      setSaved(true);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Could not save your settings.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="page-container">
      <section>
        <p className="eyebrow">Your account</p>
        <h1 className="page-title mt-2">Settings</h1>
        <p className="page-description">
          Update how LeetClimb personalizes your goals and displays your profile.
        </p>
      </section>

      <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <form className="panel" onSubmit={handleSubmit}>
          <div className="panel-header">
            <div className="flex items-center gap-3">
              <span className="icon-chip icon-chip-orange">
                <Settings2 aria-hidden="true" size={18} />
              </span>
              <div>
                <h2 className="section-heading">Profile preferences</h2>
                <p className="section-kicker">These changes appear across LeetClimb</p>
              </div>
            </div>
          </div>

          <div className="space-y-7 p-5 sm:p-6">
            <label>
              <span className="field-label">Display name</span>
              <div className="relative">
                <UserRound
                  aria-hidden="true"
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600"
                  size={16}
                />
                <input
                  className="field-input field-input-leading"
                  value={displayName}
                  onChange={(event) => {
                    setDisplayName(event.target.value);
                    setSaved(false);
                  }}
                  maxLength={100}
                  required
                />
              </div>
            </label>

            <fieldset>
              <legend className="field-label">Primary goal</legend>
              <div className="grid gap-2.5 sm:grid-cols-2">
                {goalOptions.map((option) => (
                  <label
                    className={`choice-card p-3.5 ${primaryGoal === option.value ? "choice-card-active" : ""}`}
                    key={option.value}
                  >
                    <input
                      className="sr-only"
                      type="radio"
                      name="primary-goal"
                      checked={primaryGoal === option.value}
                      onChange={() => {
                        setPrimaryGoal(option.value);
                        setSaved(false);
                      }}
                    />
                    <span className="text-sm font-bold text-white">{option.label}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="grid gap-6 sm:grid-cols-2">
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
                        onChange={() => {
                          setExperience(option.value);
                          setSaved(false);
                        }}
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
                <div className="relative">
                  <Target
                    aria-hidden="true"
                    className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600"
                    size={16}
                  />
                  <input
                    className="field-input field-input-leading"
                    type="number"
                    min={1}
                    max={100}
                    value={weeklyGoal}
                    onChange={(event) => {
                      setWeeklyGoal(Number(event.target.value));
                      setSaved(false);
                    }}
                    required
                  />
                </div>
              </label>
            </div>

            <fieldset>
              <legend className="field-label">Optional NeetCode integration</legend>
              <p className="mt-1 text-xs text-slate-500">
                LeetCode sync always stays enabled. Add a NeetCode GitHub repo to ingest
                accepted-only auto-commit submissions too.
              </p>
              <div className="mt-3 grid gap-6 sm:grid-cols-2">
                <label>
                  <span className="field-label">GitHub owner</span>
                  <div className="relative">
                    <Code2
                      aria-hidden="true"
                      className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600"
                      size={16}
                    />
                    <input
                      className="field-input field-input-leading"
                      value={neetcodeRepoOwner}
                      onChange={(event) => {
                        setNeetcodeRepoOwner(event.target.value);
                        setSaved(false);
                      }}
                      placeholder="github-username"
                      maxLength={100}
                    />
                  </div>
                </label>
                <label>
                  <span className="field-label">GitHub repository</span>
                  <div className="relative">
                    <Code2
                      aria-hidden="true"
                      className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600"
                      size={16}
                    />
                    <input
                      className="field-input field-input-leading"
                      value={neetcodeRepoName}
                      onChange={(event) => {
                        setNeetcodeRepoName(event.target.value);
                        setSaved(false);
                      }}
                      placeholder="neetcode-submissions"
                      maxLength={100}
                    />
                  </div>
                </label>
              </div>
              {repositoryChanged && neetcodeRepoOwner.trim() && neetcodeRepoName.trim() && (
                <label className="choice-card mt-4 flex items-start gap-3">
                  <input
                    className="mt-1 h-4 w-4 accent-orange-500"
                    type="checkbox"
                    checked={acceptedOnlyConfirmed}
                    onChange={(event) => {
                      setAcceptedOnlyConfirmed(event.target.checked);
                      setSaved(false);
                    }}
                    required
                  />
                  <span>
                    <span className="block text-sm font-semibold text-white">
                      My NeetCode GitHub Sync status filter is set to Accepted only.
                    </span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500">
                      Verify this under NeetCode Profile → GitHub before connecting the
                      repository so failed attempts cannot earn points.
                    </span>
                  </span>
                </label>
              )}
            </fieldset>

            {error && <div className="error-banner">{error}</div>}
            {saved && (
              <div className="success-banner flex items-center gap-2">
                <Check aria-hidden="true" size={16} />
                Settings saved.
              </div>
            )}
          </div>

          <div className="flex items-center justify-between gap-4 border-t border-white/6 px-5 py-4 sm:px-6">
            <Link className="text-button" to="/profile">
              Cancel
            </Link>
            <button
              className="primary-button py-3"
              type="submit"
              disabled={saving || unchanged}
            >
              <Save aria-hidden="true" size={16} />
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>

        <aside className="panel p-5">
          <div className="flex items-center gap-3">
            <span className="icon-chip">
              <LockKeyhole aria-hidden="true" size={17} />
            </span>
            <div>
              <h2 className="text-sm font-extrabold text-white">Connected identity</h2>
              <p className="mt-0.5 text-xs text-slate-500">Protected in this version</p>
            </div>
          </div>
          <dl className="mt-5 space-y-4">
            <div>
              <dt className="text-[0.65rem] font-extrabold uppercase tracking-wider text-slate-600">
                LeetClimb username
              </dt>
              <dd className="mt-1 text-sm font-bold text-slate-200">@{profile.username}</dd>
            </div>
            <div>
              <dt className="text-[0.65rem] font-extrabold uppercase tracking-wider text-slate-600">
                LeetCode account
              </dt>
              <dd className="mt-1 flex items-center gap-2 text-sm font-bold text-slate-200">
                <Code2 aria-hidden="true" size={14} />@{profile.leetcode_username}
              </dd>
            </div>
          </dl>
          <p className="mt-5 border-t border-white/6 pt-4 text-xs leading-5 text-slate-500">
            These usernames stay fixed because they are used for friend discovery and scoring
            history.
          </p>
        </aside>
      </div>
    </main>
  );
}
