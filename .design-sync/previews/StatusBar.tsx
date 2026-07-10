/**
 * StatusBar preview — top bar's real `/summary/` fields (tick, profit
 * rate, imperial rent Φ, population, alert badges), the takeover-open
 * buttons, and the embedded TimeControls transport. Store-driven: each
 * cell seeds `world.snapshot.tick` + `panels.summary.data` in its own
 * wrapper, always spreading the existing slice so the panel's
 * `fetch`/`setMounted` actions survive.
 *
 * Card shows the primary story only (needs cfg.overrides.StatusBar =
 * {cardMode:"single", primaryStory:"Populated"}) — the singleton store
 * makes multi-cell cards lie; per-story captures grade all three states
 * truly.
 *
 * Two gotchas worked around here (both written up in
 * .design-sync/learnings/shell.md):
 *  1. Width is an inline `style`, not a Tailwind arbitrary-value class —
 *     Tailwind's content scan never walks `.design-sync/previews/`, so a
 *     unique `w-[...]` class there compiles to nothing.
 *  2. `summary.fetch` is overridden to a no-op: `StatusBar`'s mount effect
 *     always fires `fetchSummary(gameId)`, which resolves against the
 *     capture harness's static file server (a real HTTP 404, not a
 *     network error) — harmless here since StatusBar never reads
 *     `panels.summary.error`, but a no-op keeps every cell fully
 *     deterministic regardless of capture timing.
 */
import { StatusBar, useStore } from "babylon-cockpit";

function seedStatusBar(tick: number | null, summary: Record<string, unknown> | null) {
  useStore.setState((s: any) => ({
    world: {
      ...s.world,
      snapshot: tick === null ? null : { tick, events: [] },
      lastTick: tick,
    },
    panels: {
      ...s.panels,
      summary: {
        ...s.panels.summary,
        data: summary,
        loading: false,
        error: null,
        fetch: async () => {},
      },
    },
  }));
}

function Frame({ children }: { children?: unknown }) {
  return (
    <div style={{ width: 1170 }} className="bg-void p-2">
      {children as never}
    </div>
  );
}

export function Populated() {
  seedStatusBar(104, {
    tick: 104,
    imperial_rent: 84213907.42,
    avg_consciousness: 0.42,
    population_total: 1793561,
    exploitation_rate: 0.55,
    profit_rate: 0.142,
    org_count: 12,
    class_count: 5,
    event_counts: { critical: 1, warning: 2, informational: 5 },
  });
  return (
    <Frame>
      <StatusBar gameId="wayne-county-001" />
    </Frame>
  );
}

export function NoAlerts() {
  seedStatusBar(104, {
    tick: 104,
    imperial_rent: 84213907.42,
    avg_consciousness: 0.42,
    population_total: 1793561,
    exploitation_rate: 0.55,
    profit_rate: 0.142,
    org_count: 12,
    class_count: 5,
    event_counts: { critical: 0, warning: 0, informational: 3 },
  });
  return (
    <Frame>
      <StatusBar gameId="wayne-county-001" />
    </Frame>
  );
}

export function HonestNoData() {
  seedStatusBar(null, null);
  return (
    <Frame>
      <StatusBar gameId="wayne-county-001" />
    </Frame>
  );
}
