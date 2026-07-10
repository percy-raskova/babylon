/**
 * EventsFeed preview — store-driven (reads `world.snapshot.events` +
 * `time.autopauseEventIds` from the one zustand store). Each cell seeds
 * the store inside its own wrapper; the card shows only the primary story
 * (cfg.overrides.EventsFeed.cardMode = "single") because all cells share
 * the singleton store on the combined card — per-story captures render
 * each state truly.
 *
 * Event types are real engine EventType values (the classifier maps
 * rupture → critical / bifurcation, solidarity → important / value_transfer,
 * consciousness_shift → informational).
 */
import { EventsFeed, useStore } from "babylon-cockpit";

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
  {
    id: "ev-consciousness-104",
    type: "consciousness_shift",
    tick: 104,
    severity: "informational" as const,
    title: "Consciousness Shift",
    body: "Revolutionary consciousness drifted +0.03 in the reserve army.",
    data: { org_id: "org-block-club-48210" },
  },
];

function Frame({ children }: { children?: unknown }) {
  return <div className="w-[440px] bg-void p-2">{children as never}</div>;
}

export function Populated() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 104, events: TICK_EVENTS } },
    time: { ...s.time, autopauseEventIds: ["ev-rupture-26163"] },
  }));
  return (
    <Frame>
      <EventsFeed />
    </Frame>
  );
}

export function EmptyTick() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 105, events: [] } },
    time: { ...s.time, autopauseEventIds: [] },
  }));
  return (
    <Frame>
      <EventsFeed />
    </Frame>
  );
}

export function NoWorldState() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: null },
    time: { ...s.time, autopauseEventIds: [] },
  }));
  return (
    <Frame>
      <EventsFeed />
    </Frame>
  );
}
