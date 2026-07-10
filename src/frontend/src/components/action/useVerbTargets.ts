/**
 * Live eligible targets for a verb — component-local port of the legacy
 * `VerbPage.tsx`'s `useVerbTargets` hook, minus its zustand cache (the B3
 * cockpit has no `verbTargets` store slice; `VerbForm` is keyed by
 * `${orgId}:${verb}` so a per-mount fetch is always fresh).
 *
 * Endpoint-sourced verbs (`targetsSource` unset or `"endpoint"`) call the
 * live `fetchVerbTargets`; `campaign` (`targetsSource: "snapshot"`, its
 * GET route 405s) derives targets from the snapshot's territories +
 * hyperedges instead — a pure `useMemo` derivation, not fetched state, so
 * there is no effect to synchronize for that path at all.
 *
 * The initial `loading` flag is computed lazily in `useState`'s
 * initializer (true iff this mount will actually fetch), not set
 * synchronously inside the effect — the effect's only job is to call
 * `setFetched` from the async `.then()` callback once the response lands.
 * This relies on the caller remounting on `verb`/`orgId` change (`VerbForm`
 * is keyed by `${orgId}:${verb}`) rather than this hook re-deriving
 * `loading` on every dependency change in place.
 */

import { useEffect, useMemo, useState } from "react";
import { fetchVerbTargets } from "@/lib/verbs";
import type { VerbConfig, VerbTarget } from "@/lib/verbs";
import type { GameSnapshot, PlayerVerb } from "@/types/game";

function snapshotTargets(snapshot: GameSnapshot | null): VerbTarget[] {
  return [
    ...(snapshot?.territories ?? []).map((t) => ({
      id: t.id,
      label: t.name,
      group: "Territories",
    })),
    ...(snapshot?.hyperedges ?? []).map((h) => ({
      id: h.id,
      label: h.label,
      group: "Communities",
    })),
  ];
}

export interface UseVerbTargetsResult {
  targets: VerbTarget[];
  loading: boolean;
  error: string | null;
}

const IDLE: UseVerbTargetsResult = { targets: [], loading: false, error: null };

export function useVerbTargets(
  gameId: string,
  verb: PlayerVerb,
  config: VerbConfig,
  orgId: string,
  snapshot: GameSnapshot | null,
): UseVerbTargetsResult {
  const isSnapshotSourced = (config.targetsSource ?? "endpoint") === "snapshot";
  const snapshotResult = useMemo<VerbTarget[]>(
    () => (isSnapshotSourced ? snapshotTargets(snapshot) : []),
    [isSnapshotSourced, snapshot],
  );

  const [fetched, setFetched] = useState<UseVerbTargetsResult>(() =>
    !isSnapshotSourced && orgId ? { targets: [], loading: true, error: null } : IDLE,
  );

  useEffect(() => {
    if (isSnapshotSourced || !orgId) {
      return;
    }
    let cancelled = false;
    // fetchVerbTargets never throws (it normalizes network/API errors into
    // its result object), so no unhandled-rejection guard is needed here.
    fetchVerbTargets(gameId, verb, orgId).then((res) => {
      if (cancelled) return;
      setFetched(
        res.ok
          ? { targets: config.parseTargets(res.payload), loading: false, error: null }
          : { targets: [], loading: false, error: res.message ?? "Failed to fetch action targets" },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [gameId, verb, config, orgId, isSnapshotSourced]);

  if (isSnapshotSourced) {
    return { targets: snapshotResult, loading: false, error: null };
  }
  return fetched;
}
