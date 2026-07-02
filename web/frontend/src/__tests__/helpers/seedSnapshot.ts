/**
 * Store-seeding helper for page tests (spec-061 T101/T102 follow-up).
 *
 * The v2 pages read the live gameStore snapshot (useGameState) since
 * spec-061 US6; the old page tests still asserted @/fixtures/v2-mock-data
 * content rendered directly. This helper carries those same landmark
 * values (tick 42, WCLF player org, the informant dispatch, one enemy
 * org / territory / edge / community) in the LIVE GameSnapshot shape so
 * the assertions test real data flow: store → hook → page.
 */

import { useGameStore } from "@/stores/gameStore";
import type { GameSnapshot, OrgState } from "@/types/game";

const WCLF: OrgState = {
  id: "org-wclf",
  name: "Wayne County Labor Federation",
  short_name: "WCLF",
  player_controlled: true,
  legitimacy: 0.62,
  opacity: 0.4,
  org_type: "political_faction",
  class_character: "proletarian",
  cohesion: 0.55,
  cadre_level: 0.1,
  budget: 420,
  heat: 0.18,
  territory_ids: ["terr-hamtramck"],
  hyperedge_memberships: ["hx-tenants"],
  consciousness: { liberal: 0.3, fascist: 0.1, revolutionary: 0.6 },
  ooda: {
    observe: 0.4,
    orient: 0.3,
    decide: 0.2,
    act: 0.1,
    cycle_ticks: 2,
    phase: "observe",
  },
  vanguard: {
    cadre_labor: 6,
    sympathizer_labor: 14,
    reputation: 0.44,
    budget: 420,
    heat: 0.18,
    max_cadre_labor: 10,
    max_sympathizer_labor: 25,
  },
};

const ENEMY_ORG: OrgState = {
  ...WCLF,
  id: "org-dted",
  name: "Detroit Enforcement Division",
  short_name: "DTED",
  player_controlled: false,
  org_type: "state_apparatus",
  class_character: "bourgeois",
  consciousness: { liberal: 0.5, fascist: 0.4, revolutionary: 0.1 },
  vanguard: null,
};

export const SEEDED_SNAPSHOT: GameSnapshot = {
  tick: 42,
  session_id: "wayne-county-test",
  organizations: [WCLF, ENEMY_ORG],
  institutions: [],
  territories: [
    {
      id: "terr-hamtramck",
      name: "Hamtramck",
      h3_index: "872b2632effffff",
      h3_resolution: 7,
      county_fips: "26163",
      heat: 0.35,
      sector_type: "industrial",
      territory_type: "urban",
      profile: "HIGH_PROFILE",
      rent_level: 0.42,
      population: 28000,
      under_eviction: false,
      biocapacity: 0.7,
      host_id: null,
      occupant_id: null,
    },
  ],
  hyperedges: [
    {
      id: "hx-tenants",
      category: "contradiction_pair",
      label: "Hamtramck Tenants Union",
      contradiction_partner_id: null,
      member_ids: ["org-wclf"],
      material_basis: {
        description: "Shared landlord; rent burden above 40%",
        indicators: ["rent_burden", "eviction_filings"],
      },
      ideological_dimension: {
        collective_identity_strength: 0.58,
        organizational_vehicles: ["tenant council"],
      },
    },
  ],
  edges: [
    {
      id: "edge-1",
      source_id: "org-dted",
      target_id: "org-wclf",
      mode: "ANTAGONISTIC",
      value_flow: 0,
      tension: 0.66,
      repression_flow: 0.2,
    },
  ],
  events: [
    {
      id: "evt-1",
      type: "informant_detected",
      tick: 41,
      severity: "critical",
      title: "Informant detected in Wayne County Labor Federation",
      body: "Counter-intelligence sweep flagged an informant in the WCLF cadre.",
      data: {},
    },
  ],
  derived: {
    value_tensor: {} as GameSnapshot["derived"]["value_tensor"],
    imperial_rent: {} as GameSnapshot["derived"]["imperial_rent"],
    dept_iii_visibility: { g33: 0.3 },
    class_aggregates: {},
    economy: {} as GameSnapshot["derived"]["economy"],
    predictions: { per_hyperedge: {} },
  },
};

/** Seed the game store with the canonical test snapshot. */
export function seedGameStore(snapshot: GameSnapshot = SEEDED_SNAPSHOT): void {
  useGameStore.setState({ snapshot, loading: false, error: null });
}

/** Reset the game store between tests. */
export function resetGameStore(): void {
  useGameStore.setState({ snapshot: null, loading: false, error: null });
}
