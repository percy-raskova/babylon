/**
 * Observatory time-series chart — Recharts, Tufte-minimal, palette tokens.
 *
 * Constitution VII: color = data (semantic-invariant metric colours via CSS
 * tokens), data-ink maximised (no grid, first/last tick labels only), no
 * decorative glow. Ported from `web/frontend/src/observatory/ObservatoryChart.tsx`
 * (spec-096/spec-099) onto the cockpit's Cold Collapse palette (spec-090):
 * the old theme's gold/crimson/silver/data-green/royal-blue/bio-green tokens
 * don't exist here, so each metric is remapped onto a distinct Cold Collapse
 * accent (`--color-*`, `src/index.css`) rather than reusing the retired names.
 */

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SeriesMetric, ValueAggregatePoint } from "./types";

/** Semantic metric colours (VII.6 invariance) — Cold Collapse palette tokens. */
const METRIC_COLORS: Record<SeriesMetric, string> = {
  v_sum: "var(--color-cadre)", // variable capital (labour value)
  s_sum: "var(--color-rent)", // surplus (extraction — imperial rent)
  c_sum: "var(--color-fog)", // constant capital
  k_sum: "var(--color-rupture)", // k
  biocapacity_sum: "var(--color-solidarity)", // biocapacity
  hex_count: "var(--color-ash)", // hex count
};

const METRIC_LABELS: Record<SeriesMetric, string> = {
  v_sum: "Variable capital (v)",
  s_sum: "Surplus (s)",
  c_sum: "Constant capital (c)",
  k_sum: "Capital (k)",
  biocapacity_sum: "Biocapacity",
  hex_count: "Hex count",
};

interface ObservatoryChartProps {
  points: ValueAggregatePoint[];
  metrics: SeriesMetric[];
}

export function ObservatoryChart({ points, metrics }: ObservatoryChartProps) {
  if (points.length === 0) {
    return (
      <div role="status" className="flex h-full items-center justify-center text-sm text-ash">
        No data for this scope
      </div>
    );
  }

  const firstTick = points[0]?.tick;
  const lastTick = points[points.length - 1]?.tick;
  const ticks = firstTick !== undefined && lastTick !== undefined ? [firstTick, lastTick] : [];

  return (
    <div className="h-full w-full" data-testid="observatory-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <XAxis
            dataKey="tick"
            ticks={ticks}
            tick={{ fontSize: 10, fill: "var(--babylon-ash)" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--babylon-ash)" }}
            axisLine={false}
            tickLine={false}
            width={64}
            tickCount={4}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--babylon-tar)",
              border: "1px solid var(--babylon-rebar)",
              borderRadius: "4px",
              fontSize: "11px",
            }}
            labelFormatter={(tick) => `Tick ${tick}`}
            labelStyle={{ color: "var(--babylon-fog)" }}
            isAnimationActive={false}
          />
          {metrics.map((metric) => (
            <Line
              key={metric}
              type="monotone"
              dataKey={metric}
              name={METRIC_LABELS[metric]}
              stroke={METRIC_COLORS[metric]}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export { METRIC_LABELS };
