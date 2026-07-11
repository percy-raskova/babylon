/**
 * useNarration — thin adapter over `panels.narration` (spec-113 Lane N +
 * orchestrator wiring).
 *
 * Mirrors `useWire`'s contract: mounting marks the panel eligible for the
 * tick fan-out in `worldSlice` and fires the first fetch so the host
 * surface has an answer (usually `status: "offline"` while the backend
 * endpoint is contract-only) before the next tick lands. Beats accumulate
 * in the panel across ticks (deduped by id, ascending by tick).
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import type { NarrationBeat, NarrationState } from "@/types/narration";

interface UseNarrationResult {
  status: NarrationState;
  beats: NarrationBeat[];
  /** Newest beat, or `null` when none have arrived (offline/pending/quiet). */
  latest: NarrationBeat | null;
  loading: boolean;
}

export function useNarration(gameId: string | null): UseNarrationResult {
  const panel = useStore((s) => s.panels.narration);
  const setMounted = useStore((s) => s.panels.narration.setMounted);
  const fetchNarration = useStore((s) => s.panels.narration.fetch);

  useEffect(() => {
    if (!gameId) return;
    setMounted(true);
    void fetchNarration(gameId);
    return () => setMounted(false);
  }, [gameId, setMounted, fetchNarration]);

  return {
    status: panel.status,
    beats: panel.beats,
    latest: panel.beats.at(-1) ?? null,
    loading: panel.loading,
  };
}
