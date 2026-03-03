/**
 * Hook for managing game state polling — delegates to Zustand gameStore.
 */

import { useCallback, useEffect, useRef } from "react";
import { useGameStore } from "@/stores/gameStore";
import type {
  GameSnapshot,
  AvailableAction,
  SubmitActionParams,
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
  const snapshot = useGameStore((s) => s.snapshot);
  const available = useGameStore((s) => s.available);
  const loading = useGameStore((s) => s.loading);
  const error = useGameStore((s) => s.error);
  const fetchState = useGameStore((s) => s.fetchState);
  const storeSubmitAction = useGameStore((s) => s.submitAction);
  const storeResolveTick = useGameStore((s) => s.resolveTick);
  const pollCount = useRef(0);

  const doFetch = useCallback(async () => {
    if (!gameId) return;
    await fetchState(gameId);
  }, [gameId, fetchState]);

  // Poll for state updates
  useEffect(() => {
    if (!gameId) return;
    pollCount.current = 0;

    void doFetch();
    const interval = setInterval(() => {
      if (pollCount.current >= MAX_POLL_COUNT) {
        clearInterval(interval);
        return;
      }
      pollCount.current += 1;
      void doFetch();
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [gameId, doFetch]);

  const submitAction = useCallback(
    async (params: SubmitActionParams) => {
      if (!gameId) return;
      await storeSubmitAction(gameId, params);
    },
    [gameId, storeSubmitAction],
  );

  const resolveTick = useCallback(async (): Promise<ActionResultData[] | null> => {
    if (!gameId) return null;
    return storeResolveTick(gameId);
  }, [gameId, storeResolveTick]);

  return {
    snapshot,
    available,
    loading,
    error,
    submitAction,
    resolveTick,
    refresh: doFetch,
  };
}
