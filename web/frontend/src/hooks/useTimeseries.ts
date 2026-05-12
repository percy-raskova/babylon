/**
 * Spec 061 T053 / FR-026: useTimeseries hook.
 *
 * Wraps GET /api/games/<id>/timeseries/ with React state and a polling
 * interval matched to useGameState's POLL_INTERVAL_MS (FR-028).
 * The component re-renders when the tick advances; missing values in
 * the response arrays surface as null so callers can interpolate or
 * hide gaps without an extra request.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse } from "@/types/game";
import type { TimeseriesPayload } from "@/types/timeseries";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

const _EMPTY: TimeseriesPayload = {
  ticks: [],
  imperial_rent: [],
  consciousness: [],
  solidarity: [],
  heat: [],
  wealth: [],
  biocapacity: [],
};

interface UseTimeseriesResult {
  data: TimeseriesPayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useTimeseries(gameId: string | null): UseTimeseriesResult {
  const [data, setData] = useState<TimeseriesPayload>(_EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/timeseries/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<TimeseriesPayload>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? _EMPTY);
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
      setData(_EMPTY);
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
