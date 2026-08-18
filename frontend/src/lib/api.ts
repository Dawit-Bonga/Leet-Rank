import type {
  CurrentUser,
  LeaderboardPeriod,
  LeaderboardResponse,
  OnboardingPayload,
  SyncResponse,
  UserProfile,
} from "../types/api";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  status: number;
  code: string | null;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(
  path: string,
  accessToken: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new ApiError(
      detail?.message || `Request failed with status ${response.status}.`,
      response.status,
      detail?.code || null,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
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

export function getLeaderboard(
  accessToken: string,
  period: LeaderboardPeriod,
): Promise<LeaderboardResponse> {
  return request(`/users/me/leaderboard?period=${period}`, accessToken);
}

export function syncLeetCode(accessToken: string): Promise<SyncResponse> {
  return request("/users/me/sync", accessToken, { method: "POST" });
}
