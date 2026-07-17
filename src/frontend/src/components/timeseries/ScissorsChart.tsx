/**
 * The Scissors — price⟷value divergence chart (Program 23, ADR077).
 *
 * Two form-pole series against the substance baseline: `price_index`
 * (prices over the value anchor) and `fictitious_ratio` (capitalized
 * claims over real capitalization), both exp-mapped so 1.0 means the
 * form coincides with its substance. The ReferenceLine at y=1 IS the
 * law of value — the player watches the phenomenal form diverge from
 * and snap back to it. Null entries (axis absent that tick) render as
 * gaps, never a fabricated 1.0 (Constitution III.11) — recharts'
 * default `connectNulls={false}` already does this.
 *
 * Reads the same `/timeseries/` panel data as `TimeseriesChart` — no
 * extra fetch; both mount idioms are shared.
 */

import { useEffect } from "react";
import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { MarketTicker } from "@/components/timeseries/MarketTicker";
import { deriveCorrectionTicks } from "@/lib/scissors";
import { useStore } from "@/store";
import type { TimeseriesPayload } from "@/types/game";

interface ScissorsChartProps {
  gameId: string;
}

interface ScissorsRow {
  tick: number;
  price_index: number | null;
  fictitious_ratio: number | null;
}

function toScissorsRows(payload: TimeseriesPayload): ScissorsRow[] {
  // `?? []` guards a pre-Program-23 backend payload (rollout skew): the
  // arrays absent entirely reads as "no axis", same as all-null.
  const priceIndex = payload.price_index ?? [];
  const fictitiousRatio = payload.fictitious_ratio ?? [];
  return payload.ticks.map((tick, i) => ({
    tick,
    price_index: priceIndex[i] ?? null,
    fictitious_ratio: fictitiousRatio[i] ?? null,
  }));
}

function hasAnyScissorsValue(payload: TimeseriesPayload): boolean {
  return (
    (payload.price_index ?? []).some((v) => v !== null) ||
    (payload.fictitious_ratio ?? []).some((v) => v !== null)
  );
}

export function ScissorsChart({ gameId }: ScissorsChartProps): React.JSX.Element {
  const data = useStore((s) => s.panels.timeseries.data);
  const loading = useStore((s) => s.panels.timeseries.loading);
  const error = useStore((s) => s.panels.timeseries.error);
  const fetchTimeseries = useStore((s) => s.panels.timeseries.fetch);
  const setMounted = useStore((s) => s.panels.timeseries.setMounted);

  useEffect(() => {
    setMounted(true);
    void fetchTimeseries(gameId);
    return () => setMounted(false);
  }, [gameId, fetchTimeseries, setMounted]);

  if (loading && data === null) {
    return <p className="p-3 text-[11px] text-ash">Loading the scissors…</p>;
  }
  if (error) {
    return (
      <p role="alert" className="p-3 text-[11px] text-laser">
        {error}
      </p>
    );
  }
  if (data === null || data.ticks.length === 0 || !hasAnyScissorsValue(data)) {
    return (
      <p className="p-3 text-[11px] italic text-shroud">
        No market axis yet — the phenomenal form awaits its substance.
      </p>
    );
  }

  const correctionTicks = deriveCorrectionTicks(data);

  return (
    <div className="flex h-full flex-col" data-testid="scissors-chart">
      <MarketTicker payload={data} />
      <div className="min-h-0 flex-1 p-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={toScissorsRows(data)}>
            <XAxis dataKey="tick" tick={{ fontSize: 9, fill: "var(--babylon-ash)" }} />
            <YAxis tick={{ fontSize: 9, fill: "var(--babylon-ash)" }} domain={["auto", "auto"]} />
            <Tooltip
              contentStyle={{
                background: "var(--babylon-concrete)",
                border: "1px solid var(--babylon-rebar)",
                fontSize: 11,
              }}
            />
            {/* The substance baseline: price at value, claims at real K. */}
            <ReferenceLine
              y={1}
              stroke="var(--babylon-ash)"
              strokeDasharray="4 3"
              label={{ value: "value", fontSize: 9, fill: "var(--babylon-ash)" }}
            />
            {/* ADR078: each snap tick — the correction made visible. */}
            {correctionTicks.map((tick) => (
              <ReferenceLine
                key={`correction-${tick}`}
                x={tick}
                stroke="var(--babylon-laser)"
                strokeDasharray="2 2"
                label={{ value: "correction", fontSize: 8, fill: "var(--babylon-laser)" }}
              />
            ))}
            <Line type="monotone" dataKey="price_index" stroke="var(--babylon-rent)" dot={false} />
            <Line
              type="monotone"
              dataKey="fictitious_ratio"
              stroke="var(--babylon-heat)"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
