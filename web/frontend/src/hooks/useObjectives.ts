/**
 * Spec 095: useObjectives hook.
 *
 * Wraps GET /api/games/<id>/objectives/ with React state and a 2s polling
 * interval. Backs the ObjectivesPage / ObjectivesTracker — the Vic3-style
 * objectives tracker. Constitution III: pure read.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse } from "@/types/game";
import { EMPTY_OBJECTIVES, type ObjectivesTracker } from "@/types/dialectic";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

interface UseObjectivesResult {
  data: ObjectivesTracker;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useObjectives(gameId: string | null): UseObjectivesResult {
  const [data, setData] = useState<ObjectivesTracker>(EMPTY_OBJECTIVES);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/objectives/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<ObjectivesTracker>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? EMPTY_OBJECTIVES);
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
      setData(EMPTY_OBJECTIVES);
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
