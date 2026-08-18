import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Check, Inbox, Send, UserMinus, UserPlus, UsersRound, X } from "lucide-react";
import { Link } from "react-router";

import {
  acceptFriendRequest,
  ApiError,
  deleteFriendRequest,
  getFriendRequests,
  getFriends,
  removeFriend,
  sendFriendRequest,
} from "../lib/api";
import { formatTimestamp } from "../lib/format";
import type {
  FriendRequestItem,
  FriendRequestsResponse,
  FriendsResponse,
  PublicUserSummary,
} from "../types/api";
import { ConfirmDialog } from "./ConfirmDialog";
import { UserAvatar } from "./UserAvatar";

interface FriendsPageProps {
  accessToken: string;
  onPendingCountChange: (count: number) => void;
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

function EmptyMessage({ children }: { children: string }) {
  return <div className="empty-compact">{children}</div>;
}

export function FriendsPage({ accessToken, onPendingCountChange }: FriendsPageProps) {
  const [friends, setFriends] = useState<FriendsResponse | null>(null);
  const [requests, setRequests] = useState<FriendRequestsResponse | null>(null);
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [activeRequestId, setActiveRequestId] = useState<string | null>(null);
  const [friendToRemove, setFriendToRemove] = useState<PublicUserSummary | null>(null);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadFriends = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [friendData, requestData] = await Promise.all([
        getFriends(accessToken),
        getFriendRequests(accessToken),
      ]);
      setFriends(friendData);
      setRequests(requestData);
      onPendingCountChange(requestData.incoming.length);
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Could not load friends.");
    } finally {
      setLoading(false);
    }
  }, [accessToken, onPendingCountChange]);

  useEffect(() => {
    void loadFriends();
  }, [loadFriends]);

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedUsername = username.trim().replace(/^@/, "");
    if (!normalizedUsername) return;
    setSending(true);
    setError(null);
    setNotice(null);
    try {
      const request = await sendFriendRequest(accessToken, normalizedUsername);
      setUsername("");
      setNotice(`Friend request sent to @${request.user.username}.`);
      await loadFriends();
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.message : "Could not send friend request.",
      );
    } finally {
      setSending(false);
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
      setNotice(successMessage);
      await loadFriends();
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
      setNotice(`@${friendToRemove.username} was removed from your friends.`);
      setFriendToRemove(null);
      await loadFriends();
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Could not remove friend.");
    } finally {
      setRemoving(false);
    }
  }

  const friendCount = friends?.friends.length ?? 0;
  const incomingCount = requests?.incoming.length ?? 0;

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
          <UsersRound aria-hidden="true" size={15} />
          <span><strong className="text-white">{friendCount}</strong> of 20 friends</span>
        </div>
      </section>

      <section className="panel panel-accent mt-6 p-4 sm:p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center">
          <div className="flex min-w-48 items-center gap-3">
            <span className="icon-chip icon-chip-orange">
              <UserPlus aria-hidden="true" size={18} />
            </span>
            <div>
              <h2 className="text-sm font-extrabold text-white">Add a friend</h2>
              <p className="mt-0.5 text-xs text-slate-500">Use their exact LeetRank username</p>
            </div>
          </div>
          <form className="flex flex-1 flex-col gap-2.5 sm:flex-row" onSubmit={handleSend}>
            <div className="relative flex-1">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">@</span>
              <input
                aria-label="LeetRank username"
                className="field-input py-3 pl-9"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="username"
                minLength={3}
                maxLength={31}
                required
              />
            </div>
            <button className="primary-button whitespace-nowrap py-3" type="submit" disabled={sending}>
              <UserPlus aria-hidden="true" size={16} />
              {sending ? "Sending…" : "Send request"}
            </button>
          </form>
        </div>
      </section>

      {error && <div className="error-banner mt-4">{error}</div>}
      {notice && <div className="success-banner mt-4">{notice}</div>}

      {loading && !friends ? (
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
              {friends?.friends.length ? (
                friends.friends.map((friend) => (
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
                <EmptyMessage>No friends yet. Add someone above to start competing.</EmptyMessage>
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
                {requests?.incoming.length ? (
                  requests.incoming.map((request) => (
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
                  <EmptyMessage>No incoming requests.</EmptyMessage>
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
                <span className="count-badge">{requests?.outgoing.length ?? 0}</span>
              </div>
              <div className="people-list">
                {requests?.outgoing.length ? (
                  requests.outgoing.map((request) => (
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
                  <EmptyMessage>No sent requests.</EmptyMessage>
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
