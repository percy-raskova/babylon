/**
 * Spec 095: useContradiction hook.
 *
 * Wraps GET /api/games/<id>/contradiction/ with React state and a 2s polling
 * interval (FR-095-07). Backs the Dialectic screen — the live contradiction
 * layer visualization. Constitution III: pure read, never writes engine state.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse } from "@/types/game";
import { EMPTY_CONTRADICTION, type ContradictionSnapshot } from "@/types/dialectic";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

interface UseContradictionResult {
  data: ContradictionSnapshot;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useContradiction(gameId: string | null): UseContradictionResult {
  const [data, setData] = useState<ContradictionSnapshot>(EMPTY_CONTRADICTION);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/contradiction/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<ContradictionSnapshot>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? EMPTY_CONTRADICTION);
        setError(null);
      } else {
        setError(body.message ?? `HTTP ${response.status}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "fetch failed");
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  useEffect(() => {
    if (!gameId) {
      setData(EMPTY_CONTRADICTION);
      return;
    }
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

  return { data, loading, error, refresh: doFetch };
}
