/**
 * SurvivalDuelPanel — the async-fetched half of the class InspectionCard's
 * "Survival Calculus" section (Wave 2 W2.5a,
 * `reports/wave2-implementation-map.md` owner ruling 3): the two-series
 * `DuelSparkline` fed by the real `GET /node/:id/history/` class-snapshot
 * history (never client-side accumulation), plus rupture markers from the
 * SAME response's server-filtered `ruptures` list (`UPRISING` events whose
 * `data.trigger === "revolutionary_pressure"` for this node — the only
 * honest P(S|R) > P(S|A) crossing signal; `query_node_uprising_events` is
 * uncapped, unlike `/journal/`'s shared 200-event window). The predicate is
 * re-applied client-side as defense-in-depth. The raw crossing is not
 * evented for non-struggling classes and must never be fabricated here
 * (owner ruling 3).
 *
 * The current-tick P(S|A)/P(S|R) *values* are plain synchronous
 * `InspectionRow`s in `lib/inspect/adapters/node.ts`'s "Survival Calculus"
 * section — `FormulaCard` already renders those from the resolved node
 * payload. This panel owns only the historical chart, which needs its own
 * fetch the pure/synchronous adapter pipeline (`resolveRef`) cannot make.
 * Mirrors `EconomyDashboard.tsx`'s `useCrisisTimeline` self-fetch idiom
 * exactly (one-shot `apiGet` on mount) — no new data-fetch layer.
 */

import { useEffect, useState } from "react";
import { get as apiGet } from "@/api/client";
import { endpoints } from "@/api/endpoints";
import { DuelSparkline } from "@/components/bbl/DuelSparkline";
import type { ClassHistoryPayload, ClassHistoryPoint, RuptureMarker } from "@/types/game";

interface SurvivalDuelPanelProps {
  gameId: string;
  classId: string;
}

type HistoryFetchState =
  | { status: "loading" }
  | { status: "ok"; points: ClassHistoryPoint[]; markers: RuptureMarker[] }
  | { status: "error" };

/** One-shot fetch of this class's real per-tick survival-calculus history
 * AND its rupture markers — both ride the single history response. The
 * initial `"loading"` state is the `useState` default, not set
 * synchronously inside the effect (`EconomyDashboard.tsx`'s
 * `useCrisisTimeline` idiom) — the effect's only job is to call `setState`
 * from the async `.then()` callback once the response lands. `apiGet` never
 * throws (errors are normalized into its returned envelope), so no
 * unhandled-rejection guard is needed on the bare `.then()`.
 *
 * Markers keep the owner-ruling-3 predicate client-side as
 * defense-in-depth over the server's own `query_node_uprising_events`
 * filtering (same predicate, two layers — redundant verification). */
function useClassHistory(gameId: string, classId: string): HistoryFetchState {
  const [state, setState] = useState<HistoryFetchState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    apiGet<ClassHistoryPayload>(
      endpoints.inspectorNodeHistory.path({ id: gameId, entityId: classId }),
    ).then((res) => {
      if (cancelled) return;
      if (res.status !== "ok") {
        setState({ status: "error" });
        return;
      }
      const markers = (res.data.ruptures ?? [])
        .filter(
          (e) =>
            e.type === "uprising" &&
            e.data.trigger === "revolutionary_pressure" &&
            e.data.node_id === classId,
        )
        .map((e) => ({ tick: e.tick, eventId: e.id }));
      setState({ status: "ok", points: res.data.history, markers });
    });
    return () => {
      cancelled = true;
    };
  }, [gameId, classId]);

  return state;
}

export function SurvivalDuelPanel({ gameId, classId }: SurvivalDuelPanelProps): React.JSX.Element {
  const history = useClassHistory(gameId, classId);

  if (history.status === "loading") {
    return (
      <p className="text-[11px] italic text-shroud" data-testid="survival-duel-loading">
        Loading survival duel history…
      </p>
    );
  }
  if (history.status === "error") {
    return (
      <p role="alert" className="text-[11px] text-laser" data-testid="survival-duel-error">
        Survival duel history unavailable.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-0.5" data-testid="survival-duel-panel">
      <span className="text-[9px] uppercase tracking-widest text-ash">Survival Duel</span>
      <DuelSparkline points={history.points} markers={history.markers} />
    </div>
  );
}
