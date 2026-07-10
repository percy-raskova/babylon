/**
 * BottomStrip preview — the collapsible Events / Time Series tab strip.
 * Both `EventsFeed` and `TimeseriesChart` stay mounted regardless of
 * which tab is active or whether the strip is collapsed — visibility is
 * CSS-only (see `BottomStrip.tsx`'s docstring) — so every cell seeds
 * both `world.snapshot.events` and `panels.timeseries.data` even when
 * only one is visually on top.
 *
 * Two gotchas worked around here (both written up in
 * .design-sync/learnings/shell.md):
 *  1. Sizing is an inline `style` (`display:"grid"` + explicit
 *     width/height), not Tailwind arbitrary classes — Tailwind's content
 *     scan never walks `.design-sync/previews/`, so a unique `h-[220px]`
 *     or `[&>footer]:h-full` class there compiles to nothing, and the
 *     bare `<footer>` (no intrinsic height outside the real AppShell
 *     grid) collapses to ~0px — recharts' `ResponsiveContainer` then
 *     measures a zero-height parent and renders nothing. `display:grid`
 *     on the wrapper makes its sole child (`<footer>`) stretch to fill
 *     the cell by CSS Grid's own default, with no need to target the
 *     child's tag at all.
 *  2. `timeseries.fetch` is overridden to a no-op: `TimeseriesChart`'s
 *     mount effect always fires `fetchTimeseries(gameId)`, which
 *     resolves against the capture harness's static file server (a real
 *     HTTP 404) — and `TimeseriesChart` checks `error` BEFORE `data`, so
 *     without this override the populated cell would render "HTTP 404"
 *     instead of the chart once that fetch settles.
 *
 * Card shows the primary story only (needs cfg.overrides.BottomStrip =
 * {cardMode:"single", primaryStory:"TimeseriesActive"}).
 */
import { BottomStrip, useStore } from "babylon-cockpit";

const TICK_EVENTS = [
  {
    id: "ev-rupture-26163",
    type: "rupture",
    tick: 104,
    severity: "critical" as const,
    title: "Rupture in Wayne County",
    body: "P(S|R) exceeded P(S|A) for the industrial proletariat.",
    data: { territory_id: "26163" },
  },
  {
    id: "ev-bifurcation-104",
    type: "bifurcation_threshold",
    tick: 104,
    severity: "warning" as const,
    title: "Bifurcation Threshold Crossed",
    body: "Wage collapse routes agitation toward organization, not fascism.",
    data: { territory_id: "26163" },
  },
  {
    id: "ev-solidarity-104",
    type: "solidarity_awakening",
    tick: 104,
    severity: "warning" as const,
    title: "Solidarity Awakening",
    body: "New SOLIDARITY edge: auto workers ↔ tenants union.",
    data: { org_id: "org-uaw-local-600" },
  },
  {
    id: "ev-transfer-104",
    type: "value_transfer",
    tick: 104,
    severity: "informational" as const,
    title: "Value Transfer",
    body: "Imperial rent Φ flowed core-ward along the TRIBUTE edge.",
    data: {},
  },
];

const TIMESERIES = {
  ticks: [100, 101, 102, 103, 104],
  imperial_rent: [78000000, 80100000, 81600000, 83000000, 84213907.42],
  consciousness: [0.33, 0.35, 0.37, 0.39, 0.42],
  solidarity: [0.5, 0.58, 0.62, 0.68, 0.72],
  heat: [0.4, 0.42, 0.45, 0.5, 0.55],
  wealth: [150, 152, 155, 158, 160],
  biocapacity: [0.3, 0.3, 0.29, 0.29, 0.28],
};

function seedTimeseriesPanel(data: Record<string, unknown>) {
  return { data, loading: false, error: null, fetch: async () => {} };
}

function Frame({ children }: { children?: unknown }) {
  return (
    <div style={{ display: "grid", width: 880, height: 220 }} className="bg-void p-2">
      {children as never}
    </div>
  );
}

// Collapsed shows only the header strip — the real AppShell grid shrinks
// this region to 32px when collapsed (see AppShell.tsx's
// `gridTemplateRows`); reusing the 220px expanded Frame here would leave a
// misleading void gap below the header, so this cell gets its own
// realistically-short frame instead.
function CollapsedFrame({ children }: { children?: unknown }) {
  return (
    <div style={{ display: "grid", width: 880, height: 44 }} className="bg-void p-2">
      {children as never}
    </div>
  );
}

export function TimeseriesActive() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 104, events: TICK_EVENTS } },
    panels: { ...s.panels, timeseries: { ...s.panels.timeseries, ...seedTimeseriesPanel(TIMESERIES) } },
    ui: { ...s.ui, bottomStripCollapsed: false, activeDockTab: "timeseries" },
  }));
  return (
    <Frame>
      <BottomStrip gameId="wayne-county-001" />
    </Frame>
  );
}

export function EventsActive() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 104, events: TICK_EVENTS } },
    panels: { ...s.panels, timeseries: { ...s.panels.timeseries, ...seedTimeseriesPanel(TIMESERIES) } },
    ui: { ...s.ui, bottomStripCollapsed: false, activeDockTab: "events" },
  }));
  return (
    <Frame>
      <BottomStrip gameId="wayne-county-001" />
    </Frame>
  );
}

export function Collapsed() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 104, events: TICK_EVENTS } },
    panels: { ...s.panels, timeseries: { ...s.panels.timeseries, ...seedTimeseriesPanel(TIMESERIES) } },
    ui: { ...s.ui, bottomStripCollapsed: true, activeDockTab: "timeseries" },
  }));
  return (
    <CollapsedFrame>
      <BottomStrip gameId="wayne-county-001" />
    </CollapsedFrame>
  );
}

export function EmptyEventsThisTick() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 105, events: [] } },
    panels: {
      ...s.panels,
      timeseries: {
        ...s.panels.timeseries,
        ...seedTimeseriesPanel({
          ticks: [],
          imperial_rent: [],
          consciousness: [],
          solidarity: [],
          heat: [],
          wealth: [],
          biocapacity: [],
        }),
      },
    },
    ui: { ...s.ui, bottomStripCollapsed: false, activeDockTab: "events" },
  }));
  return (
    <Frame>
      <BottomStrip gameId="wayne-county-001" />
    </Frame>
  );
}
