/**
 * useWire — thin adapter over `panels.wire` (spec-110 B5).
 *
 * Same `{data, loading, error, refresh}` surface the ported Wire family
 * (`WireApp` and friends) already consumes, but backed by the cockpit's
 * single fetch orchestrator instead of a self-contained 2s poller: mounting
 * marks the panel eligible for the tick-fan-out in `worldSlice`, and this
 * hook fires the first fetch itself so the takeover has data before the
 * next tick lands.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { EMPTY_WIRE_FEED, type WireFeed } from "@/types/wire";

interface UseWireResult {
  data: WireFeed;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useWire(gameId: string | null): UseWireResult {
  const panel = useStore((s) => s.panels.wire);
  const setMounted = useStore((s) => s.panels.wire.setMounted);
  const fetchWire = useStore((s) => s.panels.wire.fetch);

  useEffect(() => {
    if (!gameId) return;
    setMounted(true);
    void fetchWire(gameId);
    return () => setMounted(false);
  }, [gameId, setMounted, fetchWire]);

  return {
    data: panel.data ?? EMPTY_WIRE_FEED,
    loading: panel.loading,
    error: panel.error,
    refresh: () => (gameId ? fetchWire(gameId) : Promise.resolve()),
  };
}
