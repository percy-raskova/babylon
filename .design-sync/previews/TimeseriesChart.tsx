/**
 * TimeseriesChart preview — the Bottom Strip's `/timeseries/` line chart
 * (imperial_rent / consciousness / solidarity, real payload fields —
 * `heat`/`wealth`/`biocapacity` exist on the wire contract but aren't
 * plotted by this component). Store-driven AND fetches on mount
 * (`useEffect` calls `panels.timeseries.fetch(gameId)`), so seeding data
 * alone isn't enough — the real fetch would race a network call against a
 * static preview server and clobber the seed with a loud error. Each seed
 * overrides `fetch`/`setMounted` to inert no-ops so the mount effect can't
 * mutate state after the seed (see learnings — same technique needed by
 * ObjectivesTracker).
 *
 * Cells set different store states, so the combined card lies (singleton
 * store) — needs cfg.overrides.TimeseriesChart = {cardMode: "single",
 * primaryStory: "Populated"} (see learnings).
 */
import { TimeseriesChart, useStore } from "babylon-cockpit";

async function noopFetch(): Promise<void> {}
function noopSetMounted(): void {}

function seedTimeseries(patch: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    panels: {
      ...s.panels,
      timeseries: {
        ...s.panels.timeseries,
        data: null,
        loading: false,
        error: null,
        fetch: noopFetch,
        setMounted: noopSetMounted,
        ...patch,
      },
    },
  }));
}

// 26 ticks of a decaying-core scenario: Imperial Rent climbing, revolutionary
// consciousness climbing, solidarity-edge count noisy but trending up.
const TICKS = Array.from({ length: 26 }, (_, i) => 79 + i);
const IMPERIAL_RENT = TICKS.map((_, i) => Number((8.4 + i * 1.05 + Math.sin(i / 3) * 0.6).toFixed(2)));
const CONSCIOUSNESS = TICKS.map((_, i) =>
  Number(Math.min(0.58, 0.19 + i * 0.0135 + Math.sin(i / 4) * 0.01).toFixed(3)),
);
const SOLIDARITY = TICKS.map((_, i) => Math.max(1, Math.round(2 + Math.sin(i / 2.2) * 1.6 + i * 0.05)));
const HEAT = TICKS.map((_, i) => Number(Math.min(0.9, 0.3 + i * 0.012).toFixed(3)));
const WEALTH = TICKS.map((_, i) => Number((420 - i * 3.1).toFixed(1)));
const BIOCAPACITY = TICKS.map((_, i) => Number(Math.max(0.1, 0.4 - i * 0.006).toFixed(3)));

// Inline style, not a Tailwind arbitrary-value class: .design-sync/previews/
// is outside the app's Tailwind content-scan root, so w-[Npx]/h-[Npx] never
// compile here (confirmed empirically — see learnings). recharts'
// `ResponsiveContainer width="100%" height="100%"` needs a REAL ancestor
// pixel height to measure against; without it the chart silently renders
// at ~0 size.
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="bg-void" style={{ width: 800, height: 200 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  seedTimeseries({
    data: {
      ticks: TICKS,
      imperial_rent: IMPERIAL_RENT,
      consciousness: CONSCIOUSNESS,
      solidarity: SOLIDARITY,
      heat: HEAT,
      wealth: WEALTH,
      biocapacity: BIOCAPACITY,
    },
  });
  return (
    <Frame>
      <TimeseriesChart gameId="g-wayne-county-104" />
    </Frame>
  );
}

export function LoadingState() {
  seedTimeseries({ loading: true });
  return (
    <Frame>
      <TimeseriesChart gameId="g-wayne-county-104" />
    </Frame>
  );
}

export function LoudEmpty() {
  seedTimeseries({
    data: { ticks: [], imperial_rent: [], consciousness: [], solidarity: [], heat: [], wealth: [], biocapacity: [] },
  });
  return (
    <Frame>
      <TimeseriesChart gameId="g-wayne-county-104" />
    </Frame>
  );
}

export function LoudFailure() {
  seedTimeseries({ error: "Timeseries unavailable: HTTP 500" });
  return (
    <Frame>
      <TimeseriesChart gameId="g-wayne-county-104" />
    </Frame>
  );
}
