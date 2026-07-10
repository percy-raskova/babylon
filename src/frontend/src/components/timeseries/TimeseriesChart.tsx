/**
 * Timeseries panel — real `/timeseries/` arrays plotted with recharts.
 *
 * Renders imperial_rent / consciousness / solidarity — the fields the
 * real `TimeseriesPayload` contract actually carries (`types/game.ts`).
 * Null entries (a tick with no computed value for that series) render as
 * a gap, not a fabricated zero (Constitution III.11) — recharts' default
 * `connectNulls={false}` already does this.
 */

import { useEffect } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useStore } from "@/store";
import type { TimeseriesPayload } from "@/types/game";

interface TimeseriesChartProps {
  gameId: string;
}

interface ChartRow {
  tick: number;
  imperial_rent: number | null;
  consciousness: number | null;
  solidarity: number | null;
}

function toChartRows(payload: TimeseriesPayload): ChartRow[] {
  return payload.ticks.map((tick, i) => ({
    tick,
    imperial_rent: payload.imperial_rent[i] ?? null,
    consciousness: payload.consciousness[i] ?? null,
    solidarity: payload.solidarity[i] ?? null,
  }));
}

export function TimeseriesChart({ gameId }: TimeseriesChartProps): React.JSX.Element {
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
    return <p className="p-3 text-[11px] text-ash">Loading timeseries…</p>;
  }
  if (error) {
    return (
      <p role="alert" className="p-3 text-[11px] text-laser">
        {error}
      </p>
    );
  }
  if (data === null || data.ticks.length === 0) {
    return <p className="p-3 text-[11px] italic text-shroud">No timeseries data yet.</p>;
  }

  return (
    <div className="h-full p-2" data-testid="timeseries-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={toChartRows(data)}>
          <XAxis dataKey="tick" tick={{ fontSize: 9, fill: "var(--babylon-ash)" }} />
          <YAxis tick={{ fontSize: 9, fill: "var(--babylon-ash)" }} />
          <Tooltip
            contentStyle={{
              background: "var(--babylon-concrete)",
              border: "1px solid var(--babylon-rebar)",
              fontSize: 11,
            }}
          />
          <Line type="monotone" dataKey="imperial_rent" stroke="var(--babylon-rent)" dot={false} />
          <Line type="monotone" dataKey="consciousness" stroke="var(--babylon-cadre)" dot={false} />
          <Line
            type="monotone"
            dataKey="solidarity"
            stroke="var(--babylon-solidarity)"
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
