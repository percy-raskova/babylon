/**
 * useContradiction — thin adapter over `panels.contradiction` (spec-110 B5).
 *
 * Backs `DialecticSpread` (the Dialectic takeover). See `useWire`'s
 * docstring for the mount/fetch pattern this and the other takeover hooks
 * share.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { EMPTY_CONTRADICTION, type ContradictionSnapshot } from "@/types/dialectic";

interface UseContradictionResult {
  data: ContradictionSnapshot;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useContradiction(gameId: string | null): UseContradictionResult {
  const panel = useStore((s) => s.panels.contradiction);
  const setMounted = useStore((s) => s.panels.contradiction.setMounted);
  const fetchContradiction = useStore((s) => s.panels.contradiction.fetch);

  useEffect(() => {
    if (!gameId) return;
    setMounted(true);
    void fetchContradiction(gameId);
    return () => setMounted(false);
  }, [gameId, setMounted, fetchContradiction]);

  return {
    data: panel.data ?? EMPTY_CONTRADICTION,
    loading: panel.loading,
    error: panel.error,
    refresh: () => (gameId ? fetchContradiction(gameId) : Promise.resolve()),
  };
}
