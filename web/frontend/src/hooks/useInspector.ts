/**
 * Spec 061 T100 / FR-019: useInspector hook.
 *
 * Generic inspector fetcher that dispatches to the correct endpoint
 * based on the requested target type. Returns the populated detail
 * payload (or null while loading / on error).
 *
 * Backend implementations of inspect_* are stubs that return the
 * matching snapshot entry; deeper detail (recent_actions, history)
 * will populate as the US6-followup persistence queries land.
 */

import { useCallback, useEffect, useState } from "react";
import type { ApiResponse } from "@/types/game";

export type InspectorType = "node" | "org" | "community" | "edge" | "hex";

interface UseInspectorResult {
  data: Record<string, unknown> | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useInspector(
  gameId: string | null,
  type: InspectorType | null,
  id: string | null,
): UseInspectorResult {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doFetch = useCallback(async (): Promise<void> => {
    if (!gameId || !type || !id) {
      setData(null);
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`/api/games/${gameId}/${type}/${id}/`, {
        credentials: "include",
      });
      const body = (await response.json()) as ApiResponse<Record<string, unknown>>;
      if (response.ok && body.status === "ok") {
        setData(body.data ?? null);
        setError(null);
      } else {
        setError(body.message ?? `HTTP ${response.status}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "fetch failed");
    } finally {
      setLoading(false);
    }
  }, [gameId, type, id]);

  useEffect(() => {
    void doFetch();
  }, [doFetch]);

  return { data, loading, error, refresh: doFetch };
}
