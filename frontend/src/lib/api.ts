import type {
  CurrentUser,
  ActivityResponse,
  FriendRequestItem,
  FriendProfileResponse,
  FriendsOverviewResponse,
  FriendRequestsResponse,
  FriendsResponse,
  LeaderboardPeriod,
  LeaderboardResponse,
  OnboardingPayload,
  PublicUserSummary,
  ScoresResponse,
  UserProfile,
  UserSettingsPayload,
  UserSettingsResponse,
  UserSearchResponse,
} from "../types/api";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);
const API_TIMEOUT_MS = 90_000;

export type ApiErrorKind =
  | "AUTHENTICATION"
  | "VALIDATION"
  | "UPSTREAM"
  | "UNAVAILABLE"
  | "SERVER"
  | "NETWORK"
  | "TIMEOUT"
  | "RESPONSE"
  | "UNKNOWN";

function errorKindForStatus(status: number): ApiErrorKind {
  if (status === 401 || status === 403) return "AUTHENTICATION";
  if (status === 400 || status === 409 || status === 422) return "VALIDATION";
  if (status === 502) return "UPSTREAM";
  if (status === 503 || status === 504) return "UNAVAILABLE";
  if (status >= 500) return "SERVER";
  return "UNKNOWN";
}

function defaultErrorMessage(status: number): string {
  if (status === 401) return "Your session expired. Please sign in again.";
  if (status === 502) return "LeetCode could not be reached. Try again shortly.";
  if (status === 503 || status === 504) {
    return "LeetRank is temporarily unavailable. Try again shortly.";
  }
  if (status >= 500) return "Something failed on our server. Your data was not changed.";
  return `Request failed with status ${status}.`;
}

export class ApiError extends Error {
  status: number;
  code: string | null;
  kind: ApiErrorKind;

  constructor(
    message: string,
    status: number,
    code: string | null = null,
    kind: ApiErrorKind = errorKindForStatus(status),
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.kind = kind;
  }
}

async function request<T>(
  path: string,
  accessToken: string,
  init: RequestInit = {},
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      signal: init.signal ?? controller.signal,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
  } catch (caughtError) {
    const aborted = caughtError instanceof Error && caughtError.name === "AbortError";
    throw new ApiError(
      aborted
        ? "LeetRank took too long to respond. Try again."
        : "Could not reach LeetRank. Check your connection and try again.",
      0,
      aborted ? "request_timeout" : "network_unavailable",
      aborted ? "TIMEOUT" : "NETWORK",
    );
  } finally {
    window.clearTimeout(timeout);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new ApiError(
      detail?.message || defaultErrorMessage(response.status),
      response.status,
      detail?.code || null,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      "LeetRank returned an invalid response. Try again shortly.",
      response.status,
      "invalid_response",
      "RESPONSE",
    );
  }
}

export async function warmBackend(): Promise<void> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    await fetch(`${apiBaseUrl}/health`, { signal: controller.signal });
  } catch {
    // Account requests surface availability errors; warmup is best-effort.
  } finally {
    window.clearTimeout(timeout);
  }
}

export function getCurrentUser(accessToken: string): Promise<CurrentUser> {
  return request("/users/me", accessToken);
}

export function completeOnboarding(
  accessToken: string,
  payload: OnboardingPayload,
): Promise<UserProfile> {
  return request("/users/me/onboarding", accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSettings(
  accessToken: string,
  payload: UserSettingsPayload,
): Promise<UserSettingsResponse> {
  return request("/users/me/settings", accessToken, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getLeaderboard(
  accessToken: string,
  period: LeaderboardPeriod,
): Promise<LeaderboardResponse> {
  return request(`/users/me/leaderboard?period=${period}`, accessToken);
}

export function getFriendRequests(accessToken: string): Promise<FriendRequestsResponse> {
  return request("/users/me/friend-requests", accessToken);
}

export function sendFriendRequest(
  accessToken: string,
  username: string,
): Promise<FriendRequestItem> {
  return request("/users/me/friend-requests", accessToken, {
    method: "POST",
    body: JSON.stringify({ username }),
  });
}

export function searchUsers(
  accessToken: string,
  username: string,
): Promise<UserSearchResponse> {
  return request(
    `/users/me/search?username=${encodeURIComponent(username)}`,
    accessToken,
  );
}

export function acceptFriendRequest(
  accessToken: string,
  requestId: string,
): Promise<PublicUserSummary> {
  return request(`/users/me/friend-requests/${requestId}/accept`, accessToken, {
    method: "POST",
  });
}

export function deleteFriendRequest(
  accessToken: string,
  requestId: string,
): Promise<void> {
  return request(`/users/me/friend-requests/${requestId}`, accessToken, {
    method: "DELETE",
  });
}

export function getFriends(accessToken: string): Promise<FriendsResponse> {
  return request("/users/me/friends", accessToken);
}

export function getFriendsOverview(accessToken: string): Promise<FriendsOverviewResponse> {
  return request("/users/me/friends/overview", accessToken);
}

export function getFriendProfile(
  accessToken: string,
  friendId: string,
): Promise<FriendProfileResponse> {
  return request(`/users/me/friends/${friendId}/profile`, accessToken);
}

export function removeFriend(accessToken: string, friendId: string): Promise<void> {
  return request(`/users/me/friends/${friendId}`, accessToken, { method: "DELETE" });
}

export function getScores(accessToken: string): Promise<ScoresResponse> {
  return request("/users/me/scores", accessToken);
}

export function getActivity(accessToken: string, limit = 10): Promise<ActivityResponse> {
  return request(`/users/me/activity?limit=${limit}`, accessToken);
}
