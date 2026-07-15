/**
 * Test data factories — produce realistic game state objects with sensible
 * defaults and override support for targeted testing.
 *
 * Conforms to **Spec 052 — WorldState Snapshot Contract v0**.
 */

import type {
  TerritoryState,
  OrgState,
  InstitutionState,
  EdgeState,
  GameEvent,
  GameSnapshot,
  ActionResultData,
  GameSummary,
  AvailableAction,
  HyperedgeState,
  DerivedBlock,
  ConsciousnessVector,
  OodaProfile,
  FactionalComposition,
  GameSummaryPayload,
  TimeseriesPayload,
  EconomyDashboardPayload,
  CommunityEntry,
  CommunitiesDashboardPayload,
  StateApparatusDashboard,
  EdgeRow,
  EdgesDashboardPayload,
  JournalPayload,
  ClassHistoryPoint,
  ClassHistoryPayload,
  EdgeHistoryPoint,
  EdgeHistoryPayload,
  FieldStateNode,
  FieldStateEdge,
  FieldStatePayload,
  MapHistoryFrame,
  MapHistoryPayload,
} from "@/types/game";
import type { WireFeed, WireStoryIndex } from "@/types/wire";
import { EMPTY_WIRE_FEED } from "@/types/wire";
import type {
  ContradictionSnapshot,
  EndgameState,
  Objective,
  ObjectivesTracker,
} from "@/types/dialectic";
import type { BlocFlowEntry, TradeFlowsPayload } from "@/types/trade";
import type {
  OrgNetworkPayload,
  OrgNetworkNode,
  OrgNetworkEdge,
  OrgNetworkCentrality,
  DoctrineTreePayload,
  DoctrineNode,
} from "@/types/game";

export function makeTerritory(overrides?: Partial<TerritoryState>): TerritoryState {
  return {
    id: "territory-downtown",
    name: "Downtown",
    h3_index: "882a100d2bfffff",
    h3_resolution: 7,
    county_fips: "26163",
    heat: 0.4,
    sector_type: "urban_core",
    territory_type: "metropolitan",
    profile: "HIGH_PROFILE",
    rent_level: 0.6,
    population: 12000,
    under_eviction: false,
    biocapacity: 0.3,
    max_biocapacity: 100,
    habitability: null,
    bifurcation_score: null,
    host_id: null,
    occupant_id: null,
    ...overrides,
  };
}

export function makeConsciousness(overrides?: Partial<ConsciousnessVector>): ConsciousnessVector {
  return {
    liberal: 0.1,
    fascist: 0.05,
    revolutionary: 0.85,
    ...overrides,
  };
}

export function makeOoda(overrides?: Partial<OodaProfile>): OodaProfile {
  return {
    observe: 0.6,
    orient: 0.5,
    decide: 0.7,
    act: 0.8,
    cycle_ticks: 1,
    ...overrides,
  };
}

export function makeOrg(overrides?: Partial<OrgState>): OrgState {
  return {
    id: "org-workers-union",
    name: "Workers Union",
    org_type: "civil_society_org",
    class_character: "proletarian",
    cohesion: 0.75,
    cadre_level: 0.35,
    budget: 15.0,
    heat: 0.3,
    territory_ids: ["territory-downtown"],
    hyperedge_memberships: ["hx-new-afrikan"],
    consciousness: makeConsciousness(),
    ooda: makeOoda(),
    vanguard: {
      cadre_labor: 1.0,
      sympathizer_labor: 4.0,
      reputation: 0.0,
      budget: 100,
      heat: 0,
      max_cadre_labor: 5.0,
      max_sympathizer_labor: 20.0,
    },
    ...overrides,
  };
}

export function makeFactionalComposition(
  overrides?: Partial<FactionalComposition>,
): FactionalComposition {
  return {
    liberal_technocratic: 0.5,
    revanchist_fascist: 0.2,
    institutionalist_bonapartist: 0.3,
    ...overrides,
  };
}

export function makeInstitution(overrides?: Partial<InstitutionState>): InstitutionState {
  return {
    id: "inst-city-hall",
    name: "City Hall",
    apparatus_type: "executive",
    social_function: "governance",
    class_inscription: "bourgeois-democratic",
    legitimacy: 0.6,
    budget: 50.0,
    housed_org_ids: ["org-workers-union"],
    territory_ids: ["territory-downtown"],
    factional_composition: makeFactionalComposition(),
    ...overrides,
  };
}

export function makeEdge(overrides?: Partial<EdgeState>): EdgeState {
  return {
    id: "edge-01",
    source_id: "org-finance-bloc",
    target_id: "org-workers-union",
    mode: "EXTRACTIVE",
    value_flow: 12.5,
    tension: 0.4,
    repression_flow: 0.0,
    ...overrides,
  };
}

export function makeHyperedge(overrides?: Partial<HyperedgeState>): HyperedgeState {
  return {
    id: "hx-new-afrikan",
    category: "contradiction_pair",
    label: "NEW_AFRIKAN",
    contradiction_partner_id: "hx-settler",
    member_ids: ["org-workers-union", "territory-downtown"],
    material_basis: {
      description: "Structural position under settler-colonial capital accumulation",
      indicators: ["residential_segregation", "wealth_gap"],
    },
    ideological_dimension: {
      collective_identity_strength: 0.55,
      organizational_vehicles: ["org-workers-union"],
    },
    ...overrides,
  };
}

export function makeDerived(overrides?: Partial<DerivedBlock>): DerivedBlock {
  return {
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
      proletariat: { population: 850000, wage_share: 0.38, agitation_proxy: 0.2 },
      labor_aristocracy: { population: 210000, wage_share: 0.28, agitation_proxy: 0.05 },
      petite_bourgeoisie: { population: 320000, wage_share: 0.18, agitation_proxy: 0.08 },
      bourgeoisie: { population: 45000, wage_share: 0.14, agitation_proxy: 0.02 },
      lumpenproletariat: { population: 120000, wage_share: 0.02, agitation_proxy: 0.3 },
    },
    economy: {
      gdp: 180.0,
      gini: 0.62,
      profit_rate: 0.18,
      exploitation_rate: 0.55,
    },
    predictions: {
      per_hyperedge: {
        "hx-new-afrikan": {
          p_acquiescence: 0.55,
          p_revolution: 0.18,
          warsaw_ghetto_corollary_triggered: false,
        },
      },
    },
    ...overrides,
  };
}

export function makeEvent(overrides?: Partial<GameEvent>): GameEvent {
  return {
    id: "test-event-fixture",
    type: "EXTRACTION",
    tick: 1,
    severity: "informational",
    title: "Extraction",
    body: "",
    data: { source_id: "org-finance-bloc", amount: 5.0 },
    ...overrides,
  };
}

export function makeSnapshot(overrides?: Partial<GameSnapshot>): GameSnapshot {
  return {
    tick: 1,
    session_id: "test-session-001",
    organizations: [makeOrg()],
    institutions: [makeInstitution()],
    territories: [
      makeTerritory(),
      makeTerritory({
        id: "territory-suburbs",
        name: "Suburbs",
        h3_index: "882a100d2cfffff",
        heat: 0.1,
        profile: "LOW_PROFILE",
        sector_type: "residential",
        population: 30000,
      }),
    ],
    hyperedges: [makeHyperedge()],
    edges: [
      makeEdge(),
      makeEdge({
        id: "edge-02",
        source_id: "org-workers-union",
        target_id: "territory-downtown",
        mode: "SOLIDARISTIC",
        value_flow: 3.0,
        repression_flow: 0.0,
      }),
    ],
    events: [makeEvent()],
    derived: makeDerived(),
    ...overrides,
  };
}

export function makeActionResult(overrides?: Partial<ActionResultData>): ActionResultData {
  return {
    org_id: "org-workers-union",
    action_type: "educate",
    target_id: "org-workers-union",
    initiative_score: 0.75,
    action_cost: 3.0,
    success: true,
    consciousness_delta: 0.05,
    heat_delta: 0.02,
    ...overrides,
  };
}

export function makeGameSummary(overrides?: Partial<GameSummary>): GameSummary {
  return {
    id: "game-001",
    scenario: "default",
    current_tick: 5,
    status: "active",
    created_at: "2026-03-01T12:00:00Z",
    ...overrides,
  };
}

export function makeAvailableAction(overrides?: Partial<AvailableAction>): AvailableAction {
  return {
    org_id: "org-workers-union",
    verb: "educate",
    targets: ["org-workers-union", "territory-downtown"],
    cost: 3,
    ...overrides,
  };
}

/** Wayne County scenario fixture with vanguard resources and traps. */
export function makeWayneCountySnapshot(overrides?: Partial<GameSnapshot>): GameSnapshot {
  return makeSnapshot({
    session_id: "wayne-county-001",
    organizations: [
      makeOrg({
        id: "ORG001",
        name: "Wayne County Organizing Committee",
        org_type: "civil_society_org",
        class_character: "proletarian",
        cohesion: 0.5,
        cadre_level: 0.1,
        budget: 100.0,
        heat: 0.0,
        territory_ids: [],
        hyperedge_memberships: ["hx-new-afrikan"],
        consciousness: makeConsciousness({ liberal: 0.05, fascist: 0.02, revolutionary: 0.93 }),
        ooda: makeOoda(),
        vanguard: {
          cadre_labor: 1.0,
          sympathizer_labor: 4.0,
          reputation: 0.0,
          budget: 100.0,
          heat: 0.0,
          max_cadre_labor: 1.0,
          max_sympathizer_labor: 5.0,
        },
      }),
    ],
    traps: {
      liberal: {
        severity: "none",
        score: 0,
        indicators: [],
        ticks_at_moderate: 0,
      },
      ultra_left: {
        severity: "none",
        score: 0,
        indicators: [],
        ticks_at_moderate: 0,
      },
      rightist: {
        severity: "none",
        score: 0,
        indicators: [],
        ticks_at_moderate: 0,
      },
      active_trap: null,
      game_over_trap: null,
    },
    ...overrides,
  });
}

// ---------------------------------------------------------------------------
// Spec 110 B3 — cockpit dashboard payload factories (spec-109 A4 endpoints)
// ---------------------------------------------------------------------------

/** GET /api/games/{id}/summary/ payload — see `EngineBridge.get_game_summary`. */
export function makeGameSummaryPayload(
  overrides?: Partial<GameSummaryPayload>,
): GameSummaryPayload {
  return {
    tick: 1,
    imperial_rent: 12.5,
    avg_consciousness: 0.4,
    population_total: 42000,
    exploitation_rate: 0.3,
    profit_rate: 0.18,
    org_count: 1,
    class_count: 4,
    event_counts: { critical: 0, warning: 0, informational: 0 },
    ...overrides,
  };
}

/** GET /api/games/{id}/timeseries/ payload — see `EngineBridge.get_game_timeseries`. */
export function makeTimeseriesPayload(overrides?: Partial<TimeseriesPayload>): TimeseriesPayload {
  return {
    ticks: [0, 1],
    imperial_rent: [10, 12.5],
    consciousness: [0.3, 0.4],
    solidarity: [1, 1],
    heat: [0.2, 0.25],
    wealth: [100, 105],
    biocapacity: [0.5, 0.5],
    ...overrides,
  };
}

/** GET /api/games/{id}/economy/ payload — see `EngineBridge.get_economy_dashboard`. */
export function makeEconomyDashboardPayload(
  overrides?: Partial<EconomyDashboardPayload>,
): EconomyDashboardPayload {
  return {
    tick: 1,
    has_data: true,
    value_produced: 100,
    rent_extracted: 20,
    exploitation_rate: 0.2,
    profit_rate: null,
    occ: null,
    imperial_rent_pool: 50,
    current_super_wage_rate: 1.2,
    wage_flow_total: 30,
    tribute_flow_total: 5,
    wealth_by_class_role: { periphery_proletariat: 40, core_bourgeoisie: 60 },
    county_flow: { year: null, phi_accrued_this_year: null, wage_accrued_this_year: null },
    ...overrides,
  };
}

/** GET /api/games/{id}/journal/ payload — full cross-tick event history. */
export function makeJournalPayload(overrides?: Partial<JournalPayload>): JournalPayload {
  return {
    events: [],
    ...overrides,
  };
}

/** One point of GET /api/games/{id}/node/{entityId}/history/'s `history`
 *  array (Wave 2 W2.5a) — a social_class node's per-tick survival calculus. */
export function makeClassHistoryPoint(overrides?: Partial<ClassHistoryPoint>): ClassHistoryPoint {
  return {
    tick: 1,
    p_acquiescence: 0.6,
    p_revolution: 0.2,
    ...overrides,
  };
}

/** GET /api/games/{id}/node/{entityId}/history/ payload (Wave 2 W2.5a). */
export function makeClassHistoryPayload(
  overrides?: Partial<ClassHistoryPayload>,
): ClassHistoryPayload {
  return {
    class_id: "C002",
    history: [],
    ruptures: [],
    ...overrides,
  };
}

/** One `history[]` entry of GET /api/games/{id}/edge/{entityId}/history/ (audit Wave 4 straggler, task #76). */
export function makeEdgeHistoryPoint(overrides?: Partial<EdgeHistoryPoint>): EdgeHistoryPoint {
  return {
    tick: 0,
    weight: 1.0,
    solidarity: null,
    tension: 0.0,
    ...overrides,
  };
}

/** GET /api/games/{id}/edge/{entityId}/history/ payload (audit Wave 4 straggler, task #76). */
export function makeEdgeHistoryPayload(
  overrides?: Partial<EdgeHistoryPayload>,
): EdgeHistoryPayload {
  return {
    edge_id: "C001->C004",
    history: [],
    ...overrides,
  };
}

/** One `nodes[]` entry of GET /api/games/{id}/field_state/ (Wave 3 R1/R2a). */
export function makeFieldStateNode(overrides?: Partial<FieldStateNode>): FieldStateNode {
  return {
    id: "C001",
    name: "Worker",
    ...overrides,
  };
}

/** One `edges[]` entry of GET /api/games/{id}/field_state/ (Wave 3 §11's gradient-wind lens). */
export function makeFieldStateEdge(overrides?: Partial<FieldStateEdge>): FieldStateEdge {
  return {
    source: "C001",
    target: "C002",
    source_territory: "territory-downtown",
    target_territory: "territory-suburbs",
    field: "exploitation",
    gradient: 0.3,
    ...overrides,
  };
}

/**
 * GET /api/games/{id}/field_state/ payload. Defaults to the honest
 * empty-but-well-formed shape the stub bridge always returns (`nodes: []`,
 * `edges: []`, both graph-level attrs `null`) — see `FieldStatePayload`'s
 * docstring for why that is also the COMMON case on real games today
 * (R1b altitude gap), not just the stub.
 */
export function makeFieldStatePayload(overrides?: Partial<FieldStatePayload>): FieldStatePayload {
  return {
    tick: 1,
    nodes: [],
    edges: [],
    principal_field: null,
    dialectical_regime: null,
    ...overrides,
  };
}

/** One `frames[]` entry of GET /api/games/{id}/map/history/ (Program 17 Wave 3, Frontend-W3R3). */
export function makeMapHistoryFrame(overrides?: Partial<MapHistoryFrame>): MapHistoryFrame {
  return {
    tick: 1,
    values: { "26163": 0.4 },
    ...overrides,
  };
}

/**
 * GET /api/games/{id}/map/history/ payload — defaults to the honest
 * empty-but-well-formed shape (mirrors `stub_bridge.py::get_map_history`'s
 * `frames: []`); tests needing real frames override with `server.use()` or
 * pass `frames` directly.
 */
export function makeMapHistoryPayload(overrides?: Partial<MapHistoryPayload>): MapHistoryPayload {
  return {
    metric: "heat",
    from_tick: 0,
    to_tick: 0,
    capped: false,
    frames: [],
    ...overrides,
  };
}

/** One entry of GET /api/games/{id}/communities/'s `communities` array. */
export function makeCommunityEntry(overrides?: Partial<CommunityEntry>): CommunityEntry {
  return {
    id: "comm-1",
    member_ids: ["org-workers-union"],
    member_count: 5,
    dominant_role: "proletariat",
    avg_consciousness: 0.4,
    total_solidarity_strength: 2,
    ...overrides,
  };
}

/** GET /api/games/{id}/communities/ payload. */
export function makeCommunitiesDashboardPayload(
  overrides?: Partial<CommunitiesDashboardPayload>,
): CommunitiesDashboardPayload {
  return {
    communities: [makeCommunityEntry()],
    ...overrides,
  };
}

/**
 * GET /api/games/{id}/state-apparatus/ payload (spec-111 C2). Defaults
 * mirror the real wayne_county contract: the seeded Detroit Police
 * Department (`ORG002`, a `state_apparatus` org — not player-controlled, so
 * `vanguard: null`), no state actions fired yet (honest at tick 0), and no
 * state finances seeded (no scenario ships `WorldState.state_finances`).
 */
export function makeStateApparatusDashboard(
  overrides?: Partial<StateApparatusDashboard>,
): StateApparatusDashboard {
  return {
    tick: 0,
    organizations: [
      makeOrg({
        id: "ORG002",
        name: "Detroit Police Department",
        org_type: "state_apparatus",
        class_character: "state",
        budget: 40,
        heat: 0.1,
        territory_ids: [],
        hyperedge_memberships: [],
        vanguard: null,
      }),
    ],
    org_count: 1,
    total_repression_budget: 40,
    total_heat: 0.1,
    state_finances: {},
    recent_actions: [],
    ...overrides,
  };
}

/** One `EdgeRow` (see `_edge_row` in `engine_bridge.py`). */
export function makeEdgeRow(overrides?: Partial<EdgeRow>): EdgeRow {
  return {
    source_id: "org-finance-bloc",
    target_id: "org-workers-union",
    edge_type: "exploitation",
    edge_mode: null,
    value_flow: 12.5,
    tension: 0.4,
    ...overrides,
  };
}

/**
 * GET /api/games/{id}/edges/ payload (spec-111 C2). Defaults mirror the
 * real wayne_county contract cited in
 * `tests/unit/web/test_edges_dashboard.py`: 495 total edges split across
 * the seeded relation types (summing back to `total_edges`, matching the
 * backend's own `sum(counts.values()) == total_edges` invariant), one
 * SOLIDARITY edge at strength 0.05 (the seeded Detroit prole <-> Dearborn
 * workers edge), and an honestly-empty `counts_by_mode` (tick 0, before
 * `EdgeTransitionSystem` has run).
 */
export function makeEdgesDashboard(
  overrides?: Partial<EdgesDashboardPayload>,
): EdgesDashboardPayload {
  return {
    tick: 0,
    total_edges: 495,
    counts_by_type: { exploitation: 200, wages: 150, solidarity: 50, tenancy: 95 },
    counts_by_mode: {},
    top_by_tension: [makeEdgeRow({ tension: 0.82, value_flow: 40 })],
    top_by_value_flow: [makeEdgeRow({ tension: 0.4, value_flow: 500 })],
    solidarity_strength_stats: { count: 1, avg: 0.05, min: 0.05, max: 0.05 },
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Spec 110 B5 — takeover-surface payload factories (Wire/Dialectic/Chronicle
// /Objectives + the Wire Index tab's trade-flows lines).
// ---------------------------------------------------------------------------

/** One entry of GET /api/games/{id}/wire/'s `index` array. */
export function makeWireStoryIndex(overrides?: Partial<WireStoryIndex>): WireStoryIndex {
  return {
    id: "journal-1",
    tick: 5,
    slug: "UPRISING · HAMTRAMCK",
    hed: {
      c: "Authorities Report Civil Disturbance in Hamtramck",
      l: "WORKERS ROSE UP IN HAMTRAMCK",
      i: "CIVIL DISTURBANCE // HAMTRAMCK",
    },
    coverage: ["c", "l", "i"],
    severity: "critical",
    ...overrides,
  };
}

/** GET /api/games/{id}/wire/ payload — see `useWire`. */
export function makeWireFeed(overrides?: Partial<WireFeed>): WireFeed {
  return {
    ...EMPTY_WIRE_FEED,
    meta: { ...EMPTY_WIRE_FEED.meta, tick: 5, session: "wayne-county-001" },
    index: [makeWireStoryIndex()],
    euphemisms: {
      disturbance: {
        c: "civil disturbance",
        l: "UPRISING",
        filter: "ideology",
        note: "Framing a political act as a public-order issue erases the grievance.",
      },
    },
    story: {
      id: "journal-1",
      tick: 5,
      location: "Hamtramck",
      time_local: "",
      continental: {
        brand: "CONTINENTAL",
        monogram: "C•N",
        kicker: "NATIONAL",
        hed: "Authorities Report Civil Disturbance in Hamtramck",
        dek: "Law enforcement officials say a civil disturbance was brought under control.",
        byline: "By Continental Staff",
        paragraphs: [
          ["Hamtramck — ", { euph: "disturbance", text: "civil disturbance" }, { sup: 1 }],
        ],
        bibliography: [
          {
            n: 1,
            src: "DHS Office of Public Affairs",
            kind: "press release",
            id: "DHS-OPA-001",
            chunk: "chunk_001",
            sim: 0.91,
          },
        ],
      },
      liberated: {
        brand: "FREE SIGNAL",
        callsign: "WCLF-PIRATE-887",
        operator: "RASKOVA-2",
        hed: "WORKERS ROSE UP IN HAMTRAMCK",
        pre: "[ BEGIN TRANSMISSION ]",
        post: "[ END TRANSMISSION ]",
        paragraphs: [
          {
            body: ["THE STREET HELD IN HAMTRAMCK."],
            margin: {
              ref: "WITNESS-001",
              chunk: "chunk_wit_001",
              note: "front-line timestamp confirmed",
            },
          },
        ],
      },
      intel: {
        classification: "TS//SI//NOFORN",
        cable_id: "0005-A",
        origin: "FBI/HSI JOINT TASKFORCE",
        routing: ["DHS/I&A"],
        caveat: "HANDLE VIA COMINT CHANNELS ONLY",
        subj: "CIVIL DISTURBANCE",
        fields: [["EVENT", "DISTURBANCE / DETAIN"]],
        assessment: ["Action timed to suppress labor coordination."],
        refs: [{ tag: "CHUNK", id: "chunk_sigint_001", sim: 0.95, src: "SIGINT capture" }],
        distribution: "NOFORN · 30D RETAIN",
      },
    },
    filters: EMPTY_WIRE_FEED.filters.map((f, i) => (i === 4 ? { ...f, hits: 2 } : f)),
    ...overrides,
  };
}

/** GET /api/games/{id}/contradiction/ payload — see `useContradiction`. */
export function makeContradictionSnapshot(
  overrides?: Partial<ContradictionSnapshot>,
): ContradictionSnapshot {
  return {
    tick: 5,
    regime: "crisis",
    oppositions: [
      { key: "capital_labor", gap: 0.71, rate: 0.03, is_principal: true, leading_pole: "b" },
      { key: "imperial", gap: 0.42, rate: -0.01, is_principal: false, leading_pole: "a" },
    ],
    principal_key: "capital_labor",
    frame: {
      principal: {
        id: "capital_labor",
        aspect_a: "Labor",
        aspect_b: "Capital",
        principal_aspect: "b",
        intensity: 0.71,
        aspect_balance: 0.03,
        is_antagonistic: true,
      },
      secondary: {
        id: "imperial",
        aspect_a: "Core",
        aspect_b: "Periphery",
        principal_aspect: "a",
        intensity: 0.42,
        aspect_balance: -0.01,
        is_antagonistic: true,
      },
    },
    ...overrides,
  };
}

/** GET /api/games/{id}/endgame/ payload — see `useEndgame`. */
export function makeEndgameState(overrides?: Partial<EndgameState>): EndgameState {
  return {
    tick: 5,
    outcome: null,
    headline: "",
    summary: "",
    stats: { final_tick: 5, consciousness: 0.42, solidarity_edges: 3, heat: 0.31 },
    ...overrides,
  };
}

/** One entry of GET /api/games/{id}/objectives/'s `objectives` array. */
export function makeObjective(overrides?: Partial<Objective>): Objective {
  return {
    id: "revolution",
    title: "Revolutionary Victory",
    description: "Build mass class consciousness and solidarity edges to overthrow the empire.",
    progress: 0.42,
    status: "active",
    category: "revolution",
    ...overrides,
  };
}

/** GET /api/games/{id}/objectives/ payload — see `useObjectives`. */
export function makeObjectivesTracker(overrides?: Partial<ObjectivesTracker>): ObjectivesTracker {
  return {
    tick: 5,
    objectives: [makeObjective()],
    ...overrides,
  };
}

/** One entry of GET /api/games/{id}/trade-flows/'s `blocs` array. */
export function makeBlocFlowEntry(overrides?: Partial<BlocFlowEntry>): BlocFlowEntry {
  return {
    node_id: "bloc-eu",
    label: "European Union",
    kind: "international",
    latest: {
      phi_year_inflow: 12.4,
      bilateral_trade_value: 340.2,
      bilateral_trade_tons: 1200,
      erdi_ratio: 1.1,
    },
    phi_series: [
      { tick: 4, magnitude: 11.8 },
      { tick: 5, magnitude: 12.4 },
    ],
    trade_series: [
      { tick: 4, magnitude: 330.0 },
      { tick: 5, magnitude: 340.2 },
    ],
    ...overrides,
  };
}

/** GET /api/games/{id}/trade-flows/ payload — see `useTradeFlows`. */
export function makeTradeFlowsPayload(overrides?: Partial<TradeFlowsPayload>): TradeFlowsPayload {
  return {
    tick: 5,
    has_data: true,
    blocs: [makeBlocFlowEntry()],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// AW4-R2 — Org-network takeover payload factories (GET
// /api/games/{id}/orgs/network/, see `EngineBridge.get_org_network`).
// ---------------------------------------------------------------------------

/** One `nodes[]` entry. */
export function makeOrgNetworkNode(overrides?: Partial<OrgNetworkNode>): OrgNetworkNode {
  return {
    id: "org-workers-union",
    type: "organization",
    attributes: { name: "Workers Union" },
    ...overrides,
  };
}

/** One `edges[]` entry. */
export function makeOrgNetworkEdge(overrides?: Partial<OrgNetworkEdge>): OrgNetworkEdge {
  return {
    source: "org-workers-union",
    target: "territory-downtown",
    mode: "presence",
    attributes: {},
    ...overrides,
  };
}

/** One `centrality[node_id]` entry. */
export function makeOrgNetworkCentrality(
  overrides?: Partial<OrgNetworkCentrality>,
): OrgNetworkCentrality {
  return {
    degree: 0.5,
    betweenness: 0.2,
    closeness: 0.6,
    ...overrides,
  };
}

/**
 * GET /api/games/{id}/orgs/network/ payload — defaults to the honest
 * empty-but-well-formed shape (mirrors `makeFieldStatePayload`'s precedent:
 * `nodes: []`, `edges: []`, `centrality: {}`, `percolation_ratio: null`).
 * Tests needing a populated network pass real nodes/edges/centrality via
 * overrides, or use `makeOrgNetworkPayload({ ...populated })`.
 */
export function makeOrgNetworkPayload(overrides?: Partial<OrgNetworkPayload>): OrgNetworkPayload {
  return {
    tick: 5,
    nodes: [],
    edges: [],
    centrality: {},
    percolation_ratio: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Doctrine Tree canvas payload factories (GET /api/games/{id}/doctrine-tree/,
// see `EngineBridge.get_doctrine_tree`). Unlike the org-network fixture
// above, this one has no honest "empty" default — the real endpoint always
// serves the full static 11-node MVP tree
// (`src/babylon/data/game/doctrine_tree_mvp.json`), so
// `makeDoctrineTreePayload()` transcribes that same corpus data byte-for-byte
// rather than defaulting to `[]`.
// ---------------------------------------------------------------------------

/** The real 11-node MVP Doctrine Tree, transcribed from
 *  `src/babylon/data/game/doctrine_tree_mvp.json` (single source of truth:
 *  keep in sync if that file changes). */
const DOCTRINE_TREE_NODES: DoctrineNode[] = [
  {
    id: "class_consciousness",
    name: "Class Consciousness",
    tier: 0,
    parents: [],
    description: "Recognition that society is divided into classes with opposing interests.",
    tag_deltas: { class_analysis: 1 },
    cost_tl: 0,
    trunk: null,
    unlocks: [],
    warning: null,
    is_trap: false,
    trap_condition: null,
    narrative: null,
    is_goal: false,
  },
  {
    id: "trade_unionism",
    name: "Trade Unionism",
    tier: 1,
    parents: ["class_consciousness"],
    description: "Organize workers at the point of production.",
    tag_deltas: { mass_link: 2 },
    cost_tl: 25,
    trunk: null,
    unlocks: ["electoral_socialism", "democratic_centralism", "armed_vanguard"],
    warning: null,
    is_trap: false,
    trap_condition: null,
    narrative: null,
    is_goal: false,
  },
  {
    id: "electoral_socialism",
    name: "Electoral Socialism",
    tier: 2,
    parents: ["trade_unionism"],
    description: "Win power through the ballot box.",
    tag_deltas: { mass_link: 2, militancy: -2, class_analysis: -1 },
    cost_tl: 50,
    trunk: "reformist",
    unlocks: ["coalition_politics"],
    warning: "This path leads toward the Liberal Trap.",
    is_trap: false,
    trap_condition: null,
    narrative: null,
    is_goal: false,
  },
  {
    id: "coalition_politics",
    name: "Coalition Politics",
    tier: 3,
    parents: ["electoral_socialism"],
    description: "Build broad alliances with liberals and progressives.",
    tag_deltas: { mass_link: 3, class_analysis: -2 },
    cost_tl: 75,
    trunk: "reformist",
    unlocks: ["liquidationism"],
    warning: null,
    is_trap: false,
    trap_condition: null,
    narrative: null,
    is_goal: false,
  },
  {
    id: "liquidationism",
    name: "Liquidationism",
    tier: 4,
    parents: ["coalition_politics"],
    description: "The revolutionary party dissolves into the mass movement.",
    tag_deltas: { mass_link: 4, class_analysis: -3, militancy: -3 },
    cost_tl: 0,
    trunk: "reformist",
    unlocks: [],
    warning: null,
    is_trap: true,
    trap_condition: "CLASS_ANALYSIS <= 0 AND MILITANCY <= 0",
    narrative:
      '"ELECTORAL SOCIALISM: The Managed Decline"\n\nYou won the election. You hold power.\nAnd nothing changed.\n\nThe banks are still banks. The police still police.\nYou had power. You just couldn\'t use it.\n\nTHE APOCALYPSE CONTINUES, BUT NOW YOU MANAGE IT.',
    is_goal: false,
  },
  {
    id: "democratic_centralism",
    name: "Democratic Centralism",
    tier: 2,
    parents: ["trade_unionism"],
    description: "Freedom of discussion, unity of action.",
    tag_deltas: { class_analysis: 2, mass_link: 1, militancy: 1 },
    cost_tl: 75,
    trunk: "scientific",
    unlocks: ["mass_line"],
    warning: null,
    is_trap: false,
    trap_condition: null,
    narrative: null,
    is_goal: false,
  },
  {
    id: "mass_line",
    name: "Mass Line",
    tier: 3,
    parents: ["democratic_centralism"],
    description: "From the masses, to the masses.",
    tag_deltas: { class_analysis: 1, mass_link: 2 },
    cost_tl: 100,
    trunk: "scientific",
    unlocks: ["united_front"],
    warning: null,
    is_trap: false,
    trap_condition: null,
    narrative: null,
    is_goal: false,
  },
  {
    id: "united_front",
    name: "United Front",
    tier: 4,
    parents: ["mass_line"],
    description: "Unity with all progressive forces against the principal enemy.",
    tag_deltas: { class_analysis: 2, mass_link: 2, militancy: 1 },
    cost_tl: 150,
    trunk: "scientific",
    unlocks: [],
    warning: null,
    is_trap: false,
    trap_condition: null,
    narrative:
      "The Scientific path is complete.\nAll actions receive +10% effectiveness.\nTraps are no longer accessible (CLASS_ANALYSIS too high).",
    is_goal: true,
  },
  {
    id: "armed_vanguard",
    name: "Armed Vanguard",
    tier: 2,
    parents: ["trade_unionism"],
    description: "The revolution will be armed or it will not be.",
    tag_deltas: { militancy: 3, mass_link: -1 },
    cost_tl: 50,
    trunk: "insurrectionist",
    unlocks: ["urban_guerrilla"],
    warning: "This path leads toward isolation.",
    is_trap: false,
    trap_condition: null,
    narrative: null,
    is_goal: false,
  },
  {
    id: "urban_guerrilla",
    name: "Urban Guerrilla",
    tier: 3,
    parents: ["armed_vanguard"],
    description: "The city is the battlefield.",
    tag_deltas: { militancy: 3, mass_link: -2, class_analysis: -1 },
    cost_tl: 75,
    trunk: "insurrectionist",
    unlocks: ["adventurism"],
    warning: null,
    is_trap: false,
    trap_condition: null,
    narrative: null,
    is_goal: false,
  },
  {
    id: "adventurism",
    name: "Adventurism",
    tier: 4,
    parents: ["urban_guerrilla"],
    description: "Actions become ends in themselves.",
    tag_deltas: { militancy: 4, mass_link: -4, class_analysis: -2 },
    cost_tl: 0,
    trunk: "insurrectionist",
    unlocks: [],
    warning: null,
    is_trap: true,
    trap_condition: "MASS_LINK <= 0",
    narrative:
      '"PROPAGANDA OF THE DEED: The Spiral"\n\nYou struck. Again and again.\nAnd the people watched in horror.\n\nNot horror at the State. Horror at YOU.\nYour communiques went unread.\nThe State used your actions to justify everything.\n\nTHE REVOLUTION DIED SO YOUR WAR COULD CONTINUE.',
    is_goal: false,
  },
];

/** One Doctrine Tree node — defaults to the root (`class_consciousness`). */
export function makeDoctrineNode(overrides?: Partial<DoctrineNode>): DoctrineNode {
  return {
    ...(DOCTRINE_TREE_NODES[0] as DoctrineNode),
    ...overrides,
  };
}

/**
 * GET /api/games/{id}/doctrine-tree/ payload — defaults to the real 11-node
 * MVP tree with an honest `acquired_ids: []` and the corpus's starting tag
 * values (Constitution III.11 — no acquisition system is wired yet, so
 * there is no honest "empty" state to default to; the tree itself is always
 * fully present).
 */
export function makeDoctrineTreePayload(
  overrides?: Partial<DoctrineTreePayload>,
): DoctrineTreePayload {
  return {
    root_id: "class_consciousness",
    nodes: DOCTRINE_TREE_NODES,
    acquired_ids: [],
    tags: { class_analysis: 1, mass_link: 1, militancy: 0 },
    theoretical_labor: 0,
    ...overrides,
  };
}
