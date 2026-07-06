/**
 * Spec 092: useJournal hook.
 *
 * Wraps GET /api/games/<id>/journal/ with React state and a polling
 * interval matched to useGameState's POLL_INTERVAL_MS. Backs the Event
 * Log page — the full cross-tick classified event history, as opposed to
 * `snapshot.events` (current tick only, per WorldState's per-tick contract).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse, JournalPayload } from "@/types/game";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

const _EMPTY: JournalPayload = { events: [] };

interface UseJournalResult {
  data: JournalPayload;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useJournal(gameId: string | null): UseJournalResult {
  const [data, setData] = useState<JournalPayload>(_EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/journal/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<JournalPayload>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? _EMPTY);
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
      setData(_EMPTY);
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
