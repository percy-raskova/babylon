/**
 * useObjectives — thin adapter over `panels.objectives` (spec-110 B5).
 *
 * Backs `ObjectivesTracker` (the Right Dock's third tab). See `useWire`'s
 * docstring for the mount/fetch pattern this and the other takeover hooks
 * share.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import {
  EMPTY_OBJECTIVES,
  type ObjectivesTracker as ObjectivesTrackerData,
} from "@/types/dialectic";

interface UseObjectivesResult {
  data: ObjectivesTrackerData;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useObjectives(gameId: string | null): UseObjectivesResult {
  const panel = useStore((s) => s.panels.objectives);
  const setMounted = useStore((s) => s.panels.objectives.setMounted);
  const fetchObjectives = useStore((s) => s.panels.objectives.fetch);

  useEffect(() => {
    if (!gameId) return;
    setMounted(true);
    void fetchObjectives(gameId);
    return () => setMounted(false);
  }, [gameId, setMounted, fetchObjectives]);

  return {
    data: panel.data ?? EMPTY_OBJECTIVES,
    loading: panel.loading,
    error: panel.error,
    refresh: () => (gameId ? fetchObjectives(gameId) : Promise.resolve()),
  };
}
