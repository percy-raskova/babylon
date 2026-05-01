/**
 * SparklineStrip — 3 compact sparklines in a horizontal row.
 *
 * Reads tickSummaries from gameStore. Shows avgHeat, avgConsciousness,
 * totalWealth. Handles empty (tick 0), partial, and full-window states.
 */

import { useMemo } from "react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { useGameStore, type TickSummary } from "@/stores/gameStore";

interface SparklineProps {
  data: { value: number }[];
  color: string;
  label: string;
  currentValue: string;
}

function Sparkline({ data, color, label, currentValue }: SparklineProps) {
  return (
    <div className="flex flex-1 items-center gap-2 rounded border border-wet-concrete bg-dark-metal px-3 py-1.5">
      <div className="flex flex-col">
        <span className="text-[9px] uppercase tracking-wider text-ash">{label}</span>
        <span className="font-mono text-xs font-semibold text-bone">{currentValue}</span>
      </div>
      <div className="h-8 w-20">
        {data.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-[9px] text-ash">—</div>
        )}
      </div>
    </div>
  );
}

export function SparklineStrip() {
  const tickSummaries = useGameStore((s) => s.tickSummaries);

  const { heatData, consciousnessData, wealthData, latest } = useMemo(() => {
    const window = tickSummaries.slice(-30);
    return {
      heatData: window.map((s: TickSummary) => ({ value: s.avgHeat })),
      consciousnessData: window.map((s: TickSummary) => ({ value: s.avgConsciousness })),
      wealthData: window.map((s: TickSummary) => ({ value: s.totalWealth })),
      latest: window[window.length - 1] ?? null,
    };
  }, [tickSummaries]);

  return (
    <div className="flex shrink-0 gap-2 px-3 py-1.5">
      <Sparkline
        data={heatData}
        color="#e63946"
        label="Avg Heat"
        currentValue={latest ? latest.avgHeat.toFixed(2) : "—"}
      />
      <Sparkline
        data={consciousnessData}
        color="#8b5cf6"
        label="Avg Consciousness"
        currentValue={latest ? latest.avgConsciousness.toFixed(2) : "—"}
      />
      <Sparkline
        data={wealthData}
        color="#4ade80"
        label="Total Budget"
        currentValue={latest ? latest.totalWealth.toFixed(0) : "—"}
      />
    </div>
  );
}
