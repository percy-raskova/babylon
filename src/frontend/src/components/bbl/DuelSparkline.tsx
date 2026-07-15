/**
 * DuelSparkline — two-series SVG sparkline for the class InspectionCard's
 * "Survival Duel" chart (Wave 2 W2.5a, `reports/wave2-implementation-map.md`
 * owner ruling 3): P(S|A) (survival by acquiescence) vs P(S|R) (survival by
 * revolution) plotted on one shared y-scale, with rupture markers at ticks
 * where an UPRISING event's `data.trigger === "revolutionary_pressure"`
 * fired for this class (`SurvivalDuelPanel` supplies both, real-fetched —
 * never client-side accumulation).
 *
 * Extends `bbl/Sparkline`'s conventions: block SVG, `var(--babylon-*)`
 * stroke colors passed as literal strings (the same pattern already used
 * for `Sparkline`'s `color` prop — see `BlocFlowLines.tsx`'s
 * `color="var(--babylon-spire)"`). Colors: P(S|R) uses `--babylon-laser`
 * (crimson — matches `lib/inspect/adapters/node.ts`'s existing
 * `CONSCIOUSNESS_COLORS.revolutionary`), P(S|A) uses `--babylon-cadre`
 * (matches that same file's `CONSCIOUSNESS_COLORS.liberal` — acquiescence
 * as accommodation), and rupture markers use `--babylon-rupture`
 * (`index.css`: "REVOLUTION — bronze-gold, used rarely" — literally the
 * rare-event color, reserved for the marker so it never collides with
 * either series line).
 *
 * Null-honest (Constitution III.11): a tick whose value is `null` breaks
 * that series' polyline into a separate run rather than interpolating
 * across the gap or fabricating a zero; a marker whose tick has no matching
 * history point is silently skipped rather than plotted at a guessed
 * position.
 */

import type { ClassHistoryPoint, RuptureMarker } from "@/types/game";

const ACQUIESCENCE_COLOR = "var(--babylon-cadre)";
const REVOLUTION_COLOR = "var(--babylon-laser)";
const MARKER_COLOR = "var(--babylon-rupture)";

interface DuelSparklineProps {
  /** Oldest-tick-first. */
  points: ClassHistoryPoint[];
  markers?: RuptureMarker[];
  w?: number;
  h?: number;
}

/** x-position for point index `i` across `count` points; 0 when `count <= 1`
 * (a lone tick renders at the left edge instead of the `NaN` a `/0` step
 * would produce). */
function xFor(i: number, count: number, w: number): number {
  return count > 1 ? (i * w) / (count - 1) : 0;
}

/** Split a series into contiguous non-null runs of `"x,y"` point strings —
 * one `<polyline>` per run, so a null tick opens a visible gap instead of
 * an interpolated line across missing data. */
function seriesRuns(
  values: (number | null)[],
  min: number,
  span: number,
  w: number,
  h: number,
): string[][] {
  const runs: string[][] = [];
  let current: string[] = [];
  values.forEach((v, i) => {
    if (v === null) {
      if (current.length > 0) runs.push(current);
      current = [];
      return;
    }
    const x = xFor(i, values.length, w);
    const y = h - ((v - min) / span) * h;
    current.push(`${x},${y}`);
  });
  if (current.length > 0) runs.push(current);
  return runs;
}

export function DuelSparkline({
  points,
  markers = [],
  w = 140,
  h = 32,
}: DuelSparklineProps): React.JSX.Element {
  if (points.length === 0) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid="duel-sparkline-empty">
        No survival-calculus history recorded yet.
      </p>
    );
  }

  const acquiescence = points.map((p) => p.p_acquiescence);
  const revolution = points.map((p) => p.p_revolution);
  const allValues = [...acquiescence, ...revolution].filter((v): v is number => v !== null);

  if (allValues.length === 0) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid="duel-sparkline-no-values">
        No survival-calculus values recorded yet.
      </p>
    );
  }

  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const span = max - min || 1;

  const acquiescenceRuns = seriesRuns(acquiescence, min, span, w, h);
  const revolutionRuns = seriesRuns(revolution, min, span, w, h);

  return (
    <svg
      width={w}
      height={h}
      className="block"
      data-testid="duel-sparkline"
      role="img"
      aria-label="Survival duel: acquiescence vs revolution probability history"
    >
      {acquiescenceRuns.map((run, i) => (
        <polyline
          key={`acq-${i}`}
          data-testid="duel-sparkline-acquiescence"
          fill="none"
          stroke={ACQUIESCENCE_COLOR}
          strokeWidth="1.2"
          points={run.join(" ")}
        />
      ))}
      {revolutionRuns.map((run, i) => (
        <polyline
          key={`rev-${i}`}
          data-testid="duel-sparkline-revolution"
          fill="none"
          stroke={REVOLUTION_COLOR}
          strokeWidth="1.2"
          points={run.join(" ")}
        />
      ))}
      {markers.map((marker) => {
        const index = points.findIndex((p) => p.tick === marker.tick);
        if (index === -1) return null;
        const x = xFor(index, points.length, w);
        return (
          <line
            key={marker.eventId}
            data-testid={`duel-sparkline-marker-${marker.eventId}`}
            x1={x}
            y1={0}
            x2={x}
            y2={h}
            stroke={MARKER_COLOR}
            strokeWidth="1"
            strokeDasharray="2,1"
          />
        );
      })}
    </svg>
  );
}
