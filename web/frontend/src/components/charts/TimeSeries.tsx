/**
 * Time series panel — Recharts LineCharts showing key metrics over ticks.
 *
 * Replaces the SVG sparkline stub with four interactive Recharts charts
 * matching the spec's time series layout. Charts render from tick
 * summaries accumulated in the game store.
 */

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { useGameStore, type TickSummary } from "@/stores/gameStore";
import type { GameSnapshot } from "@/types/game";

/** Chart definition — maps store data to chart lines. */
interface ChartDef {
  title: string;
  lines: { key: keyof TickSummary; color: string; label: string }[];
  yDomain?: [number, number];
}

const CHARTS: ChartDef[] = [
  {
    title: "Wealth",
    lines: [{ key: "totalWealth", color: "var(--color-data-green)", label: "Total Wealth" }],
  },
  {
    title: "Heat",
    lines: [{ key: "avgHeat", color: "var(--color-gold)", label: "Avg Heat" }],
    yDomain: [0, 1],
  },
  {
    title: "Consciousness",
    lines: [{ key: "avgConsciousness", color: "var(--color-gold)", label: "Avg Consciousness" }],
    yDomain: [0, 1],
  },
  {
    title: "Organization",
    lines: [
      { key: "orgCount", color: "var(--color-royal-blue)", label: "Orgs" },
      { key: "edgeCount", color: "var(--color-gold)", label: "Edges" },
    ],
  },
];

interface TimeSeriesProps {
  snapshot: GameSnapshot;
}

export function TimeSeries({ snapshot }: TimeSeriesProps) {
  const tickSummaries = useGameStore((s) => s.tickSummaries);
  const currentTick = snapshot.tick;

  // Memoize chart data to avoid recalculating on every render
  const chartData = useMemo(() => tickSummaries.map((s) => ({ ...s })), [tickSummaries]);

  if (chartData.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-ash">
        No tick data recorded yet
      </div>
    );
  }

  return (
    <div className="flex h-full gap-2 overflow-hidden">
      {CHARTS.map((chart) => (
        <TimeSeriesChart
          key={chart.title}
          chart={chart}
          data={chartData}
          currentTick={currentTick}
        />
      ))}
    </div>
  );
}

/** Individual chart panel. */
function TimeSeriesChart({
  chart,
  data,
  currentTick,
}: {
  chart: ChartDef;
  data: TickSummary[];
  currentTick: number;
}) {
  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <span className="mb-1 text-[10px] uppercase tracking-wider text-ash">{chart.title}</span>
      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="tick"
              tick={{ fontSize: 9, fill: "#606070" }}
              axisLine={{ stroke: "#2a2a3a" }}
              tickLine={false}
            />
            <YAxis
              domain={chart.yDomain ?? ["auto", "auto"]}
              tick={{ fontSize: 9, fill: "#606070" }}
              axisLine={false}
              tickLine={false}
              width={36}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0a0a14",
                border: "1px solid #2a2a3a",
                borderRadius: "4px",
                fontSize: "11px",
              }}
              labelStyle={{ color: "#b0b0c0" }}
              itemStyle={{ padding: 0 }}
              isAnimationActive={false}
            />
            <ReferenceLine x={currentTick} stroke="#d4a843" strokeDasharray="3 3" />
            {chart.lines.map((line) => (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                stroke={line.color}
                strokeWidth={1.5}
                dot={false}
                name={line.label}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
