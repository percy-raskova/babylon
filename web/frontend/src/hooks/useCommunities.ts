/**
 * Spec 061 T099 / FR-018: useCommunities hook.
 *
 * Wraps GET /api/games/<id>/communities/ with React state. The
 * endpoint is the bridge's get_communities_dashboard which currently
 * returns an empty array until the US6-followup XGI persistence
 * query lands. The hook degrades gracefully to an empty list and
 * never throws.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse } from "@/types/game";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_COUNT = 1000;

interface CommunitiesPayload {
  communities: unknown[];
}

interface UseCommunitiesResult {
  data: CommunitiesPayload;
  loading: boolean;
  error: string | null;
}

export function useCommunities(gameId: string | null): UseCommunitiesResult {
  const [data, setData] = useState<CommunitiesPayload>({ communities: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/communities/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<CommunitiesPayload>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? { communities: [] });
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
    if (!gameId) return;
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

  return { data, loading, error };
}
