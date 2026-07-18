/**
 * Per-org verb eligibility for the VerbGrid (spec-116 FR-4.8) — one
 * fetch per (game, org, tick), mirroring `useVerbTargets`'s
 * cancel-on-unmount pattern; the tick dependency re-fetches after every
 * resolved tick so the grid tracks the moving world.
 *
 * HONEST-NULL: while the fetch is unresolved or failed the map is null
 * and every verb renders enabled exactly as before — a fabricated
 * disabled state would be a phantom (Constitution III.11).
 */

import { useEffect, useState } from "react";
import { fetchVerbEligibility } from "@/lib/verbs";
import type { VerbEligibilityEntry } from "@/types/game";

export type VerbEligibilityMap = Record<string, VerbEligibilityEntry>;

export function useVerbEligibility(
  gameId: string,
  orgId: string,
  tick: number | null,
): VerbEligibilityMap | null {
  const [map, setMap] = useState<VerbEligibilityMap | null>(null);

  useEffect(() => {
    if (!orgId) {
      return;
    }
    let cancelled = false;
    // fetchVerbEligibility never throws (normalized result object).
    fetchVerbEligibility(gameId, orgId).then((res) => {
      if (cancelled) return;
      if (!res.ok || res.data === null) {
        setMap(null);
        return;
      }
      const next: VerbEligibilityMap = {};
      for (const entry of res.data.verbs) {
        next[entry.verb] = entry;
      }
      setMap(next);
    });
    return () => {
      cancelled = true;
    };
  }, [gameId, orgId, tick]);

  // Honest-null regardless of stale internal state once orgId is absent —
  // avoids a synchronous setState-in-effect for the "no acting org" case.
  return orgId ? map : null;
}
