/**
 * useDoctrineTree — thin adapter over `panels.doctrineTree` (Epoch 3 Wave 6
 * Phase 0, the Doctrine Tree takeover). Same mount/fetch idiom as
 * `useOrgNetwork`/`useWire`/`useContradiction`: mounting marks the panel
 * eligible for the cockpit's single tick-fan-out (`worldSlice.onTickAdvanced`)
 * and this hook fires the first fetch itself so the takeover has data before
 * the next tick lands. Unmounting (takeover close) drops it from the
 * fan-out again.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { EMPTY_DOCTRINE_TREE, type DoctrineTreePayload } from "@/types/game";

interface UseDoctrineTreeResult {
  data: DoctrineTreePayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useDoctrineTree(gameId: string | null): UseDoctrineTreeResult {
  const panel = useStore((s) => s.panels.doctrineTree);
  const setMounted = useStore((s) => s.panels.doctrineTree.setMounted);
  const fetchDoctrineTree = useStore((s) => s.panels.doctrineTree.fetch);

  useEffect(() => {
    if (!gameId) return;
    setMounted(true);
    void fetchDoctrineTree(gameId);
    return () => setMounted(false);
  }, [gameId, setMounted, fetchDoctrineTree]);

  return {
    data: panel.data ?? EMPTY_DOCTRINE_TREE,
    loading: panel.loading,
    error: panel.error,
    refresh: () => (gameId ? fetchDoctrineTree(gameId) : Promise.resolve()),
  };
}
