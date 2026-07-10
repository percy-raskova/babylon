/**
 * useEndgame — thin adapter over `panels.endgame` (spec-110 B5).
 *
 * Backs `EndStateScreen` (the Chronicle takeover). Same shape as the ported
 * component expects; see `useWire`'s docstring for the mount/fetch pattern
 * this and the other takeover hooks share.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { EMPTY_ENDGAME, type EndgameState } from "@/types/dialectic";

interface UseEndgameResult {
  data: EndgameState;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useEndgame(gameId: string | null): UseEndgameResult {
  const panel = useStore((s) => s.panels.endgame);
  const setMounted = useStore((s) => s.panels.endgame.setMounted);
  const fetchEndgame = useStore((s) => s.panels.endgame.fetch);

  useEffect(() => {
    if (!gameId) return;
    setMounted(true);
    void fetchEndgame(gameId);
    return () => setMounted(false);
  }, [gameId, setMounted, fetchEndgame]);

  return {
    data: panel.data ?? EMPTY_ENDGAME,
    loading: panel.loading,
    error: panel.error,
    refresh: () => (gameId ? fetchEndgame(gameId) : Promise.resolve()),
  };
}
