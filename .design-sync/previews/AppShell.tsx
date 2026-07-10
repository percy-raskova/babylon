/**
 * AppShell preview — the whole cockpit grid, one canonical seeded
 * composition (spec-110 B3 stage 2: five persistent regions + the B5
 * takeover-overlay host). This is the hero card: every store slice the
 * five regions read is seeded here so the shell renders as it would
 * mid-session (tick 104, Wayne County scenario), not as five independent
 * empty panels. `ui.takeover.active` is left at its default `null` so
 * `TakeoverOverlay` renders nothing — per the lane brief, AppShell gets
 * exactly this one cell.
 *
 * Learnings note (see .design-sync/learnings/shell.md): `AppShell`'s root
 * is `h-screen w-screen` (viewport units, not container-relative) — it
 * always fills the ACTUAL capture viewport, ignoring any wrapper `<div>`
 * width, so the "~1200px hero frame" the brief asks for needs
 * `cfg.overrides.AppShell.viewport`, a config.json change outside this
 * file's reach.
 *
 * MapPanel embeds deck.gl + MapLibre (WebGL + external basemap tiles) —
 * per the lane brief this preview does not fight WebGL rendering blank in
 * headless capture; the surrounding chrome is the thing under review.
 *
 * Every seeded panel also overrides `.fetch` to a no-op: each of
 * StatusBar/MapPanel/Outliner/BottomStrip mounts its own docked panel and
 * fires a real fetch against the capture harness's static file server (a
 * real HTTP 404, not a network error) — `TimeseriesChart` (BottomStrip's
 * default tab) checks `panels.timeseries.error` BEFORE `data`, so without
 * this override the hero shot's bottom strip renders "HTTP 404" instead
 * of the chart. See .design-sync/learnings/shell.md.
 */
import { AppShell, useStore } from "babylon-cockpit";

const TERRITORIES = [
  {
    id: "territory-detroit-mi",
    name: "Detroit",
    h3_index: "882a100d2bfffff",
    h3_resolution: 7,
    county_fips: "26163",
    heat: 0.55,
    sector_type: "urban_core",
    territory_type: "metropolitan",
    profile: "HIGH_PROFILE",
    rent_level: 0.62,
    population: 639111,
    under_eviction: true,
    biocapacity: 0.28,
    max_biocapacity: 100,
    habitability: 0.31,
    host_id: null,
    occupant_id: null,
  },
  {
    id: "territory-dearborn-mi",
    name: "Dearborn",
    h3_index: "882a100d2cfffff",
    h3_resolution: 7,
    county_fips: "26163",
    heat: 0.22,
    sector_type: "residential",
    territory_type: "metropolitan",
    profile: "LOW_PROFILE",
    rent_level: 0.4,
    population: 109976,
    under_eviction: false,
    biocapacity: 0.4,
    max_biocapacity: 100,
    habitability: null,
    host_id: null,
    occupant_id: null,
  },
];

const ORGANIZATIONS = [
  {
    id: "org-uaw-local-600",
    name: "UAW Local 600",
    short_name: "UAW Local 600",
    player_controlled: true,
    legitimacy: 0.7,
    opacity: 0.3,
    org_type: "civil_society_org",
    class_character: "proletarian",
    cohesion: 0.68,
    cadre_level: 0.42,
    budget: 82.0,
    heat: 0.35,
    territory_ids: ["territory-detroit-mi"],
    hyperedge_memberships: ["hx-new-afrikan"],
    consciousness: { liberal: 0.12, fascist: 0.03, revolutionary: 0.85 },
    ooda: { observe: 0.6, orient: 0.55, decide: 0.7, act: 0.75, cycle_ticks: 1, phase: "act" },
    vanguard: {
      cadre_labor: 3.2,
      sympathizer_labor: 11.5,
      reputation: 0.4,
      budget: 82.0,
      heat: 0.35,
      max_cadre_labor: 5.0,
      max_sympathizer_labor: 20.0,
    },
  },
  {
    id: "org-detroit-pd",
    name: "Detroit Police Department",
    short_name: "Detroit PD",
    player_controlled: false,
    legitimacy: 0.45,
    opacity: 0.55,
    org_type: "state_apparatus",
    class_character: "repressive_apparatus",
    cohesion: 0.8,
    cadre_level: 0.1,
    budget: 340.0,
    heat: 0.6,
    territory_ids: ["territory-detroit-mi"],
    hyperedge_memberships: [],
    consciousness: null,
    ooda: { observe: 0.7, orient: 0.5, decide: 0.6, act: 0.65, cycle_ticks: 1, phase: "observe" },
  },
];

const EVENTS = [
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

const SNAPSHOT = {
  tick: 104,
  session_id: "wayne-county-001",
  organizations: ORGANIZATIONS,
  institutions: [],
  territories: TERRITORIES,
  hyperedges: [],
  edges: [],
  events: EVENTS,
  derived: {
    value_tensor: {
      departments: ["I", "IIa", "IIb", "III"],
      components: ["c", "v", "s"],
      values: [
        [40.0, 20.0, 12.0],
        [15.0, 10.0, 6.0],
        [8.0, 5.0, 3.0],
        [0.0, 12.0, 4.0],
      ],
      conservation_residual: 0.0,
    },
    imperial_rent: {
      unequal_exchange: 6.2,
      externalized_reproductive: 5.1,
      domestic_shadow: 4.2,
      total: 15.5,
    },
    dept_iii_visibility: { g33: 0.12 },
    class_aggregates: {
      proletariat: { population: 639111, wage_share: 0.36, agitation_proxy: 0.31 },
      bourgeoisie: { population: 18500, wage_share: 0.14, agitation_proxy: 0.02 },
    },
    economy: { gdp: 180.0, gini: 0.62, profit_rate: 0.142, exploitation_rate: 0.55 },
    predictions: { per_hyperedge: {} },
  },
};

export function WayneCountyCockpit() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: SNAPSHOT, lastTick: 104 },
    map: {
      ...s.map,
      lens: { kind: "stance" },
      framing: "county",
      selection: { kind: "org", id: "org-uaw-local-600" },
      factionFilter: null,
    },
    ui: {
      ...s.ui,
      bottomStripCollapsed: false,
      activeDockTab: "timeseries",
      rightDockTab: "actions",
      takeover: { active: null },
    },
    actions: {
      ...s.actions,
      pending: [
        {
          id: "pending-1",
          verb: "educate",
          orgId: "org-uaw-local-600",
          targetId: null,
          submittedAtTick: 104,
        },
      ],
    },
    panels: {
      ...s.panels,
      summary: {
        ...s.panels.summary,
        loading: false,
        error: null,
        fetch: async () => {},
        data: {
          tick: 104,
          imperial_rent: 84213907.42,
          avg_consciousness: 0.42,
          population_total: 1793561,
          exploitation_rate: 0.55,
          profit_rate: 0.142,
          org_count: 2,
          class_count: 5,
          event_counts: { critical: 1, warning: 2, informational: 5 },
        },
      },
      map: {
        ...s.panels.map,
        loading: false,
        error: null,
        fetch: async () => {},
        data: {
          type: "FeatureCollection",
          features: [],
          metadata: {
            balkanization: {
              factions: [
                { id: "FAC_DECOLONIAL", colonial_stance: "abolish", is_settler_formation: false },
                { id: "FAC_LOYALIST", colonial_stance: "uphold", is_settler_formation: true },
              ],
              sovereigns: [],
              territory_influence: [],
            },
          },
        },
      },
      communities: {
        ...s.panels.communities,
        loading: false,
        error: null,
        fetch: async () => {},
        data: {
          communities: [
            {
              id: "comm-uaw-solidarity",
              member_ids: ["org-uaw-local-600"],
              member_count: 340,
              dominant_role: "proletariat",
              avg_consciousness: 0.62,
              total_solidarity_strength: 4.8,
            },
          ],
        },
      },
      timeseries: {
        ...s.panels.timeseries,
        loading: false,
        error: null,
        fetch: async () => {},
        data: {
          ticks: [100, 101, 102, 103, 104],
          imperial_rent: [78000000, 80100000, 81600000, 83000000, 84213907.42],
          consciousness: [0.33, 0.35, 0.37, 0.39, 0.42],
          solidarity: [0.5, 0.58, 0.62, 0.68, 0.72],
          heat: [0.4, 0.42, 0.45, 0.5, 0.55],
          wealth: [150, 152, 155, 158, 160],
          biocapacity: [0.3, 0.3, 0.29, 0.29, 0.28],
        },
      },
    },
  }));
  return <AppShell gameId="wayne-county-001" />;
}
