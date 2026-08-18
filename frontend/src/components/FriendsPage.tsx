import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  acceptFriendRequest,
  ApiError,
  deleteFriendRequest,
  getFriendRequests,
  getFriends,
  removeFriend,
  sendFriendRequest,
} from "../lib/api";
import { formatTimestamp, initials } from "../lib/format";
import type {
  FriendRequestItem,
  FriendRequestsResponse,
  FriendsResponse,
  PublicUserSummary,
} from "../types/api";
import { ConfirmDialog } from "./ConfirmDialog";

interface FriendsPageProps {
  accessToken: string;
  onPendingCountChange: (count: number) => void;
}

function Person({ user }: { user: PublicUserSummary }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="grid size-11 shrink-0 place-items-center rounded-full bg-slate-800 text-xs font-bold text-slate-300">
        {initials(user.display_name)}
      </div>
      <div className="min-w-0">
        <p className="truncate font-bold text-white">{user.display_name}</p>
        <p className="truncate text-xs text-slate-500">@{user.username}</p>
      </div>
    </div>
  );
}

function EmptyMessage({ children }: { children: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/10 px-5 py-8 text-center text-sm text-slate-500">
      {children}
    </div>
  );
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

  return (
    <main className="mx-auto max-w-6xl px-5 pb-28 pt-10 sm:px-8 sm:py-14">
      <section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">Your circle</p>
          <h1 className="mt-3 text-4xl font-black tracking-tight sm:text-5xl">Friends</h1>
          <p className="mt-3 max-w-xl text-slate-400">
            Build a small circle that keeps showing up. Add people by their exact LeetRank
            username.
          </p>
        </div>
        <div className="rounded-xl border border-white/8 bg-white/3 px-4 py-3 text-sm">
          <span className="font-black text-white">{friendCount}</span>
          <span className="text-slate-500"> / 20 accepted friends</span>
        </div>
      </section>

      <section className="mt-8 rounded-2xl border border-white/8 bg-slate-900/70 p-5 sm:p-6">
        <h2 className="font-bold text-white">Add a friend</h2>
        <p className="mt-1 text-sm text-slate-500">Their account must already be on LeetRank.</p>
        <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={handleSend}>
          <div className="relative flex-1">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">@</span>
            <input
              aria-label="LeetRank username"
              className="field-input pl-9"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="username"
              minLength={3}
              maxLength={31}
              required
            />
          </div>
          <button className="primary-button sm:min-w-32" type="submit" disabled={sending}>
            {sending ? "Sending…" : "Send request"}
          </button>
        </form>
      </section>

      {error && <div className="error-banner mt-6">{error}</div>}
      {notice && <div className="success-banner mt-6">{notice}</div>}

      {loading && !friends ? (
        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          {[0, 1].map((item) => (
            <div className="h-56 animate-pulse rounded-2xl bg-white/4" key={item} />
          ))}
        </div>
      ) : (
        <div className="mt-8 grid items-start gap-6 lg:grid-cols-2">
          <section className="social-card lg:col-span-2">
            <div className="social-card-header">
              <div>
                <h2 className="text-lg font-black text-white">Incoming requests</h2>
                <p className="mt-1 text-xs text-slate-500">People waiting for your response</p>
              </div>
              <span className="count-badge">{requests?.incoming.length ?? 0}</span>
            </div>
            <div className="space-y-3 p-5">
              {requests?.incoming.length ? (
                requests.incoming.map((request) => (
                  <div className="social-row" key={request.id}>
                    <Person user={request.user} />
                    <div className="flex shrink-0 gap-2">
                      <button
                        className="compact-primary-button"
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
                        Accept
                      </button>
                      <button
                        className="compact-secondary-button"
                        type="button"
                        disabled={activeRequestId === request.id}
                        onClick={() =>
                          void handleRequestAction(request, "delete", "Friend request declined.")
                        }
                      >
                        Decline
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyMessage>No incoming friend requests.</EmptyMessage>
              )}
            </div>
          </section>

          <section className="social-card">
            <div className="social-card-header">
              <div>
                <h2 className="text-lg font-black text-white">Your friends</h2>
                <p className="mt-1 text-xs text-slate-500">Everyone on your leaderboard</p>
              </div>
              <span className="count-badge">{friendCount}</span>
            </div>
            <div className="space-y-3 p-5">
              {friends?.friends.length ? (
                friends.friends.map((friend) => (
                  <div className="social-row" key={friend.id}>
                    <Person user={friend} />
                    <button
                      aria-label={`Remove ${friend.display_name}`}
                      className="compact-secondary-button"
                      type="button"
                      onClick={() => setFriendToRemove(friend)}
                    >
                      Remove
                    </button>
                  </div>
                ))
              ) : (
                <EmptyMessage>No friends yet. Send your first request above.</EmptyMessage>
              )}
            </div>
          </section>

          <section className="social-card">
            <div className="social-card-header">
              <div>
                <h2 className="text-lg font-black text-white">Sent requests</h2>
                <p className="mt-1 text-xs text-slate-500">Waiting for a response</p>
              </div>
              <span className="count-badge">{requests?.outgoing.length ?? 0}</span>
            </div>
            <div className="space-y-3 p-5">
              {requests?.outgoing.length ? (
                requests.outgoing.map((request) => (
                  <div className="social-row" key={request.id}>
                    <div>
                      <Person user={request.user} />
                      <p className="ml-14 mt-1 text-[0.68rem] text-slate-600">
                        Sent {formatTimestamp(request.created_at)}
                      </p>
                    </div>
                    <button
                      className="compact-secondary-button"
                      type="button"
                      disabled={activeRequestId === request.id}
                      onClick={() =>
                        void handleRequestAction(request, "delete", "Friend request canceled.")
                      }
                    >
                      Cancel
                    </button>
                  </div>
                ))
              ) : (
                <EmptyMessage>No outgoing requests.</EmptyMessage>
              )}
            </div>
          </section>
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
