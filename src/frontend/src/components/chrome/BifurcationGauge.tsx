/**
 * BifurcationGauge — the "George Jackson dial" v1 HUD widget (Wave 3 Round
 * 2a, `reports/wave3-weather-implementation-map.md` Round 2's "Bifurcation
 * gauge v1"). A compact −1…+1 axis (revolution left, fascism right) with one
 * needle per independently-honest data source:
 *
 * - **Territory aggregate**, labeled "solidarity density" — deliberately
 *   NOT the Π₀ topological invariant. `bifurcation_tendency()` (β₀/β₁,
 *   `bifurcation/analysis.py`) computes that, but its only caller
 *   (`BifurcationMonitor`) is never instantiated in production (dormant
 *   math). The LIVE signal is `crisis/bifurcation.py`'s per-county
 *   density-based score, sign convention −1 revolutionary / +1 fascist,
 *   serialized on every `/state/` snapshot territory row as
 *   `bifurcation_score` (`_territory_graph_attr(..., "tick_bifurcation_score")`,
 *   `web/game/engine_bridge.py::_serialize_territory`) — a field this
 *   codebase's `TerritoryState` interface never declared until this widget's
 *   R2a pass. Population-weighted mean across territories carrying a real
 *   (non-null) score (falls back to a plain mean if no territory carries a
 *   usable population weight — never happens on real `/state/` data since
 *   `population` is a required field, but keeps the aggregate honest if it
 *   ever did).
 * - **Class fascist-alignment aggregate** — plain mean of the new
 *   `GET /field_state/` endpoint's per-node `fascist_alignment`
 *   (`FascistFactionSystem`, `reactionary.py`). No population weight is
 *   carried on a `FieldStateNode` row. One-shot fetch on mount
 *   (`EconomyDashboard.tsx`'s `useCrisisTimeline` idiom — no new fetch-layer
 *   abstraction).
 *
 * Each source degrades independently and honestly (Constitution III.11):
 * `fascist_alignment` may legitimately be present while territories carry no
 * `bifurcation_score` yet this session (or vice versa) — neither source's
 * absence blocks the other's needle or line.
 *
 * Mounted via `FloatingPanel` (anchor="free") in `AppShell`'s existing
 * right-column chrome stack, alongside `EventTray`/`ObjectivesTray` — the
 * literal "AppShell chrome line" append point this brief names, not a new
 * screen position. No keyboard hotkey (matches every other `ui.chrome.*Open`
 * toggle; `useSpeedShortcut`'s number keys are an unrelated concern).
 *
 * Deliberately does NOT route through `StatChip`'s `metric`/`scope` probe
 * wiring (`METRIC_PROVENANCE`-keyed inspector push): both numbers here are
 * FRONTEND-computed aggregates over multiple rows, not a single backend
 * `explain`-able scalar, so a probe affordance would imply provenance this
 * widget doesn't have.
 */

import { useEffect, useState } from "react";
import { get as apiGet } from "@/api/client";
import { endpoints } from "@/api/endpoints";
import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import type { FieldStateNode, FieldStatePayload, TerritoryState } from "@/types/game";

interface BifurcationGaugeProps {
  gameId: string;
}

type FieldStateFetchState =
  { status: "loading" } | { status: "ok"; nodes: FieldStateNode[] } | { status: "error" };

/**
 * One-shot fetch of `/field_state/` on mount for its `nodes` array —
 * mirrors `EconomyDashboard.tsx`'s `useCrisisTimeline` idiom exactly: the
 * initial `"loading"` state is the `useState` default (not set synchronously
 * in the effect), and `apiGet` never throws (errors normalize into its
 * returned envelope), so no unhandled-rejection guard is needed on the bare
 * `.then()`.
 */
function useFieldStateOnce(gameId: string): FieldStateFetchState {
  const [state, setState] = useState<FieldStateFetchState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    apiGet<FieldStatePayload>(endpoints.fieldState.path({ id: gameId })).then((res) => {
      if (cancelled) return;
      if (res.status !== "ok") {
        setState({ status: "error" });
        return;
      }
      setState({ status: "ok", nodes: res.data.nodes });
    });
    return () => {
      cancelled = true;
    };
  }, [gameId]);

  return state;
}

/**
 * Population-weighted mean of `TerritoryState.bifurcation_score` across
 * territories carrying a real (finite) score. Falls back to a plain mean
 * when the scored rows carry no usable (positive) population weight. `null`
 * when no territory carries a score at all (Constitution III.11 — never a
 * fabricated 0).
 */
export function aggregateBifurcationScore(territories: TerritoryState[]): number | null {
  const rows = territories
    .map((t) => ({ score: t.bifurcation_score, population: t.population }))
    .filter(
      (r): r is { score: number; population: number } =>
        typeof r.score === "number" && Number.isFinite(r.score),
    );
  if (rows.length === 0) return null;

  const totalPopulation = rows.reduce((sum, r) => sum + Math.max(0, r.population), 0);
  if (totalPopulation > 0) {
    const weighted = rows.reduce((sum, r) => sum + r.score * Math.max(0, r.population), 0);
    return weighted / totalPopulation;
  }
  return rows.reduce((sum, r) => sum + r.score, 0) / rows.length;
}

/**
 * Plain mean of `field_state` nodes' `fascist_alignment` — no population
 * weight is carried on a `FieldStateNode` row. `null` when no node carries
 * the field (the common case pre-R1b, see `FieldStatePayload`'s docstring).
 */
export function aggregateFascistAlignment(nodes: FieldStateNode[]): number | null {
  const values = nodes
    .map((n) => n.fascist_alignment)
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (values.length === 0) return null;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

const AXIS_W = 176;
const AXIS_PAD = 12;
const AXIS_Y = 24;

/** Map a [-1, 1] value onto the axis's pixel x-range, clamped. */
function needleX(value: number): number {
  const clamped = Math.max(-1, Math.min(1, value));
  return AXIS_PAD + ((clamped + 1) / 2) * (AXIS_W - 2 * AXIS_PAD);
}

/** Isoceles-triangle point string centered on (cx, cy) — the fascist-alignment needle glyph. */
function trianglePoints(cx: number, cy: number): string {
  return `${cx},${cy - 5} ${cx - 5},${cy + 5} ${cx + 5},${cy + 5}`;
}

/** Copy for the class fascist-alignment line — one honest state per fetch phase. */
function fascistLineText(fieldState: FieldStateFetchState, fascistScore: number | null): string {
  if (fieldState.status === "loading") return "Class fascist alignment: loading…";
  if (fascistScore === null) return "Class fascist alignment: no data yet.";
  return `Class fascist alignment: ${fascistScore.toFixed(2)}`;
}

function BifurcationAxis({
  territoryScore,
  fascistScore,
}: {
  territoryScore: number | null;
  fascistScore: number | null;
}): React.JSX.Element {
  return (
    <svg
      width={AXIS_W}
      height={40}
      className="block"
      data-testid="bifurcation-axis"
      role="img"
      aria-label="Bifurcation axis: revolution (left, -1) to fascism (right, +1)"
    >
      <line
        x1={AXIS_PAD}
        y1={AXIS_Y}
        x2={AXIS_W - AXIS_PAD}
        y2={AXIS_Y}
        stroke="var(--babylon-shroud)"
        strokeWidth="1"
      />
      <line
        x1={AXIS_W / 2}
        y1={AXIS_Y - 4}
        x2={AXIS_W / 2}
        y2={AXIS_Y + 4}
        stroke="var(--babylon-shroud)"
        strokeWidth="1"
      />
      <text x={AXIS_PAD - 2} y={9} className="text-[8px]" fill="var(--babylon-laser)">
        REV
      </text>
      <text x={AXIS_W - AXIS_PAD - 21} y={9} className="text-[8px]" fill="var(--babylon-rupture)">
        FASC
      </text>
      {territoryScore !== null && (
        <circle
          data-testid="bifurcation-needle-territory"
          cx={needleX(territoryScore)}
          cy={AXIS_Y}
          r={4}
          fill="var(--babylon-solidarity)"
        />
      )}
      {fascistScore !== null && (
        <polygon
          data-testid="bifurcation-needle-fascist"
          points={trianglePoints(needleX(fascistScore), AXIS_Y)}
          fill="var(--babylon-rupture)"
        />
      )}
    </svg>
  );
}

export function BifurcationGauge({ gameId }: BifurcationGaugeProps): React.JSX.Element {
  const bifurcationOpen = useStore((s) => s.ui.chrome.bifurcationOpen);
  const toggleBifurcation = useStore((s) => s.ui.toggleBifurcation);
  // `?? []` stays OUTSIDE the selector (Outliner.tsx's pattern) — a fallback
  // literal INSIDE a zustand selector returns a new array reference every
  // call, which trips useSyncExternalStore's "getSnapshot should be cached"
  // infinite-loop guard once `world.snapshot` is null.
  const snapshot = useStore((s) => s.world.snapshot);
  const territories = snapshot?.territories ?? [];
  const fieldState = useFieldStateOnce(gameId);

  const territoryScore = aggregateBifurcationScore(territories);
  const fascistScore =
    fieldState.status === "ok" ? aggregateFascistAlignment(fieldState.nodes) : null;

  return (
    <FloatingPanel
      anchor="free"
      title="Bifurcation"
      collapsed={!bifurcationOpen}
      onToggle={toggleBifurcation}
      testId="bifurcation-gauge"
    >
      <div className="flex flex-col gap-1 p-2">
        {(territoryScore !== null || fascistScore !== null) && (
          <BifurcationAxis territoryScore={territoryScore} fascistScore={fascistScore} />
        )}
        <p className="text-[9px] text-ksbc-muted-2" data-testid="bifurcation-territory-line">
          {territoryScore === null
            ? "Solidarity density: no data yet."
            : `Solidarity density: ${territoryScore.toFixed(2)}`}
        </p>
        {fieldState.status === "error" ? (
          <p role="alert" className="text-[9px] text-laser" data-testid="bifurcation-fascist-error">
            Field data unavailable.
          </p>
        ) : (
          <p className="text-[9px] text-ksbc-muted-2" data-testid="bifurcation-fascist-line">
            {fascistLineText(fieldState, fascistScore)}
          </p>
        )}
      </div>
    </FloatingPanel>
  );
}
