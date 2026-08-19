import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { ApiError, getFriendsOverview } from "../lib/api";
import type { FriendsOverviewResponse } from "../types/api";

const CACHE_TTL_MS = 60_000;

interface RefreshOptions {
  force?: boolean;
}

interface FriendsDataValue {
  overview: FriendsOverviewResponse | null;
  initialLoading: boolean;
  refreshing: boolean;
  error: string | null;
  loadedAt: number | null;
  refresh: (options?: RefreshOptions) => Promise<void>;
}

const FriendsDataContext = createContext<FriendsDataValue | null>(null);

export function FriendsDataProvider({
  accessToken,
  children,
}: {
  accessToken: string;
  children: ReactNode;
}) {
  const [overview, setOverview] = useState<FriendsOverviewResponse | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadedAt, setLoadedAt] = useState<number | null>(null);
  const overviewRef = useRef<FriendsOverviewResponse | null>(null);
  const loadedAtRef = useRef<number | null>(null);
  const inFlightRef = useRef<Promise<void> | null>(null);

  const refresh = useCallback(
    async ({ force = false }: RefreshOptions = {}) => {
      const lastLoadedAt = loadedAtRef.current;
      if (!force && lastLoadedAt && Date.now() - lastLoadedAt < CACHE_TTL_MS) return;
      if (inFlightRef.current) {
        await inFlightRef.current;
        if (!force) return;
        if (inFlightRef.current) return inFlightRef.current;
      }

      if (overviewRef.current) {
        setRefreshing(true);
      } else {
        setInitialLoading(true);
      }
      setError(null);

      const request = getFriendsOverview(accessToken)
        .then((nextOverview) => {
          const now = Date.now();
          overviewRef.current = nextOverview;
          loadedAtRef.current = now;
          setOverview(nextOverview);
          setLoadedAt(now);
        })
        .catch((caughtError) => {
          setError(
            caughtError instanceof ApiError
              ? caughtError.message
              : "Could not refresh your friends.",
          );
        })
        .finally(() => {
          setInitialLoading(false);
          setRefreshing(false);
          inFlightRef.current = null;
        });

      inFlightRef.current = request;
      return request;
    },
    [accessToken],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <FriendsDataContext.Provider
      value={{ overview, initialLoading, refreshing, error, loadedAt, refresh }}
    >
      {children}
    </FriendsDataContext.Provider>
  );
}

export function useFriendsData(): FriendsDataValue {
  const context = useContext(FriendsDataContext);
  if (!context) {
    throw new Error("useFriendsData must be used inside FriendsDataProvider.");
  }
  return context;
}
