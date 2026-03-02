/** TypeScript interfaces matching the Django API response schema. */

/** Standard API response envelope. */
export interface ApiResponse<T> {
  status: "ok" | "error";
  data: T;
  tick?: number;
  session_id?: string;
  message?: string;
}

/** Game session summary (from GET /api/games/). */
export interface GameSummary {
  id: string;
  scenario: string;
  current_tick: number;
  status: GameStatus;
  created_at: string;
}

export type GameStatus = "active" | "paused" | "completed" | "abandoned";

/** Full game state snapshot (from GET /api/games/{id}/state/). */
export interface GameSnapshot {
  tick: number;
  session_id: string;
  entities: EntityState[];
  territories: TerritoryState[];
  organizations: OrgState[];
  institutions: InstitutionState[];
  edges: EdgeState[];
  economy: Record<string, unknown>;
  events: GameEvent[];
}

/** Social class entity with full visualization fields. */
export interface EntityState {
  id: string;
  name: string;
  role: string;
  wealth: number;
  consciousness: number;
  national_identity: number;
  agitation: number;
  organization: number;
  repression: number;
  p_acquiescence: number;
  p_revolution: number;
  subsistence: number;
  population: number;
  inequality: number;
  active: boolean;
}

/** Territory with full visualization fields. */
export interface TerritoryState {
  id: string;
  name: string;
  h3_index: string | null;
  heat: number;
  sector_type: string;
  territory_type: string;
  profile: string;
  rent_level: number;
  population: number;
  under_eviction: boolean;
  biocapacity: number;
  host_id: string | null;
  occupant_id: string | null;
}

/** Organization with full visualization fields. */
export interface OrgState {
  id: string;
  name: string;
  org_type: string;
  class_character: string;
  cohesion: number;
  cadre_level: number;
  budget: number;
  heat: number;
  territory_ids: string[];
  consciousness_tendency: string;
}

/** Institution with full visualization fields. */
export interface InstitutionState {
  id: string;
  name: string;
  apparatus_type: string;
  social_function: string;
  class_inscription: string;
  legitimacy: number;
  budget: number;
  housed_org_ids: string[];
  territory_ids: string[];
  hegemonic_fraction: string;
  liberal_technocratic: number;
  revanchist_fascist: number;
  institutionalist_bonapartist: number;
}

/** Relationship edge. */
export interface EdgeState {
  source_id: string;
  target_id: string;
  edge_type: string;
  value_flow: number;
  tension: number;
  solidarity_strength: number;
}

/** Simulation event. */
export interface GameEvent {
  type: string;
  tick: number;
  data: Record<string, unknown>;
}

/** Available action for an organization. */
export interface AvailableAction {
  org_id: string;
  verb: string;
  action_type?: string;
  targets?: string[];
  cost?: number;
}

/** Pending player action. */
export interface PendingAction {
  id: number;
  org_id: string;
  verb: string;
  action_type?: string;
  target_id?: string;
  tick: number;
}

/** Action result from tick resolution. */
export interface ActionResultData {
  org_id: string;
  action_type: string;
  target_id?: string;
  initiative_score: number;
  action_cost: number;
  success: boolean;
  consciousness_delta?: number;
  heat_delta?: number;
  details?: Record<string, unknown>;
}

/** Parameters for submitting an action. */
export interface SubmitActionParams {
  org_id: string;
  verb: string;
  action_type?: string;
  target_id?: string;
  target_community?: string;
  params_json?: Record<string, unknown>;
}

/** Parameters for creating a new game. */
export interface CreateGameParams {
  scenario: string;
  config?: Record<string, unknown>;
  defines?: Record<string, unknown>;
  rng_seed?: number;
}

/** Auth state from /accounts/whoami/. */
export interface AuthState {
  is_authenticated: boolean;
  id?: number;
  username?: string;
}

/** Map layer type for hex visualization. */
export type MapLayer =
  | "heat"
  | "consciousness"
  | "wealth"
  | "rent"
  | "biocapacity"
  | "population";
