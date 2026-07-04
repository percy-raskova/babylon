/**
 * Spec 093 US5: useEconomy hook.
 *
 * Wraps GET /api/games/<id>/economy/?territory_id=<tid> — the real
 * per-territory economic summary powering Territory Detail's economic
 * panel. Follows the same fetch/poll shape as `useTimeseries` /
 * `useJournal` (no shared client helper — matches sibling precedent).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse, EconomyPayload } from "@/types/game";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

const _EMPTY: EconomyPayload = {
  territory_id: null,
  has_data: false,
  value_produced: 0,
  wage_share: null,
  rent_extracted: 0,
  exploitation_rate: null,
  extraction_intensity: 0,
};

interface UseEconomyResult {
  data: EconomyPayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useEconomy(gameId: string | null, territoryId: string | null): UseEconomyResult {
  const [data, setData] = useState<EconomyPayload>(_EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId || !territoryId) return;
    setLoading(true);
    try {
      const response = await fetch(
        `/api/games/${gameId}/economy/?territory_id=${encodeURIComponent(territoryId)}`,
        { credentials: "include" },
      );
      const body = (await response.json()) as ApiResponse<EconomyPayload>;
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
  }, [gameId, territoryId]);

  useEffect(() => {
    if (!gameId || !territoryId) {
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
  }, [gameId, territoryId, doFetch]);

  return { data, loading, error, refresh: doFetch };
}
