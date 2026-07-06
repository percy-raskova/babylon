/**
 * Spec 103 FR-103-07: useTradeFlows hook.
 *
 * Polls GET /api/games/<id>/trade-flows/ — per-bloc price/flow lines for
 * the Wire INDEX tab. Follows the same fetch/poll shape as `useEconomy`.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse, TradeFlowsPayload } from "@/types/trade";
import { EMPTY_TRADE_FLOWS } from "@/types/trade";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

interface UseTradeFlowsResult {
  data: TradeFlowsPayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useTradeFlows(gameId: string | null): UseTradeFlowsResult {
  const [data, setData] = useState<TradeFlowsPayload>(EMPTY_TRADE_FLOWS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/trade-flows/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<TradeFlowsPayload>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? EMPTY_TRADE_FLOWS);
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
      setData(EMPTY_TRADE_FLOWS);
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
