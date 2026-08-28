import { useEffect, useState } from "react";
import {
  Check,
  Clock3,
  Inbox,
  LoaderCircle,
  Search,
  Send,
  UserCheck,
  UserMinus,
  UserPlus,
  UsersRound,
  X,
} from "lucide-react";
import { Link } from "react-router";

import {
  acceptFriendRequest,
  ApiError,
  deleteFriendRequest,
  removeFriend,
  searchUsers,
  sendFriendRequest,
} from "../lib/api";
import { useFriendsData } from "../context/FriendsDataContext";
import { formatTimestamp } from "../lib/format";
import type {
  FriendRequestItem,
  PublicUserSummary,
  UserSearchItem,
  UserSearchResponse,
} from "../types/api";
import { ConfirmDialog } from "./ConfirmDialog";
import { EmptyState } from "./EmptyState";
import { UserAvatar } from "./UserAvatar";

interface FriendsPageProps {
  accessToken: string;
}

function Person({ user, profileHref }: { user: PublicUserSummary; profileHref?: string }) {
  const content = (
    <div className="flex min-w-0 items-center gap-3">
      <UserAvatar name={user.display_name} />
      <div className="min-w-0">
        <p className="truncate text-sm font-extrabold text-white">{user.display_name}</p>
        <p className="truncate text-xs text-slate-500">@{user.username}</p>
      </div>
    </div>
  );
  return profileHref ? (
    <Link
      aria-label={`View ${user.display_name}’s profile`}
      className="min-w-0 flex-1 rounded-lg transition hover:opacity-85 focus:outline-none focus:ring-4 focus:ring-orange-400/10"
      to={profileHref}
    >
      {content}
    </Link>
  ) : content;
}

export function FriendsPage({ accessToken }: FriendsPageProps) {
  const {
    overview,
    initialLoading: loading,
    refreshing,
    error: overviewError,
    refresh,
  } = useFriendsData();
  const [username, setUsername] = useState("");
  const [searchResults, setSearchResults] = useState<UserSearchResponse | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [activeSearchUserId, setActiveSearchUserId] = useState<string | null>(null);
  const [activeRequestId, setActiveRequestId] = useState<string | null>(null);
  const [friendToRemove, setFriendToRemove] = useState<PublicUserSummary | null>(null);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const normalizedSearch = username.trim().replace(/^@/, "");

  useEffect(() => {
    if (normalizedSearch.length < 3) {
      setSearchResults(null);
      setSearchLoading(false);
      setSearchError(null);
      return;
    }
    if (!/^[A-Za-z0-9][A-Za-z0-9_]{2,29}$/.test(normalizedSearch)) {
      setSearchResults(null);
      setSearchLoading(false);
      setSearchError("Use only letters, numbers, and underscores.");
      return;
    }

    let active = true;
    setSearchLoading(true);
    setSearchResults(null);
    setSearchError(null);
    const timeout = window.setTimeout(() => {
      void searchUsers(accessToken, normalizedSearch)
        .then((results) => {
          if (active) setSearchResults(results);
        })
        .catch((caughtError) => {
          if (!active) return;
          setSearchError(
            caughtError instanceof ApiError
              ? caughtError.message
              : "Could not search for users.",
          );
        })
        .finally(() => {
          if (active) setSearchLoading(false);
        });
    }, 300);

    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [accessToken, normalizedSearch]);

  async function handleSearchAction(result: UserSearchItem) {
    if (
      result.relationship !== "NONE" &&
      !(result.relationship === "INCOMING" && result.friend_request_id)
    ) {
      return;
    }
    setActiveSearchUserId(result.user.id);
    setError(null);
    setNotice(null);
    try {
      if (result.relationship === "INCOMING" && result.friend_request_id) {
        await acceptFriendRequest(accessToken, result.friend_request_id);
        setNotice(`You and @${result.user.username} are now friends.`);
        setSearchResults((current) =>
          current
            ? {
                users: current.users.map((item) =>
                  item.user.id === result.user.id
                    ? { ...item, relationship: "FRIEND", friend_request_id: null }
                    : item,
                ),
              }
            : current,
        );
      } else {
        const request = await sendFriendRequest(accessToken, result.user.username);
        setNotice(`Friend request sent to @${request.user.username}.`);
        setSearchResults((current) =>
          current
            ? {
                users: current.users.map((item) =>
                  item.user.id === result.user.id
                    ? {
                        ...item,
                        relationship: "OUTGOING",
                        friend_request_id: request.id,
                      }
                    : item,
                ),
              }
            : current,
        );
      }
      await refresh({ force: true });
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.message : "Could not send friend request.",
      );
    } finally {
      setActiveSearchUserId(null);
    }
  }

  async function handleRequestAction(
    request: FriendRequestItem,
    action: "accept" | "delete",
    successMessage: string,
  ) {
    setActiveRequestId(request.id);
    setError(null);
    setNotice(null);
    try {
      if (action === "accept") {
        await acceptFriendRequest(accessToken, request.id);
      } else {
        await deleteFriendRequest(accessToken, request.id);
      }
      setSearchResults((current) =>
        current
          ? {
              users: current.users.map((item) =>
                item.user.id === request.user.id
                  ? {
                      ...item,
                      relationship: action === "accept" ? "FRIEND" : "NONE",
                      friend_request_id: null,
                    }
                  : item,
              ),
            }
          : current,
      );
      setNotice(successMessage);
      await refresh({ force: true });
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Could not update request.");
    } finally {
      setActiveRequestId(null);
    }
  }

  async function handleRemoveFriend() {
    if (!friendToRemove) return;
    setRemoving(true);
    setError(null);
    try {
      await removeFriend(accessToken, friendToRemove.id);
      setSearchResults((current) =>
        current
          ? {
              users: current.users.map((item) =>
                item.user.id === friendToRemove.id
                  ? { ...item, relationship: "NONE", friend_request_id: null }
                  : item,
              ),
            }
          : current,
      );
      setNotice(`@${friendToRemove.username} was removed from your friends.`);
      setFriendToRemove(null);
      await refresh({ force: true });
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Could not remove friend.");
    } finally {
      setRemoving(false);
    }
  }

  const friendCount = overview?.friends.length ?? 0;
  const incomingCount = overview?.incoming.length ?? 0;

  return (
    <main className="page-container">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">Your circle</p>
          <h1 className="page-title mt-2">Friends</h1>
          <p className="page-description">
            Build a focused circle of people who keep showing up.
          </p>
        </div>
        <div className="sync-status">
          {refreshing ? (
            <LoaderCircle aria-label="Updating friends" className="animate-spin" size={15} />
          ) : (
            <UsersRound aria-hidden="true" size={15} />
          )}
          <span><strong className="text-white">{friendCount}</strong> of 20 friends</span>
        </div>
      </section>

      <section className="panel panel-accent mt-6">
        <div className="flex flex-col gap-4 p-4 md:flex-row md:items-center sm:p-5">
          <div className="flex min-w-48 items-center gap-3">
            <span className="icon-chip icon-chip-orange">
              <UserPlus aria-hidden="true" size={18} />
            </span>
            <div>
              <h2 className="text-sm font-extrabold text-white">Add a friend</h2>
              <p className="mt-0.5 text-xs text-slate-500">Search by LeetClimb username</p>
            </div>
          </div>
          <div className="relative flex-1">
            <Search
              aria-hidden="true"
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600"
              size={17}
            />
            <input
              aria-label="Search LeetClimb usernames"
              className="field-input field-input-compact field-input-leading field-input-trailing"
              type="search"
              value={username}
              onChange={(event) => {
                setUsername(event.target.value);
                setNotice(null);
              }}
              placeholder="Start typing a username"
              maxLength={31}
            />
            {searchLoading && (
              <LoaderCircle
                aria-label="Searching"
                className="absolute right-4 top-1/2 -translate-y-1/2 animate-spin text-orange-400"
                size={17}
              />
            )}
          </div>
        </div>

        {normalizedSearch.length < 3 ? (
          <p className="border-t border-white/6 px-5 py-3 text-center text-xs text-slate-600">
            Enter at least three characters to find someone.
          </p>
        ) : searchError ? (
          <p className="border-t border-red-400/10 bg-red-400/5 px-5 py-3 text-center text-xs text-red-200">
            {searchError}
          </p>
        ) : searchResults ? (
          <div className="border-t border-white/6">
            {searchResults.users.length ? (
              <div className="people-list">
                {searchResults.users.map((result) => (
                  <div className="person-row" key={result.user.id}>
                    <Person
                      profileHref={
                        result.relationship === "FRIEND"
                          ? `/friends/${result.user.id}`
                          : undefined
                      }
                      user={result.user}
                    />
                    {result.relationship === "NONE" && (
                      <button
                        className="compact-primary-button"
                        type="button"
                        disabled={activeSearchUserId === result.user.id}
                        onClick={() => void handleSearchAction(result)}
                      >
                        <UserPlus aria-hidden="true" size={14} />
                        {activeSearchUserId === result.user.id ? "Sending…" : "Add"}
                      </button>
                    )}
                    {result.relationship === "INCOMING" && (
                      <button
                        className="compact-primary-button"
                        type="button"
                        disabled={activeSearchUserId === result.user.id}
                        onClick={() => void handleSearchAction(result)}
                      >
                        <Check aria-hidden="true" size={14} />
                        {activeSearchUserId === result.user.id ? "Accepting…" : "Accept"}
                      </button>
                    )}
                    {result.relationship === "OUTGOING" && (
                      <span className="inline-flex items-center gap-1.5 px-2 text-xs font-bold text-slate-500">
                        <Clock3 aria-hidden="true" size={14} /> Requested
                      </span>
                    )}
                    {result.relationship === "FRIEND" && (
                      <span className="inline-flex items-center gap-1.5 px-2 text-xs font-bold text-orange-300">
                        <UserCheck aria-hidden="true" size={14} /> Friends
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                compact
                description="Try another LeetClimb username."
                icon={Search}
                title="No matching users"
              />
            )}
          </div>
        ) : null}
      </section>

      {(error || overviewError) && (
        <div className="error-banner mt-4">
          {error ||
            (overview
              ? `${overviewError} Showing the most recently loaded information.`
              : overviewError)}
        </div>
      )}
      {notice && <div className="success-banner mt-4">{notice}</div>}

      {loading && !overview ? (
        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(18rem,0.75fr)]">
          <div className="h-72 animate-pulse rounded-2xl bg-white/4" />
          <div className="h-56 animate-pulse rounded-2xl bg-white/4" />
        </div>
      ) : (
        <div className="mt-5 grid items-start gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(18rem,0.75fr)]">
          <section className="panel">
            <div className="panel-header">
              <div className="flex items-center gap-3">
                <span className="icon-chip">
                  <UsersRound aria-hidden="true" size={18} />
                </span>
                <div>
                  <h2 className="section-heading">Your friends</h2>
                  <p className="section-kicker">Everyone competing on your leaderboard</p>
                </div>
              </div>
              <span className="count-badge">{friendCount}</span>
            </div>
            <div className="people-list">
              {overview?.friends.length ? (
                overview.friends.map((friend) => (
                  <div className="person-row" key={friend.id}>
                    <Person profileHref={`/friends/${friend.id}`} user={friend} />
                    <button
                      aria-label={`Remove ${friend.display_name}`}
                      className="compact-secondary-button"
                      type="button"
                      onClick={() => setFriendToRemove(friend)}
                    >
                      <UserMinus aria-hidden="true" size={14} />
                      <span className="hidden sm:inline">Remove</span>
                    </button>
                  </div>
                ))
              ) : (
                <EmptyState
                  description="Search above to build your first leaderboard."
                  icon={UsersRound}
                  title="Your circle is waiting"
                />
              )}
            </div>
          </section>

          <aside className="space-y-5">
            <section className={`panel ${incomingCount > 0 ? "panel-accent border-orange-400/15" : ""}`}>
              <div className="panel-header">
                <div className="flex items-center gap-3">
                  <span className={incomingCount > 0 ? "icon-chip icon-chip-orange" : "icon-chip"}>
                    <Inbox aria-hidden="true" size={17} />
                  </span>
                  <div>
                    <h2 className="section-heading">Incoming</h2>
                    <p className="section-kicker">Waiting for your response</p>
                  </div>
                </div>
                <span className="count-badge">{incomingCount}</span>
              </div>
              <div className="people-list">
                {overview?.incoming.length ? (
                  overview.incoming.map((request) => (
                    <div className="px-4 py-3.5" key={request.id}>
                      <Person user={request.user} />
                      <div className="ml-14 mt-3 flex gap-2">
                        <button
                          className="compact-primary-button inline-flex items-center gap-1.5"
                          type="button"
                          disabled={activeRequestId === request.id}
                          onClick={() =>
                            void handleRequestAction(
                              request,
                              "accept",
                              `You and @${request.user.username} are now friends.`,
                            )
                          }
                        >
                          <Check aria-hidden="true" size={13} /> Accept
                        </button>
                        <button
                          aria-label={`Decline request from ${request.user.display_name}`}
                          className="compact-secondary-button inline-flex items-center gap-1.5"
                          type="button"
                          disabled={activeRequestId === request.id}
                          onClick={() =>
                            void handleRequestAction(request, "delete", "Friend request declined.")
                          }
                        >
                          <X aria-hidden="true" size={13} /> Decline
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyState
                    compact
                    description="New requests will appear here."
                    icon={Inbox}
                    title="Inbox clear"
                  />
                )}
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div className="flex items-center gap-3">
                  <span className="icon-chip">
                    <Send aria-hidden="true" size={16} />
                  </span>
                  <div>
                    <h2 className="section-heading">Sent</h2>
                    <p className="section-kicker">Awaiting a response</p>
                  </div>
                </div>
              <span className="count-badge">{overview?.outgoing.length ?? 0}</span>
              </div>
              <div className="people-list">
                {overview?.outgoing.length ? (
                  overview.outgoing.map((request) => (
                    <div className="px-4 py-3.5" key={request.id}>
                      <Person user={request.user} />
                      <div className="ml-14 mt-2 flex items-center justify-between gap-3">
                        <p className="text-[0.65rem] text-slate-600">
                          Sent {formatTimestamp(request.created_at)}
                        </p>
                        <button
                          className="text-button px-2 py-1 text-xs"
                          type="button"
                          disabled={activeRequestId === request.id}
                          onClick={() =>
                            void handleRequestAction(request, "delete", "Friend request canceled.")
                          }
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyState
                    compact
                    description="Requests you send will stay here until answered."
                    icon={Send}
                    title="Nothing pending"
                  />
                )}
              </div>
            </section>
          </aside>
        </div>
      )}

      <ConfirmDialog
        open={friendToRemove !== null}
        title="Remove this friend?"
        description={
          friendToRemove
            ? `You and @${friendToRemove.username} will disappear from each other’s friends lists and leaderboards. Scores and activity will not be deleted.`
            : ""
        }
        confirmLabel="Remove friend"
        loading={removing}
        onCancel={() => setFriendToRemove(null)}
        onConfirm={() => void handleRemoveFriend()}
      />
    </main>
  );
}
