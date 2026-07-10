/**
 * useTradeFlows — thin adapter over `panels.tradeFlows` (spec-110 B5).
 *
 * Backs `BlocFlowLines` (the Wire takeover's INDEX tab). See `useWire`'s
 * docstring for the mount/fetch pattern this and the other takeover hooks
 * share.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { EMPTY_TRADE_FLOWS, type TradeFlowsPayload } from "@/types/trade";

interface UseTradeFlowsResult {
  data: TradeFlowsPayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useTradeFlows(gameId: string | null): UseTradeFlowsResult {
  const panel = useStore((s) => s.panels.tradeFlows);
  const setMounted = useStore((s) => s.panels.tradeFlows.setMounted);
  const fetchTradeFlows = useStore((s) => s.panels.tradeFlows.fetch);

  useEffect(() => {
    if (!gameId) return;
    setMounted(true);
    void fetchTradeFlows(gameId);
    return () => setMounted(false);
  }, [gameId, setMounted, fetchTradeFlows]);

  return {
    data: panel.data ?? EMPTY_TRADE_FLOWS,
    loading: panel.loading,
    error: panel.error,
    refresh: () => (gameId ? fetchTradeFlows(gameId) : Promise.resolve()),
  };
}
