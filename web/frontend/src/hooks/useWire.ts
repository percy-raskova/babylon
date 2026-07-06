/**
 * Spec 094: useWire hook.
 *
 * Wraps GET /api/games/<id>/wire/ with React state and a polling
 * interval matched to useGameState's POLL_INTERVAL_MS. Backs The Wire
 * 4-tab window — the triptych comparative reading view fed by the
 * DeterministicNarrator.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse } from "@/types/game";
import type { WireFeed } from "@/types/wire";
import { EMPTY_WIRE_FEED } from "@/types/wire";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

interface UseWireResult {
  data: WireFeed;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useWire(gameId: string | null): UseWireResult {
  const [data, setData] = useState<WireFeed>(EMPTY_WIRE_FEED);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/wire/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<WireFeed>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? EMPTY_WIRE_FEED);
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
      setData(EMPTY_WIRE_FEED);
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
