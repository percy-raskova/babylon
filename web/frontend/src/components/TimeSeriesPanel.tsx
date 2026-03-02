/**
 * Time series panel component.
 *
 * Tracks and displays key metrics over ticks using Recharts.
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
  const nodes = Object.values(snap.nodes);
  const territories = nodes.filter((n) => n.node_type === "territory");

  const avgHeat =
    territories.length > 0
      ? territories.reduce((s, t) => s + Number(t["heat"] ?? 0), 0) /
        territories.length
      : 0;

  const avgConsciousness =
    nodes.length > 0
      ? nodes.reduce((s, n) => s + Number(n["consciousness"] ?? 0), 0) /
        nodes.length
      : 0;

  const totalWealth = nodes.reduce(
    (s, n) => s + Number(n["wealth"] ?? 0),
    0,
  );

  const orgCount = Object.keys(snap.organizations ?? {}).length;
  const eventCount = (snap.events ?? []).length;

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

  // Append new data points (deduplicated by tick)
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

  // Simple sparkline rendering (Recharts integration deferred to npm install)
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
    <div style={styles.container}>
      <h3 style={styles.title}>Time Series</h3>
      <div style={styles.grid}>
        {sparklines.map(({ metric, points, latest: val }) => (
          <div key={metric} style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.metricName}>
                {metric.replace(/_/g, " ")}
              </span>
              <span style={styles.metricValue}>
                {typeof val === "number" ? val.toFixed(2) : val}
              </span>
            </div>
            <svg
              viewBox="0 0 200 40"
              style={styles.sparkline}
              preserveAspectRatio="none"
            >
              <polyline
                points={points}
                fill="none"
                stroke="#c8a860"
                strokeWidth="1.5"
              />
            </svg>
          </div>
        ))}
      </div>
      {latest && (
        <div style={styles.footer}>
          {history.length} ticks recorded
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column" as const,
    height: "100%",
  },
  title: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#c8a860",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
    marginBottom: "12px",
    flexShrink: 0,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "8px",
    overflow: "auto",
    flex: 1,
  },
  card: {
    background: "#0e0e18",
    border: "1px solid #2a2a3a",
    borderRadius: "6px",
    padding: "8px 10px",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: "4px",
  },
  metricName: {
    fontSize: "10px",
    color: "#666",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  metricValue: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#e0e0e0",
    fontFamily: "monospace",
  },
  sparkline: {
    width: "100%",
    height: "30px",
  },
  footer: {
    fontSize: "11px",
    color: "#444",
    textAlign: "center" as const,
    padding: "8px 0",
    flexShrink: 0,
  },
};
