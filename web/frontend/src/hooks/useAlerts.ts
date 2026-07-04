/**
 * Spec 092: useAlerts hook.
 *
 * Wraps GET /api/games/<id>/alerts/ with React state. Backs the Tick
 * Resolution screen's "state response" section — critical/warning events
 * from the tick that was just resolved.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse, AlertsPayload } from "@/types/game";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

const _EMPTY: AlertsPayload = { alerts: [] };

interface UseAlertsResult {
  data: AlertsPayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useAlerts(gameId: string | null): UseAlertsResult {
  const [data, setData] = useState<AlertsPayload>(_EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/alerts/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<AlertsPayload>;
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
