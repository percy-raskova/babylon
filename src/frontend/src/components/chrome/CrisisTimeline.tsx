/**
 * CrisisTimeline — the "watchable business cycle" HUD widget. A compact
 * 5-segment strip tracing the crisis lifecycle (NORMAL → ONSET → EARLY →
 * DEEP → RECOVERY), with the currently-active *peak* phase lit, plus the
 * population share in crisis, cumulative wage compression, and aggregate
 * capital stock (the last two are where devaluation reads).
 *
 * DATA (all already on the wire, zero backend work — Feature 018
 * crisis-devaluation surfaced via Program 17 Item 1a): `_serialize_territory`
 * (`web/game/engine_bridge.py`) emits `crisis_phase`/`crisis_duration`/
 * `wage_compression`/`capital_stock` on every `/state/` snapshot territory
 * row, off the graph-only `tick_crisis_*`/`tick_capital_stock` attrs the
 * crisis system writes (`domain/economics/tick/types.py::CrisisState`;
 * registered `SeamScope.TERRITORY`, `sentinels/seam/registry.py:433-484`).
 * The `TerritoryState` interface never declared them until this widget.
 *
 * HONESTY (Constitution III.11): the crisis detector runs on the YEAR
 * boundary, so early in a session every territory carries `crisis_phase:
 * null` — each aggregate returns `null` and the widget says so rather than
 * fabricating a "normal"/0. Capital stock is EXTENSIVE (summed, not averaged);
 * wage compression is population-weighted; the peak phase and crisis share
 * are population-weighted so a single tiny county in DEEP doesn't dominate.
 *
 * Mounted via `FloatingPanel` (anchor="free") in `AppShell`'s right-column
 * chrome stack alongside `BifurcationGauge`/`EventTray` — the exact sibling
 * position, copied line-for-line from that widget's precedent. No keyboard
 * hotkey (matches the whole `ui.chrome.*Open` family). Purely
 * frontend-computed aggregates over multiple rows, so — like
 * `BifurcationGauge` — it deliberately does NOT route through `StatChip`'s
 * `metric`/`scope` probe wiring (no single backend `explain`-able scalar).
 */

import { useStore } from "@/store";
import type { CrisisPhase, TerritoryState } from "@/types/game";
import { FloatingPanel } from "./FloatingPanel";

interface CrisisTimelineProps {
  gameId: string;
}

/**
 * The lifecycle order (mirrors the `CrisisPhase` StrEnum docstring). Index =
 * position on the strip; also the severity rank used to pick the peak
 * (RECOVERY sits AFTER deep as a distinct post-crisis state, so it never
 * out-ranks an active DEEP — see `peakCrisisPhase`).
 */
export const CRISIS_PHASE_ORDER: readonly CrisisPhase[] = [
  "normal",
  "onset",
  "early",
  "deep",
  "recovery",
] as const;

/** The phases that count as "in crisis" (CrisisState: ONSET through DEEP). */
export const CRISIS_IN_PROGRESS_PHASES: readonly CrisisPhase[] = [
  "onset",
  "early",
  "deep",
] as const;

/** Human labels for the strip segments. */
const CRISIS_PHASE_LABEL: Record<CrisisPhase, string> = {
  normal: "NORMAL",
  onset: "ONSET",
  early: "EARLY",
  deep: "DEEP",
  recovery: "RECOVERY",
};

/** Severity rank for picking the peak — only the ACTIVE crisis arc escalates. */
const CRISIS_SEVERITY: Record<CrisisPhase, number> = {
  normal: 0,
  onset: 1,
  early: 2,
  deep: 3,
  recovery: 0, // post-crisis, not more severe than DEEP
};

function isCrisisPhase(v: unknown): v is CrisisPhase {
  return typeof v === "string" && v in CRISIS_SEVERITY;
}

/**
 * The most severe crisis phase carried by any territory with positive
 * population. `null` when no populated territory carries a phase at all
 * (Constitution III.11 — never a fabricated "normal"). RECOVERY only wins
 * when nothing is actively in crisis, since its severity rank ties NORMAL.
 */
export function peakCrisisPhase(territories: TerritoryState[]): CrisisPhase | null {
  const phased = territories.filter(
    (t) => isCrisisPhase(t.crisis_phase) && Math.max(0, t.population) > 0,
  );
  if (phased.length === 0) return null;

  // Escalating arc first (highest severity wins); if nothing is in the
  // active arc, fall back to whichever phase is present (recovery/normal).
  let best: CrisisPhase = "normal";
  let bestSeverity = -1;
  let sawRecovery = false;
  for (const t of phased) {
    const phase = t.crisis_phase as CrisisPhase;
    if (phase === "recovery") sawRecovery = true;
    if (CRISIS_SEVERITY[phase] > bestSeverity) {
      bestSeverity = CRISIS_SEVERITY[phase];
      best = phase;
    }
  }
  // If the winner is NORMAL by rank but a RECOVERY was present, surface the
  // more informative RECOVERY (the county is climbing out, not flat-normal).
  if (bestSeverity === 0 && sawRecovery) return "recovery";
  return best;
}

/**
 * Population share (0..1) in an active crisis phase (onset/early/deep),
 * over the population that carries any phase. `null` when no territory
 * carries a phase.
 */
export function crisisPopulationShare(territories: TerritoryState[]): number | null {
  let phasedPop = 0;
  let crisisPop = 0;
  for (const t of territories) {
    if (!isCrisisPhase(t.crisis_phase)) continue;
    const pop = Math.max(0, t.population);
    phasedPop += pop;
    if (CRISIS_IN_PROGRESS_PHASES.includes(t.crisis_phase)) crisisPop += pop;
  }
  if (phasedPop === 0) {
    // Every phased territory carries zero population weight — fall back to a
    // plain territory-count share so the number is still honest, not null.
    const phased = territories.filter((t) => isCrisisPhase(t.crisis_phase));
    if (phased.length === 0) return null;
    const inCrisis = phased.filter((t) =>
      CRISIS_IN_PROGRESS_PHASES.includes(t.crisis_phase as CrisisPhase),
    ).length;
    return inCrisis / phased.length;
  }
  return crisisPop / phasedPop;
}

/**
 * Population-weighted mean of `wage_compression` over territories carrying
 * a finite value; plain mean when those rows carry no population; `null`
 * when none carry it.
 */
export function aggregateWageCompression(territories: TerritoryState[]): number | null {
  const rows = territories
    .map((t) => ({ value: t.wage_compression, population: t.population }))
    .filter(
      (r): r is { value: number; population: number } =>
        typeof r.value === "number" && Number.isFinite(r.value),
    );
  if (rows.length === 0) return null;
  const totalPop = rows.reduce((sum, r) => sum + Math.max(0, r.population), 0);
  if (totalPop > 0) {
    return rows.reduce((sum, r) => sum + r.value * Math.max(0, r.population), 0) / totalPop;
  }
  return rows.reduce((sum, r) => sum + r.value, 0) / rows.length;
}

/**
 * SUM of `capital_stock` across territories carrying a finite value —
 * capital stock is extensive, so the aggregate is a total (falling total =
 * devaluation), not a mean. `null` when no territory carries it.
 */
export function aggregateCapitalStock(territories: TerritoryState[]): number | null {
  const values = territories
    .map((t) => t.capital_stock)
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (values.length === 0) return null;
  return values.reduce((sum, v) => sum + v, 0);
}

/** Compact human formatting for a capital-stock total (K, $B/$M/$k). */
function formatCapital(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(value / 1e3).toFixed(1)}k`;
  return `$${value.toFixed(0)}`;
}

/** Segment fill class: lit red for an active crisis phase, green for an
 *  active normal/recovery phase, muted otherwise (avoids a nested ternary). */
function phaseSegClass(phase: CrisisPhase, active: boolean): string {
  if (!active) return "bg-plate text-ksbc-muted-2";
  return CRISIS_IN_PROGRESS_PHASES.includes(phase)
    ? "bg-rupture text-plate"
    : "bg-solidarity text-plate";
}

function PhaseStrip({ peak }: { peak: CrisisPhase | null }): React.JSX.Element {
  return (
    <div
      className="flex gap-0.5"
      data-testid="crisis-phase-strip"
      role="img"
      aria-label="Crisis lifecycle strip"
    >
      {CRISIS_PHASE_ORDER.map((phase) => {
        const active = phase === peak;
        return (
          <div
            key={phase}
            data-testid={`crisis-phase-seg-${phase}`}
            data-active={active}
            className={[
              "flex-1 rounded-[1px] px-1 py-0.5 text-center text-[7px] tracking-widest transition-colors",
              phaseSegClass(phase, active),
            ].join(" ")}
          >
            {CRISIS_PHASE_LABEL[phase]}
          </div>
        );
      })}
    </div>
  );
}

export function CrisisTimeline({ gameId: _gameId }: CrisisTimelineProps): React.JSX.Element {
  const crisisTimelineOpen = useStore((s) => s.ui.chrome.crisisTimelineOpen);
  const toggleCrisisTimeline = useStore((s) => s.ui.toggleCrisisTimeline);
  // `?? []` stays OUTSIDE the selector (BifurcationGauge's pattern) — a
  // fallback literal inside a zustand selector returns a new array reference
  // every call, tripping useSyncExternalStore's cached-snapshot guard.
  const snapshot = useStore((s) => s.world.snapshot);
  const territories = snapshot?.territories ?? [];

  const peak = peakCrisisPhase(territories);
  const share = crisisPopulationShare(territories);
  const wageCompression = aggregateWageCompression(territories);
  const capital = aggregateCapitalStock(territories);

  const hasAnySignal =
    peak !== null || share !== null || wageCompression !== null || capital !== null;

  return (
    <FloatingPanel
      anchor="free"
      title="Business Cycle"
      collapsed={!crisisTimelineOpen}
      onToggle={toggleCrisisTimeline}
      testId="crisis-timeline"
    >
      <div className="flex flex-col gap-1 p-2">
        {peak !== null && <PhaseStrip peak={peak} />}
        {!hasAnySignal ? (
          <p className="text-[9px] text-ksbc-muted-2" data-testid="crisis-empty-line">
            No crisis data yet — the detector runs on the year boundary.
          </p>
        ) : (
          <>
            <p className="text-[9px] text-ksbc-muted-2" data-testid="crisis-share-line">
              {share === null
                ? "Population in crisis: no data yet."
                : `Population in crisis: ${(share * 100).toFixed(0)}%`}
            </p>
            <p className="text-[9px] text-ksbc-muted-2" data-testid="crisis-wage-line">
              {wageCompression === null
                ? "Wage compression: no data yet."
                : `Wage compression: ${(wageCompression * 100).toFixed(0)}%`}
            </p>
            <p className="text-[9px] text-ksbc-muted-2" data-testid="crisis-capital-line">
              {capital === null
                ? "Capital stock: no data yet."
                : `Capital stock: ${formatCapital(capital)}`}
            </p>
          </>
        )}
      </div>
    </FloatingPanel>
  );
}
