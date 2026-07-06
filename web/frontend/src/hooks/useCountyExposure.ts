/**
 * Spec 103 FR-103-08: useCountyExposure hook.
 *
 * Polls GET /api/games/<id>/exposure/?county_fips=<fips> — the import-exposure
 * provenance breakdown for Territory Detail. Follows the same fetch/poll
 * shape as `useEconomy`.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse, ExposurePayload } from "@/types/trade";
import { EMPTY_EXPOSURE } from "@/types/trade";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

interface UseCountyExposureResult {
  data: ExposurePayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useCountyExposure(
  gameId: string | null,
  countyFips: string | null,
): UseCountyExposureResult {
  const [data, setData] = useState<ExposurePayload>(EMPTY_EXPOSURE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId || !countyFips) return;
    setLoading(true);
    try {
      const response = await fetch(
        `/api/games/${gameId}/exposure/?county_fips=${encodeURIComponent(countyFips)}`,
        { credentials: "include" },
      );
      const body = (await response.json()) as ApiResponse<ExposurePayload>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? EMPTY_EXPOSURE);
        setError(null);
      } else {
        setError(body.message ?? `HTTP ${response.status}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "fetch failed");
    } finally {
      setLoading(false);
    }
  }, [gameId, countyFips]);

  useEffect(() => {
    if (!gameId || !countyFips) {
      setData(EMPTY_EXPOSURE);
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
  }, [gameId, countyFips, doFetch]);

  return { data, loading, error, refresh: doFetch };
}
