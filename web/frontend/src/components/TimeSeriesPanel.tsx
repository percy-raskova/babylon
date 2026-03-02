/**
 * Time series panel component.
 *
 * Displays key metrics over ticks using SVG sparklines.
 * Reads accumulated tick summaries from the game store.
 */

import { useMemo } from "react";
import { useGameStore, type TickSummary } from "@/stores/gameStore";
import type { GameSnapshot } from "@/types/game";

/** Metrics to extract from each summary. */
const TRACKED_METRICS: { key: keyof TickSummary; label: string }[] = [
  { key: "avgHeat", label: "avg heat" },
  { key: "avgConsciousness", label: "avg consciousness" },
  { key: "totalWealth", label: "total wealth" },
  { key: "orgCount", label: "org count" },
  { key: "eventCount", label: "event count" },
];

interface TimeSeriesPanelProps {
  snapshot: GameSnapshot;
}

export function TimeSeriesPanel({ snapshot: _snapshot }: TimeSeriesPanelProps) {
  const tickSummaries = useGameStore((s) => s.tickSummaries);

  const sparklines = useMemo(() => {
    return TRACKED_METRICS.map(({ key, label }) => {
      const values = tickSummaries.map((s) => Number(s[key]));
      const max = Math.max(...values, 1);
      const points = values
        .map((v, i) => {
          const x = (i / Math.max(values.length - 1, 1)) * 200;
          const y = 40 - (v / max) * 35;
          return `${x},${y}`;
        })
        .join(" ");
      return { key, label, points, latest: values[values.length - 1] ?? 0 };
    });
  }, [tickSummaries]);

  return (
    <div className="flex h-full flex-col">
      <h3 className="mb-3 shrink-0 text-sm font-semibold uppercase tracking-wider text-gold">
        Time Series
      </h3>
      <div className="grid flex-1 grid-cols-2 gap-2 overflow-auto">
        {sparklines.map(({ key, label, points, latest }) => (
          <div key={key} className="rounded-md border border-wet-concrete bg-void px-2.5 py-2">
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-[10px] uppercase tracking-wider text-ash">{label}</span>
              <span className="font-mono text-sm font-semibold text-bone">
                {typeof latest === "number" ? latest.toFixed(2) : latest}
              </span>
            </div>
            <svg viewBox="0 0 200 40" className="h-[30px] w-full" preserveAspectRatio="none">
              <polyline points={points} fill="none" stroke="var(--color-gold)" strokeWidth="1.5" />
            </svg>
          </div>
        ))}
      </div>
      {tickSummaries.length > 0 && (
        <div className="shrink-0 py-2 text-center text-[11px] text-soot">
          {tickSummaries.length} ticks recorded
        </div>
      )}
    </div>
  );
}
