/**
 * Hook for managing game state polling and mutations.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { get, post } from "@/api/client";
import type {
  GameSnapshot,
  SubmitActionParams,
  AvailableAction,
  ActionResultData,
} from "@/types/game";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

interface UseGameStateResult {
  snapshot: GameSnapshot | null;
  available: AvailableAction[];
  loading: boolean;
  error: string | null;
  submitAction: (params: SubmitActionParams) => Promise<void>;
  resolveTick: () => Promise<ActionResultData[] | null>;
  refresh: () => Promise<void>;
}

export function useGameState(gameId: string | null): UseGameStateResult {
  const [snapshot, setSnapshot] = useState<GameSnapshot | null>(null);
  const [available, setAvailable] = useState<AvailableAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const fetchState = useCallback(async () => {
    if (!gameId) return;
    setLoading(true);
    setError(null);

    const [stateRes, actionsRes] = await Promise.all([
      get<GameSnapshot>(`/api/games/${gameId}/state/`),
      get<AvailableAction[]>(`/api/games/${gameId}/actions/available/`),
    ]);

    if (stateRes.status === "ok") {
      setSnapshot(stateRes.data);
    } else {
      setError(stateRes.message ?? "Failed to load game state");
    }

    if (actionsRes.status === "ok") {
      setAvailable(actionsRes.data);
    }

    setLoading(false);
  }, [gameId]);

  // Poll for state updates
  useEffect(() => {
    if (!gameId) return;
    pollCount.current = 0;

    void fetchState();
    const interval = setInterval(() => {
      if (pollCount.current >= MAX_POLL_COUNT) {
        clearInterval(interval);
        return;
      }
      pollCount.current += 1;
      void fetchState();
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [gameId, fetchState]);

  const submitAction = useCallback(
    async (params: SubmitActionParams) => {
      if (!gameId) return;
      const res = await post(`/api/games/${gameId}/actions/`, params);
      if (res.status !== "ok") {
        setError(res.message ?? "Failed to submit action");
      }
      await fetchState();
    },
    [gameId, fetchState],
  );

  const resolveTick = useCallback(async (): Promise<
    ActionResultData[] | null
  > => {
    if (!gameId) return null;
    const res = await post<Record<string, unknown>>(
      `/api/games/${gameId}/resolve/`,
    );
    if (res.status !== "ok") {
      setError(res.message ?? "Failed to resolve tick");
      return null;
    }
    await fetchState();
    // Fetch results for the resolved tick
    const tick = res.tick ?? 0;
    const resultsRes = await get<ActionResultData[]>(
      `/api/games/${gameId}/results/${tick}/`,
    );
    return resultsRes.status === "ok" ? resultsRes.data : null;
  }, [gameId, fetchState]);

  return {
    snapshot,
    available,
    loading,
    error,
    submitAction,
    resolveTick,
    refresh: fetchState,
  };
}
