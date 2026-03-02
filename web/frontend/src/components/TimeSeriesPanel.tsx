/**
 * Time series panel component.
 *
 * Tracks and displays key metrics over ticks using SVG sparklines.
 * Accumulates snapshots in memory to build time series.
 */

import { useEffect, useMemo, useRef } from "react";
import type { GameSnapshot } from "@/types/game";

/** A single data point for a tick. */
interface TickDataPoint {
  tick: number;
  [metric: string]: number;
}

/** Metrics to extract from each snapshot. */
const TRACKED_METRICS = [
  "avg_heat",
  "avg_consciousness",
  "total_wealth",
  "org_count",
  "event_count",
] as const;

interface TimeSeriesPanelProps {
  snapshot: GameSnapshot;
}

/** Extract aggregate metrics from a snapshot. */
function extractMetrics(snap: GameSnapshot): TickDataPoint {
  const territories = snap.territories;
  const entities = snap.entities;

  const avgHeat =
    territories.length > 0
      ? territories.reduce((s, t) => s + t.heat, 0) / territories.length
      : 0;

  const avgConsciousness =
    entities.length > 0
      ? entities.reduce((s, e) => s + e.consciousness, 0) / entities.length
      : 0;

  const totalWealth = entities.reduce((s, e) => s + e.wealth, 0);

  const orgCount = snap.organizations.length;
  const eventCount = snap.events.length;

  return {
    tick: snap.tick,
    avg_heat: avgHeat,
    avg_consciousness: avgConsciousness,
    total_wealth: totalWealth,
    org_count: orgCount,
    event_count: eventCount,
  };
}

export function TimeSeriesPanel({ snapshot }: TimeSeriesPanelProps) {
  const historyRef = useRef<TickDataPoint[]>([]);

  useEffect(() => {
    const metrics = extractMetrics(snapshot);
    const existing = historyRef.current;
    if (
      existing.length === 0 ||
      existing[existing.length - 1]!.tick !== metrics.tick
    ) {
      historyRef.current = [...existing, metrics];
    }
  }, [snapshot]);

  const history = historyRef.current;
  const latest = history[history.length - 1];

  const sparklines = useMemo(() => {
    return TRACKED_METRICS.map((metric) => {
      const values = history.map((d) => d[metric] ?? 0);
      const max = Math.max(...values, 1);
      const points = values
        .map((v, i) => {
          const x = (i / Math.max(values.length - 1, 1)) * 200;
          const y = 40 - (v / max) * 35;
          return `${x},${y}`;
        })
        .join(" ");
      return { metric, points, latest: values[values.length - 1] ?? 0 };
    });
  }, [history]);

  return (
    <div className="flex h-full flex-col">
      <h3 className="mb-3 shrink-0 text-sm font-semibold uppercase tracking-wider text-gold">
        Time Series
      </h3>
      <div className="grid flex-1 grid-cols-2 gap-2 overflow-auto">
        {sparklines.map(({ metric, points, latest: val }) => (
          <div
            key={metric}
            className="rounded-md border border-wet-concrete bg-void px-2.5 py-2"
          >
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-[10px] uppercase tracking-wider text-ash">
                {metric.replace(/_/g, " ")}
              </span>
              <span className="font-mono text-sm font-semibold text-bone">
                {typeof val === "number" ? val.toFixed(2) : val}
              </span>
            </div>
            <svg
              viewBox="0 0 200 40"
              className="h-[30px] w-full"
              preserveAspectRatio="none"
            >
              <polyline
                points={points}
                fill="none"
                stroke="var(--color-gold)"
                strokeWidth="1.5"
              />
            </svg>
          </div>
        ))}
      </div>
      {latest && (
        <div className="shrink-0 py-2 text-center text-[11px] text-soot">
          {history.length} ticks recorded
        </div>
      )}
    </div>
  );
}
