import {
  ArrowRight,
  Check,
  Code2,
  Crown,
  Link2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  Trophy,
  UsersRound,
  Zap,
} from "lucide-react";
import { Link } from "react-router";

import { Brand } from "./Brand";

const previewPlayers = [
  { rank: 1, name: "Maya", username: "mayacodes", points: 140 },
  { rank: 2, name: "You", username: "yourhandle", points: 110, current: true },
  { rank: 3, name: "Jordan", username: "jordan_dev", points: 80 },
];

function LeaderboardPreview({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`landing-preview ${compact ? "landing-preview-compact" : ""}`}>
      <div className="flex items-center justify-between border-b border-white/7 px-4 py-3 sm:px-5">
        <div>
          <p className="text-xs font-black text-white">Friends leaderboard</p>
          <p className="mt-0.5 text-[0.62rem] text-slate-600">Past week</p>
        </div>
        <div className="flex rounded-lg border border-white/6 bg-slate-950/60 p-1">
          <span className="rounded-md bg-slate-800 px-2.5 py-1 text-[0.58rem] font-bold text-white">
            Week
          </span>
          <span className="px-2.5 py-1 text-[0.58rem] font-bold text-slate-600">Month</span>
        </div>
      </div>
      <div className="divide-y divide-white/6">
        {previewPlayers.map((player) => (
          <div
            className={`grid grid-cols-[2.25rem_1fr_auto] items-center gap-3 px-4 py-3.5 sm:px-5 ${
              player.current ? "bg-orange-400/7 shadow-[inset_3px_0_0_rgba(251,146,60,0.8)]" : ""
            }`}
            key={player.rank}
          >
            <span
              className={`grid size-7 place-items-center rounded-lg text-xs font-black ${
                player.rank === 1
                  ? "border border-orange-400/20 bg-orange-400/12 text-orange-200"
                  : "border border-white/6 bg-slate-800/80 text-slate-500"
              }`}
            >
              {player.rank === 1 ? <Crown aria-label="First place" size={14} /> : player.rank}
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="truncate text-xs font-extrabold text-white sm:text-sm">{player.name}</p>
                {player.current && (
                  <span className="rounded-full bg-orange-400/10 px-1.5 py-0.5 text-[0.5rem] font-black uppercase tracking-wider text-orange-300">
                    You
                  </span>
                )}
              </div>
              <p className="truncate text-[0.62rem] text-slate-600">@{player.username}</p>
            </div>
            <p className="text-sm font-black tabular-nums text-white sm:text-base">
              {player.points}<span className="ml-1 text-[0.6rem] text-slate-600">pts</span>
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

const steps = [
  {
    icon: Link2,
    number: "01",
    title: "Connect LeetCode",
    description: "Add your public username. Scoring begins when you join—not before.",
  },
  {
    icon: Code2,
    number: "02",
    title: "Solve problems",
    description: "Keep coding normally. Accepted submissions are picked up automatically.",
  },
  {
    icon: Trophy,
    number: "03",
    title: "Climb together",
    description: "Compare weekly, monthly, and all-time points with a focused friend group.",
  },
];

export function LandingPage() {
  return (
    <main className="landing-page min-h-screen overflow-hidden">
      <header className="relative z-20 mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
        <Link className="rounded-xl focus:outline-none focus:ring-4 focus:ring-orange-400/20" to="/">
          <Brand compact />
        </Link>
        <nav aria-label="Main navigation" className="hidden items-center gap-7 md:flex">
          <a className="landing-nav-link" href="#how-it-works">How it works</a>
          <a className="landing-nav-link" href="#product">Product</a>
          <a className="landing-nav-link" href="#scoring">Scoring</a>
        </nav>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link className="text-button px-2.5 sm:px-3" to="/sign-in">Sign in</Link>
          <Link className="compact-primary-button px-3.5 py-2.5 sm:px-4" to="/sign-up">
            Get started <ArrowRight aria-hidden="true" className="hidden sm:block" size={14} />
          </Link>
        </div>
      </header>

      <section className="relative mx-auto grid max-w-7xl items-center gap-14 px-5 pb-24 pt-16 sm:px-8 sm:pt-24 lg:grid-cols-[1.05fr_0.95fr] lg:gap-20 lg:pb-32">
        <div className="landing-hero-glow" />
        <div className="relative z-10">
          <div className="landing-pill">
            <Sparkles aria-hidden="true" size={13} /> Friendly accountability for LeetCode
          </div>
          <h1 className="mt-7 max-w-3xl text-5xl font-black leading-[0.98] tracking-[-0.055em] text-white sm:text-6xl lg:text-7xl">
            Turn practice into <span className="landing-gradient-text">friendly competition.</span>
          </h1>
          <p className="mt-7 max-w-xl text-base leading-7 text-slate-400 sm:text-lg sm:leading-8">
            Earn points for accepted LeetCode solves, stay accountable to your weekly goal,
            and see where you stand with the friends who keep you moving.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Link className="primary-button px-6" to="/sign-up">
              Create an account <ArrowRight aria-hidden="true" size={16} />
            </Link>
            <Link className="secondary-button px-6" to="/sign-in">Sign in</Link>
          </div>
          <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 text-xs font-semibold text-slate-500">
            {['No code access', 'Scoring starts after joining', 'Automatic sync'].map((item) => (
              <span className="flex items-center gap-1.5" key={item}>
                <Check aria-hidden="true" className="text-teal-400" size={13} /> {item}
              </span>
            ))}
          </div>
        </div>

        <div className="relative z-10 mx-auto w-full max-w-xl">
          <div className="absolute -inset-8 rounded-full bg-orange-500/8 blur-3xl" />
          <div className="landing-hero-card relative">
            <div className="mb-3 flex items-center justify-between px-1">
              <span className="text-[0.62rem] font-extrabold uppercase tracking-[0.18em] text-slate-600">Live product preview</span>
              <span className="flex items-center gap-1.5 text-[0.62rem] font-bold text-teal-400">
                <RefreshCw aria-hidden="true" size={11} /> Auto-synced
              </span>
            </div>
            <div className="mb-3 grid grid-cols-3 gap-2.5">
              <div className="landing-mini-stat landing-mini-stat-primary">
                <p>Rank</p><strong>#2</strong>
              </div>
              <div className="landing-mini-stat">
                <p>Week</p><strong>110 <small>pts</small></strong>
              </div>
              <div className="landing-mini-stat">
                <p>Goal</p><strong>4<small>/5</small></strong>
                <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-950">
                  <div className="h-full w-4/5 rounded-full bg-teal-400" />
                </div>
              </div>
            </div>
            <LeaderboardPreview compact />
          </div>
        </div>
      </section>

      <section className="landing-section" id="how-it-works">
        <div className="landing-section-heading">
          <p className="eyebrow">Simple by design</p>
          <h2>Practice as usual. LeetClimb handles the competition.</h2>
          <p>No new routine to manage—just a clearer reason to keep showing up.</p>
        </div>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {steps.map(({ icon: Icon, number, title, description }) => (
            <article className="landing-feature-card" key={number}>
              <div className="flex items-center justify-between">
                <span className="icon-chip icon-chip-orange"><Icon aria-hidden="true" size={18} /></span>
                <span className="text-xs font-black tracking-[0.18em] text-slate-700">{number}</span>
              </div>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section grid items-center gap-12 lg:grid-cols-[0.85fr_1.15fr]" id="product">
        <div>
          <p className="eyebrow">Built for your circle</p>
          <h2 className="mt-3 text-3xl font-black tracking-[-0.04em] text-white sm:text-4xl">
            Enough competition to push you. Not enough noise to distract you.
          </h2>
          <p className="mt-5 max-w-xl text-sm leading-7 text-slate-400 sm:text-base">
            LeetClimb keeps the group intentionally small and the feedback immediate. See the
            score, close the gap, and celebrate the solve.
          </p>
          <div className="mt-8 space-y-3">
            {[
              [UsersRound, 'A focused leaderboard for you and your friends'],
              [Target, 'A visible weekly goal that keeps momentum honest'],
              [ShieldCheck, 'Points count only after you join LeetClimb'],
            ].map(([Icon, text]) => {
              const FeatureIcon = Icon as typeof UsersRound;
              return (
                <div className="flex items-center gap-3 text-sm font-bold text-slate-300" key={text as string}>
                  <span className="icon-chip icon-chip-teal"><FeatureIcon aria-hidden="true" size={16} /></span>
                  {text as string}
                </div>
              );
            })}
          </div>
        </div>
        <div className="landing-product-frame">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-black text-white">Your weekly race</p>
              <p className="mt-1 text-xs text-slate-600">A clear view of the people keeping pace</p>
            </div>
            <span className="landing-status"><span /> Synced</span>
          </div>
          <LeaderboardPreview />
        </div>
      </section>

      <section className="landing-section" id="scoring">
        <div className="landing-section-heading">
          <p className="eyebrow">Points with purpose</p>
          <h2>Harder solve. Bigger move.</h2>
          <p>A transparent scoring system makes every accepted problem easy to understand.</p>
        </div>
        <div className="mx-auto mt-10 grid max-w-3xl gap-3 sm:grid-cols-3">
          {[
            ['Easy', '+10', 'text-teal-300', 'border-teal-400/15'],
            ['Medium', '+20', 'text-amber-300', 'border-amber-400/15'],
            ['Hard', '+30', 'text-rose-300', 'border-rose-400/15'],
          ].map(([difficulty, points, color, border]) => (
            <div className={`landing-score-card ${border}`} key={difficulty}>
              <span className={`text-xs font-extrabold uppercase tracking-[0.14em] ${color}`}>{difficulty}</span>
              <strong>{points}<small> pts</small></strong>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-20 pt-8 sm:px-8 sm:pb-28">
        <div className="landing-cta">
          <div className="relative z-10">
            <Zap aria-hidden="true" className="mx-auto text-orange-300" size={24} />
            <h2 className="mt-5 text-3xl font-black tracking-[-0.04em] text-white sm:text-4xl">Make the next solve count.</h2>
            <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-slate-400">Create your circle, set your target, and turn consistency into something everyone can see.</p>
            <Link className="primary-button mt-7 px-6" to="/sign-up">Create an account <ArrowRight aria-hidden="true" size={16} /></Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/6">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-5 py-7 sm:flex-row sm:px-8">
          <Brand compact />
          <p className="text-xs text-slate-600">Practice together. Climb together.</p>
          <div className="flex items-center gap-5 text-xs font-bold text-slate-500">
            <a className="hover:text-white" href="#how-it-works">How it works</a>
            <Link className="hover:text-white" to="/sign-in">Sign in</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
