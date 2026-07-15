/**
 * useOrgNetwork — thin adapter over `panels.network` (AW4-R2, spec-110 B5
 * takeover-panel pattern). Same mount/fetch idiom as `useWire`/
 * `useContradiction`: mounting marks the panel eligible for the cockpit's
 * single tick-fan-out (`worldSlice.onTickAdvanced`) and this hook fires the
 * first fetch itself so the Network takeover has data before the next tick
 * lands. Unmounting (takeover close) drops it from the fan-out again.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { EMPTY_ORG_NETWORK, type OrgNetworkPayload } from "@/types/game";

interface UseOrgNetworkResult {
  data: OrgNetworkPayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useOrgNetwork(gameId: string | null): UseOrgNetworkResult {
  const panel = useStore((s) => s.panels.network);
  const setMounted = useStore((s) => s.panels.network.setMounted);
  const fetchNetwork = useStore((s) => s.panels.network.fetch);

  useEffect(() => {
    if (!gameId) return;
    setMounted(true);
    void fetchNetwork(gameId);
    return () => setMounted(false);
  }, [gameId, setMounted, fetchNetwork]);

  return {
    data: panel.data ?? EMPTY_ORG_NETWORK,
    loading: panel.loading,
    error: panel.error,
    refresh: () => (gameId ? fetchNetwork(gameId) : Promise.resolve()),
  };
}
