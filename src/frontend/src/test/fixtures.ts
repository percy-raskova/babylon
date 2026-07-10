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
  CommunityEntry,
  CommunitiesDashboardPayload,
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
