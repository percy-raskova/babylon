/**
 * Spec 103 FR-103-09: useTradePanel hook.
 *
 * Polls GET /api/games/<id>/trade-panel/ — the aggregate trade panel for
 * the Analysis page. Follows the same fetch/poll shape as `useEconomy`.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse, TradePanelPayload } from "@/types/trade";
import { EMPTY_TRADE_PANEL } from "@/types/trade";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

interface UseTradePanelResult {
  data: TradePanelPayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useTradePanel(gameId: string | null): UseTradePanelResult {
  const [data, setData] = useState<TradePanelPayload>(EMPTY_TRADE_PANEL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/trade-panel/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<TradePanelPayload>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? EMPTY_TRADE_PANEL);
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
      setData(EMPTY_TRADE_PANEL);
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
