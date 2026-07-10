/**
 * Outliner preview — the left nav's three collapsible sections
 * (Organizations / Communities / Factions), each built from
 * OutlinerSection + OutlinerRow. Store-driven: orgs come off
 * `world.snapshot.organizations`, communities off
 * `panels.communities.data`, factions off `panels.map.data`'s
 * balkanization block (MapPanel owns that panel's fetch lifecycle in the
 * real shell — this preview seeds the data directly instead).
 *
 * Two gotchas worked around here (both written up in
 * .design-sync/learnings/shell.md):
 *  1. Width is an inline `style`, not a Tailwind arbitrary-value class —
 *     Tailwind's content scan never walks `.design-sync/previews/`, so a
 *     unique `w-[300px]` class there compiles to nothing. `<nav>`'s own
 *     content is list-driven (no chart/canvas), so unlike MapPanel/
 *     BottomStrip it renders fine at its natural content height without
 *     any forced-height wrapper.
 *  2. `communities.fetch` / `map.fetch` are overridden to no-ops — both
 *     panels' mount effects fire against the capture harness's static
 *     file server (a real HTTP 404); harmless here since `Outliner` never
 *     reads either panel's `.error`, but a no-op keeps every cell fully
 *     deterministic.
 *
 * Card shows the primary story only (needs cfg.overrides.Outliner =
 * {cardMode:"single", primaryStory:"Populated"}).
 */
import { Outliner, useStore } from "babylon-cockpit";

const ORGANIZATIONS = [
  {
    id: "org-uaw-local-600",
    name: "UAW Local 600",
    short_name: "UAW Local 600",
    player_controlled: true,
    org_type: "civil_society_org",
    class_character: "proletarian",
    cohesion: 0.68,
    cadre_level: 0.42,
    budget: 82.0,
    heat: 0.35,
    territory_ids: ["territory-detroit-mi"],
    hyperedge_memberships: ["hx-new-afrikan"],
    consciousness: { liberal: 0.12, fascist: 0.03, revolutionary: 0.85 },
    ooda: { observe: 0.6, orient: 0.55, decide: 0.7, act: 0.75, cycle_ticks: 1 },
  },
  {
    id: "org-detroit-pd",
    name: "Detroit Police Department",
    short_name: "Detroit PD",
    player_controlled: false,
    org_type: "state_apparatus",
    class_character: "repressive_apparatus",
    cohesion: 0.8,
    cadre_level: 0.1,
    budget: 340.0,
    heat: 0.6,
    territory_ids: ["territory-detroit-mi"],
    hyperedge_memberships: [],
    consciousness: null,
    ooda: { observe: 0.7, orient: 0.5, decide: 0.6, act: 0.65, cycle_ticks: 1 },
  },
];

const COMMUNITIES = [
  {
    id: "comm-uaw-solidarity",
    member_ids: ["org-uaw-local-600"],
    member_count: 340,
    dominant_role: "proletariat",
    avg_consciousness: 0.62,
    total_solidarity_strength: 4.8,
  },
  {
    id: "comm-eastside-petite-bourg",
    member_ids: [],
    member_count: 58,
    dominant_role: "petite_bourgeoisie",
    avg_consciousness: 0.22,
    total_solidarity_strength: 0.9,
  },
];

const FACTIONS = [
  { id: "FAC_DECOLONIAL", colonial_stance: "abolish", is_settler_formation: false },
  { id: "FAC_LOYALIST", colonial_stance: "uphold", is_settler_formation: true },
];

function noopPanel(data: unknown) {
  return { data, loading: false, error: null, fetch: async () => {} };
}

function mapPanelWithFactions() {
  return noopPanel({
    type: "FeatureCollection",
    features: [],
    metadata: { balkanization: { factions: FACTIONS, sovereigns: [], territory_influence: [] } },
  });
}

function Frame({ children }: { children?: unknown }) {
  return (
    <div style={{ width: 300 }} className="bg-void p-2">
      {children as never}
    </div>
  );
}

export function Populated() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 104, organizations: ORGANIZATIONS, events: [] } },
    panels: {
      ...s.panels,
      communities: { ...s.panels.communities, ...noopPanel({ communities: COMMUNITIES }) },
      map: { ...s.panels.map, ...mapPanelWithFactions() },
    },
    map: { ...s.map, selection: { kind: "org", id: "org-uaw-local-600" }, factionFilter: null },
  }));
  return (
    <Frame>
      <Outliner gameId="wayne-county-001" />
    </Frame>
  );
}

export function EmptyBeforeLoad() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 104, organizations: [], events: [] } },
    panels: {
      ...s.panels,
      communities: { ...s.panels.communities, ...noopPanel(null) },
      map: { ...s.panels.map, ...noopPanel(null) },
    },
    map: { ...s.map, selection: null, factionFilter: null },
  }));
  return (
    <Frame>
      <Outliner gameId="wayne-county-001" />
    </Frame>
  );
}

export function FactionFilterActive() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 104, organizations: ORGANIZATIONS, events: [] } },
    panels: {
      ...s.panels,
      communities: { ...s.panels.communities, ...noopPanel({ communities: COMMUNITIES }) },
      map: { ...s.panels.map, ...mapPanelWithFactions() },
    },
    map: { ...s.map, selection: null, factionFilter: "FAC_DECOLONIAL" },
  }));
  return (
    <Frame>
      <Outliner gameId="wayne-county-001" />
    </Frame>
  );
}
