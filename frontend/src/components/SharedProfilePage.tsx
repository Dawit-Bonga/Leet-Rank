import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Check,
  Code2,
  ExternalLink,
  Link2,
  LoaderCircle,
  Target,
  UserCheck,
  UserPlus,
  UsersRound,
} from "lucide-react";
import { Link, useParams } from "react-router";

import { useFriendsData } from "../context/FriendsDataContext";
import {
  acceptFriendRequest,
  ApiError,
  getSharedProfile,
  sendFriendRequest,
} from "../lib/api";
import { formatDate } from "../lib/format";
import type { FriendsOverviewResponse, SharedProfile, UserProfile } from "../types/api";
import { Brand } from "./Brand";
import { UserAvatar } from "./UserAvatar";

interface SharedProfilePageProps {
  accessToken?: string;
  currentProfile?: UserProfile;
  overview?: FriendsOverviewResponse | null;
  refreshFriends?: () => Promise<void>;
  standalone?: boolean;
}

export function AuthenticatedSharedProfilePage({
  accessToken,
  currentProfile,
}: {
  accessToken: string;
  currentProfile: UserProfile;
}) {
  const { overview, refresh } = useFriendsData();
  return (
    <SharedProfilePage
      accessToken={accessToken}
      currentProfile={currentProfile}
      overview={overview}
      refreshFriends={() => refresh({ force: true })}
    />
  );
}

export function SharedProfilePage({
  accessToken,
  currentProfile,
  overview,
  refreshFriends,
  standalone = false,
}: SharedProfilePageProps) {
  const { username = "" } = useParams<{ username: string }>();
  const [profile, setProfile] = useState<SharedProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void getSharedProfile(username)
      .then((result) => {
        if (active) setProfile(result);
      })
      .catch((caughtError) => {
        if (!active) return;
        setProfile(null);
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Could not load this LeetClimb profile.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [username]);

  const friend = profile ? overview?.friends.find((item) => item.id === profile.id) : null;
  const incoming = profile
    ? overview?.incoming.find((item) => item.user.id === profile.id)
    : null;
  const outgoing = profile
    ? overview?.outgoing.find((item) => item.user.id === profile.id)
    : null;
  const isSelf = Boolean(profile && currentProfile?.id === profile.id);

  async function handleRelationshipAction() {
    if (!accessToken || !profile || !refreshFriends) return;
    setActing(true);
    setError(null);
    setNotice(null);
    try {
      if (incoming) {
        await acceptFriendRequest(accessToken, incoming.id);
        setNotice(`You and @${profile.username} are now friends.`);
      } else {
        await sendFriendRequest(accessToken, profile.username);
        setNotice(`Friend request sent to @${profile.username}.`);
      }
      await refreshFriends();
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Could not update this friend request.",
      );
    } finally {
      setActing(false);
    }
  }

  const returnPath = profile ? `/u/${profile.username}` : `/u/${username}`;
  const authQuery = `?next=${encodeURIComponent(returnPath)}`;

  const content = loading ? (
    <div className="mx-auto max-w-2xl">
      <div className="h-72 animate-pulse rounded-3xl bg-white/4" />
    </div>
  ) : !profile ? (
    <section className="panel mx-auto max-w-lg p-8 text-center">
      <span className="icon-chip mx-auto"><UsersRound aria-hidden="true" size={18} /></span>
      <h1 className="mt-5 text-2xl font-black text-white">Profile not found</h1>
      <p className="mt-2 text-sm leading-6 text-slate-400">
        {error ?? "This shared LeetClimb profile is unavailable."}
      </p>
      <Link className="secondary-button mt-6" to={accessToken ? "/" : "/"}>
        <ArrowLeft aria-hidden="true" size={15} /> Back to LeetClimb
      </Link>
    </section>
  ) : (
    <div className="mx-auto max-w-2xl">
      <section className="shared-profile-card">
        <div className="shared-profile-grid" />
        <div className="relative z-10 flex flex-col items-center text-center">
          <p className="landing-pill"><Link2 aria-hidden="true" size={13} /> Shared profile</p>
          <div className="mt-7 rounded-full bg-orange-400/5 p-2 ring-1 ring-orange-400/10">
            <UserAvatar highlighted name={profile.display_name} size="lg" />
          </div>
          <h1 className="mt-5 text-3xl font-black tracking-[-0.04em] text-white sm:text-4xl">
            {profile.display_name}
          </h1>
          <p className="mt-1 text-sm font-bold text-slate-500">@{profile.username}</p>
          <p className="mt-5 max-w-md text-sm leading-6 text-slate-400">
            Add {profile.display_name.split(" ")[0]} to your circle and keep each other accountable.
          </p>

          <div className="mt-7 grid w-full gap-3 sm:grid-cols-3">
            <div className="shared-profile-detail">
              <Code2 aria-hidden="true" size={16} />
              <span>LeetCode</span>
              <strong>@{profile.leetcode_username}</strong>
            </div>
            <div className="shared-profile-detail">
              <Target aria-hidden="true" size={16} />
              <span>Weekly goal</span>
              <strong>{profile.weekly_problem_goal} solves</strong>
            </div>
            <div className="shared-profile-detail">
              <UserCheck aria-hidden="true" size={16} />
              <span>Member since</span>
              <strong>{formatDate(profile.joined_at)}</strong>
            </div>
          </div>

          {error && <div className="error-banner mt-5 w-full">{error}</div>}
          {notice && <div className="success-banner mt-5 w-full">{notice}</div>}

          <div className="mt-7 flex w-full flex-col justify-center gap-3 sm:flex-row">
            {!accessToken ? (
              <>
                <Link className="primary-button" to={`/sign-up${authQuery}`}>
                  <UserPlus aria-hidden="true" size={16} /> Join to add {profile.display_name.split(" ")[0]}
                </Link>
                <Link className="secondary-button" to={`/sign-in${authQuery}`}>Sign in</Link>
              </>
            ) : isSelf ? (
              <Link className="primary-button" to="/profile">View your profile</Link>
            ) : friend ? (
              <Link className="primary-button" to={`/friends/${friend.id}`}>
                <UserCheck aria-hidden="true" size={16} /> View friend profile
              </Link>
            ) : outgoing ? (
              <button className="secondary-button" disabled type="button">
                <Check aria-hidden="true" size={16} /> Request sent
              </button>
            ) : overview ? (
              <button
                className="primary-button"
                disabled={acting}
                type="button"
                onClick={() => void handleRelationshipAction()}
              >
                {acting ? (
                  <LoaderCircle aria-hidden="true" className="animate-spin" size={16} />
                ) : incoming ? (
                  <Check aria-hidden="true" size={16} />
                ) : (
                  <UserPlus aria-hidden="true" size={16} />
                )}
                {acting ? "Updating…" : incoming ? "Accept request" : "Add friend"}
              </button>
            ) : (
              <button className="secondary-button" disabled type="button">
                <LoaderCircle aria-hidden="true" className="animate-spin" size={16} /> Checking connection…
              </button>
            )}
            <a
              className="secondary-button"
              href={`https://leetcode.com/u/${encodeURIComponent(profile.leetcode_username)}/`}
              rel="noreferrer"
              target="_blank"
            >
              LeetCode <ExternalLink aria-hidden="true" size={14} />
            </a>
          </div>
          <p className="mt-5 text-[0.68rem] leading-5 text-slate-600">
            Scores and recent activity stay private until you become friends.
          </p>
        </div>
      </section>
    </div>
  );

  if (!standalone) {
    return <main className="page-container">{content}</main>;
  }

  return (
    <main className="landing-page min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 sm:px-8">
        <Link className="rounded-xl focus:outline-none focus:ring-4 focus:ring-orange-400/20" to="/">
          <Brand compact />
        </Link>
        <Link className="text-button" to={`/sign-in${authQuery}`}>Sign in</Link>
      </header>
      <div className="px-5 py-12 sm:px-8 sm:py-20">{content}</div>
    </main>
  );
}
