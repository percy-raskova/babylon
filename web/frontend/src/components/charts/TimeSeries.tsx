/**
 * Time series panel — Recharts LineCharts with Tufte-aligned styling.
 *
 * Data-ink ratio >0.8: no grid lines, minimal axis labels (first/last tick),
 * constitutional palette (CRIMSON for extraction, GOLD for solidarity, SILVER for mass).
 * Metric selector allows choosing which indicators to chart.
 */

import { useMemo, useState } from "react";
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
import { useUIStore } from "@/stores/uiStore";
import { getLensById } from "@/lib/lensDefinitions";
import type { GameSnapshot } from "@/types/game";

/** Chart definition — maps store data to chart lines. */
interface ChartDef {
  title: string;
  lines: { key: keyof TickSummary; color: string; label: string }[];
  yDomain?: [number, number];
}

/** Full metric catalog. */
const ALL_CHARTS: ChartDef[] = [
  {
    title: "Wealth",
    lines: [{ key: "totalWealth", color: "var(--color-data-green)", label: "Total Wealth" }],
  },
  {
    title: "Heat",
    lines: [{ key: "avgHeat", color: "var(--color-crimson)", label: "Avg Heat" }],
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
      { key: "edgeCount", color: "var(--color-silver)", label: "Edges" },
    ],
  },
];

/** Map lens default chart metrics to chart titles. */
const LENS_CHART_DEFAULTS: Record<string, string[]> = {
  economic: ["Wealth", "Heat", "Organization"],
  political: ["Consciousness", "Heat", "Organization"],
  social: ["Consciousness", "Wealth", "Organization"],
  strategic: ["Heat", "Consciousness", "Wealth", "Organization"],
};

interface TimeSeriesProps {
  snapshot: GameSnapshot;
}

export function TimeSeries({ snapshot }: TimeSeriesProps) {
  const tickSummaries = useGameStore((s) => s.tickSummaries);
  const activeLens = useUIStore((s) => s.activeLens);
  const currentTick = snapshot.tick;
  const lens = getLensById(activeLens);

  // Default charts based on active lens
  const fallback = LENS_CHART_DEFAULTS.political ?? [];
  const defaultCharts = LENS_CHART_DEFAULTS[lens.id] ?? fallback;
  const [selectedCharts, setSelectedCharts] = useState<string[]>(() => defaultCharts);

  const chartData = useMemo(() => tickSummaries.map((s) => ({ ...s })), [tickSummaries]);

  const visibleCharts = ALL_CHARTS.filter((c) => selectedCharts.includes(c.title));

  if (chartData.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-ash">
        No tick data recorded yet
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-1 overflow-hidden">
      {/* Metric selector */}
      <div className="flex shrink-0 items-center gap-1">
        {ALL_CHARTS.map((chart) => {
          const active = selectedCharts.includes(chart.title);
          return (
            <button
              key={chart.title}
              onClick={() => {
                if (active && selectedCharts.length > 1) {
                  setSelectedCharts(selectedCharts.filter((c) => c !== chart.title));
                } else if (!active) {
                  setSelectedCharts([...selectedCharts, chart.title]);
                }
              }}
              className={`rounded px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider transition-colors ${
                active ? "bg-dark-metal text-gold" : "text-ash hover:text-silver"
              }`}
            >
              {chart.title}
            </button>
          );
        })}
      </div>

      {/* Charts */}
      <div className="flex min-h-0 flex-1 gap-2 overflow-hidden">
        {visibleCharts.map((chart) => (
          <TimeSeriesChart
            key={chart.title}
            chart={chart}
            data={chartData}
            currentTick={currentTick}
          />
        ))}
      </div>
    </div>
  );
}

/** Individual chart panel with Tufte-aligned minimal styling. */
function TimeSeriesChart({
  chart,
  data,
  currentTick,
}: {
  chart: ChartDef;
  data: TickSummary[];
  currentTick: number;
}) {
  // Only show first and last tick labels for Tufte minimalism
  const firstTick = data.length > 0 ? data[0]?.tick : undefined;
  const lastTick = data.length > 0 ? data[data.length - 1]?.tick : undefined;
  const ticks = firstTick !== undefined && lastTick !== undefined ? [firstTick, lastTick] : [];

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <span className="mb-0.5 text-[10px] uppercase tracking-wider text-ash">{chart.title}</span>
      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="tick"
              ticks={ticks}
              tick={{ fontSize: 9, fill: "#787878" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={chart.yDomain ?? ["auto", "auto"]}
              tick={{ fontSize: 9, fill: "#787878" }}
              axisLine={false}
              tickLine={false}
              width={30}
              tickCount={3}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0a0a14",
                border: "1px solid #2a2a3a",
                borderRadius: "4px",
                fontSize: "11px",
              }}
              labelFormatter={(tick) => `Tick ${tick}`}
              labelStyle={{ color: "#b0b0c0" }}
              itemStyle={{ padding: 0 }}
              isAnimationActive={false}
            />
            <ReferenceLine x={currentTick} stroke="#c8a860" strokeWidth={1} strokeDasharray="3 3" />
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
