/**
 * BlocFlowLines preview — spec-103 per-bloc Φ-inflow + trade sparklines for
 * the Wire INDEX tab. Store/hook-driven (`useTradeFlows` → `panels.tradeFlows`,
 * fetch-on-mount). The mount effect fires unconditionally when `gameId` is
 * truthy — seeding `data` alone isn't enough, since the effect's real
 * `fetch` would immediately overwrite it with a 404 error from the static
 * preview server (no backend). Each cell also stubs `fetch` to a no-op
 * after seeding, always spreading the existing panel slice first to keep
 * `setMounted` intact. cfg.overrides.BlocFlowLines = {cardMode: "single",
 * primaryStory: "Populated"} recommended (see wire.md) — 4 cells share one
 * store singleton on the non-story combined card.
 */
import { BlocFlowLines, useStore } from "babylon-cockpit";

const TRADE_FLOWS = {
  tick: 104,
  has_data: true,
  blocs: [
    {
      node_id: "bloc-cn",
      label: "China",
      kind: "international" as const,
      latest: { phi_year_inflow: 812.4, bilateral_trade_value: 4210.7, bilateral_trade_tons: 98000, erdi_ratio: 1.34 },
      phi_series: [
        { tick: 100, magnitude: 740 },
        { tick: 101, magnitude: 765 },
        { tick: 102, magnitude: 788 },
        { tick: 103, magnitude: 801 },
        { tick: 104, magnitude: 812.4 },
      ],
      trade_series: [
        { tick: 100, magnitude: 3900 },
        { tick: 101, magnitude: 4020 },
        { tick: 102, magnitude: 4105 },
        { tick: 103, magnitude: 4180 },
        { tick: 104, magnitude: 4210.7 },
      ],
    },
    {
      node_id: "bloc-eu",
      label: "EU Bloc",
      kind: "international" as const,
      latest: { phi_year_inflow: 301.2, bilateral_trade_value: 2870.5, bilateral_trade_tons: 61000, erdi_ratio: 0.92 },
      phi_series: [
        { tick: 100, magnitude: 330 },
        { tick: 101, magnitude: 322 },
        { tick: 102, magnitude: 315 },
        { tick: 103, magnitude: 308 },
        { tick: 104, magnitude: 301.2 },
      ],
      trade_series: [
        { tick: 100, magnitude: 2750 },
        { tick: 101, magnitude: 2790 },
        { tick: 102, magnitude: 2820 },
        { tick: 103, magnitude: 2850 },
        { tick: 104, magnitude: 2870.5 },
      ],
    },
    {
      node_id: "dom-rest",
      label: "Domestic Rest (ex-MI)",
      kind: "domestic_rest" as const,
      latest: { phi_year_inflow: 0, bilateral_trade_value: 1540.9, bilateral_trade_tons: 45210, erdi_ratio: 1.0 },
      phi_series: [],
      trade_series: [
        { tick: 100, magnitude: 1420 },
        { tick: 101, magnitude: 1465 },
        { tick: 102, magnitude: 1498 },
        { tick: 103, magnitude: 1520 },
        { tick: 104, magnitude: 1540.9 },
      ],
    },
  ],
};

function seedTradeFlows(patch: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    panels: {
      ...s.panels,
      tradeFlows: {
        ...s.panels.tradeFlows,
        fetch: async () => {},
        data: null,
        loading: false,
        error: null,
        ...patch,
      },
    },
  }));
}

function Frame({ children }: { children?: unknown }) {
  // Inline style, not a Tailwind arbitrary-value class — see wire.md: the DS
  // package's Tailwind content-scan doesn't cover .design-sync/previews/, so
  // `w-[1000px]` compiles to nothing and silently no-ops. 840px to stay
  // inside the capture pipeline's fixed 900x700 viewport.
  return (
    <div className="bg-void p-2" style={{ width: 840 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  seedTradeFlows({ data: TRADE_FLOWS });
  return (
    <Frame>
      <BlocFlowLines gameId="g-preview-104" />
    </Frame>
  );
}

export function Loading() {
  seedTradeFlows({ loading: true });
  return (
    <Frame>
      <BlocFlowLines gameId="g-preview-104" />
    </Frame>
  );
}

export function EmptyNoData() {
  seedTradeFlows({ data: { tick: 0, has_data: false, blocs: [] } });
  return (
    <Frame>
      <BlocFlowLines gameId="g-preview-104" />
    </Frame>
  );
}

export function LoudFailure() {
  seedTradeFlows({ error: "HTTP 502" });
  return (
    <Frame>
      <BlocFlowLines gameId="g-preview-104" />
    </Frame>
  );
}
