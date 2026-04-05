/**
 * Test data factories — produce realistic game state objects with sensible
 * defaults and override support for targeted testing.
 */

import type {
  EntityState,
  TerritoryState,
  OrgState,
  InstitutionState,
  EdgeState,
  GameEvent,
  GameSnapshot,
  ActionResultData,
  GameSummary,
  AvailableAction,
} from "@/types/game";

export function makeEntity(overrides?: Partial<EntityState>): EntityState {
  return {
    id: "entity-proletariat",
    name: "Proletariat",
    role: "proletariat",
    wealth: 25.0,
    consciousness: 0.3,
    national_identity: 0.5,
    agitation: 0.2,
    organization: 0.15,
    repression: 0.4,
    p_acquiescence: 0.7,
    p_revolution: 0.1,
    subsistence: 10.0,
    population: 50000,
    inequality: 0.45,
    active: true,
    ...overrides,
  };
}

export function makeTerritory(overrides?: Partial<TerritoryState>): TerritoryState {
  return {
    id: "territory-downtown",
    name: "Downtown",
    h3_index: "882a100d2bfffff",
    heat: 0.4,
    sector_type: "INDUSTRIAL",
    territory_type: "URBAN",
    profile: "HIGH_PROFILE",
    rent_level: 0.6,
    population: 12000,
    under_eviction: false,
    biocapacity: 0.3,
    host_id: null,
    occupant_id: null,
    ...overrides,
  };
}

export function makeOrg(overrides?: Partial<OrgState>): OrgState {
  return {
    id: "org-workers-union",
    name: "Workers Union",
    org_type: "POLITICAL_FACTION",
    class_character: "proletariat",
    cohesion: 0.75,
    cadre_level: 2,
    budget: 15.0,
    heat: 0.3,
    territory_ids: ["territory-downtown"],
    consciousness_tendency: "revolutionary",
    ...overrides,
  };
}

export function makeInstitution(overrides?: Partial<InstitutionState>): InstitutionState {
  return {
    id: "inst-city-hall",
    name: "City Hall",
    apparatus_type: "RSA",
    social_function: "governance",
    class_inscription: "bourgeoisie",
    legitimacy: 0.6,
    budget: 50.0,
    housed_org_ids: ["org-workers-union"],
    territory_ids: ["territory-downtown"],
    hegemonic_fraction: "liberal_technocratic",
    liberal_technocratic: 0.5,
    revanchist_fascist: 0.2,
    institutionalist_bonapartist: 0.3,
    ...overrides,
  };
}

export function makeEdge(overrides?: Partial<EdgeState>): EdgeState {
  return {
    source_id: "entity-proletariat",
    target_id: "entity-bourgeoisie",
    edge_type: "EXPLOITATION",
    value_flow: 12.5,
    tension: 0.4,
    solidarity_strength: 0.0,
    ...overrides,
  };
}

export function makeEvent(overrides?: Partial<GameEvent>): GameEvent {
  return {
    type: "EXTRACTION",
    tick: 1,
    data: { source_id: "entity-bourgeoisie", amount: 5.0 },
    ...overrides,
  };
}

export function makeSnapshot(overrides?: Partial<GameSnapshot>): GameSnapshot {
  return {
    tick: 1,
    session_id: "test-session-001",
    entities: [
      makeEntity(),
      makeEntity({
        id: "entity-bourgeoisie",
        name: "Bourgeoisie",
        role: "bourgeoisie",
        wealth: 200.0,
        consciousness: 0.1,
        p_acquiescence: 0.95,
        p_revolution: 0.01,
        population: 5000,
      }),
    ],
    territories: [
      makeTerritory(),
      makeTerritory({
        id: "territory-suburbs",
        name: "Suburbs",
        h3_index: "882a100d2cfffff",
        heat: 0.1,
        profile: "LOW_PROFILE",
        sector_type: "RESIDENTIAL",
        population: 30000,
      }),
    ],
    organizations: [makeOrg()],
    institutions: [makeInstitution()],
    edges: [
      makeEdge(),
      makeEdge({
        source_id: "entity-proletariat",
        target_id: "territory-downtown",
        edge_type: "TENANCY",
        value_flow: 3.0,
        solidarity_strength: 0.6,
      }),
    ],
    economy: { gdp: 1000, imperial_rent: 50 },
    events: [makeEvent()],
    ...overrides,
  };
}

export function makeActionResult(overrides?: Partial<ActionResultData>): ActionResultData {
  return {
    org_id: "org-workers-union",
    action_type: "educate",
    target_id: "entity-proletariat",
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
    targets: ["entity-proletariat", "entity-bourgeoisie"],
    cost: 3,
    ...overrides,
  };
}

/** Wayne County scenario fixture with vanguard resources and traps. */
export function makeWayneCountySnapshot(overrides?: Partial<GameSnapshot>): GameSnapshot {
  return makeSnapshot({
    session_id: "wayne-county-001",
    entities: [
      makeEntity({
        id: "C001",
        name: "Detroit Proletariat",
        role: "internal_proletariat",
        wealth: 0.15,
        consciousness: 0.1,
        national_identity: 0.2,
        organization: 0.05,
        repression: 0.7,
        population: 640_000,
      }),
      makeEntity({
        id: "C002",
        name: "Suburban Petty Bourgeoisie",
        role: "labor_aristocracy",
        wealth: 0.65,
        consciousness: 0.05,
        national_identity: 0.6,
        organization: 0.3,
        repression: 0.1,
        population: 800_000,
      }),
      makeEntity({
        id: "C003",
        name: "Wayne County Bourgeoisie",
        role: "core_bourgeoisie",
        wealth: 0.9,
        consciousness: 0.01,
        national_identity: 0.8,
        organization: 0.8,
        repression: 0.05,
        population: 50_000,
      }),
      makeEntity({
        id: "C004",
        name: "Dearborn Industrial Workers",
        role: "periphery_proletariat",
        wealth: 0.35,
        consciousness: 0.15,
        national_identity: 0.3,
        organization: 0.15,
        repression: 0.4,
        population: 300_000,
      }),
    ],
    organizations: [
      makeOrg({
        id: "ORG001",
        name: "Wayne County Organizing Committee",
        org_type: "civil_society",
        class_character: "proletarian",
        cohesion: 0.5,
        cadre_level: 0.1,
        budget: 100.0,
        heat: 0.0,
        territory_ids: [],
        consciousness_tendency: "revolutionary",
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
        trap_type: "liberal",
        severity: "none",
        score: 0,
        indicators: [],
        ticks_at_moderate: 0,
      },
      ultra_left: {
        trap_type: "ultra_left",
        severity: "none",
        score: 0,
        indicators: [],
        ticks_at_moderate: 0,
      },
      rightist: {
        trap_type: "rightist",
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
