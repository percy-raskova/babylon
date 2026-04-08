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

/** Endgame outcome from tick resolution. */
export interface EndgameData {
  outcome: "REVOLUTIONARY_VICTORY" | "ECOLOGICAL_COLLAPSE" | "FASCIST_CONSOLIDATION";
  tick: number;
  summary: string;
}

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
  endgame?: EndgameData;
  /** Trap detection results (Wayne County scenario). */
  traps?: TrapDetectionResult;
}

/** Trap detection output from the engine. */
export interface TrapDetectionResult {
  liberal: TrapStatus;
  ultra_left: TrapStatus;
  rightist: TrapStatus;
  active_trap: "liberal" | "ultra_left" | "rightist" | null;
  game_over_trap: "liberal" | "ultra_left" | "rightist" | null;
}

/** Status of a single trap detector. */
export interface TrapStatus {
  trap_type: "liberal" | "ultra_left" | "rightist";
  severity: "none" | "mild" | "moderate" | "severe";
  score: number;
  indicators: string[];
  ticks_at_moderate: number;
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
  /** Computed vanguard economy resources (player orgs only). */
  vanguard?: VanguardResources;
}

/** Vanguard Economy resource snapshot for player organizations. */
export interface VanguardResources {
  cadre_labor: number;
  sympathizer_labor: number;
  reputation: number;
  budget: number;
  heat: number;
  max_cadre_labor: number;
  max_sympathizer_labor: number;
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
export type MapLayer = "heat" | "consciousness" | "wealth" | "rent" | "biocapacity" | "population";

/** The 9 constitutional verbs from Article V. */
export type PlayerVerb =
  | "educate"
  | "reproduce"
  | "investigate"
  | "attack"
  | "mobilize"
  | "campaign"
  | "aid"
  | "move"
  | "negotiate";

/** Verb category groupings for the 3x3 grid. */
export type VerbCategory = "build" | "project" | "manage";

// ---------------------------------------------------------------------------
// Feature 042 — Game UI Overhaul types
// ---------------------------------------------------------------------------

/** Analytical perspective that recontextualizes the entire UI. */
export type LensId = "economic" | "political" | "social" | "strategic";

/** Lens definition specifying which UI elements to emphasize. */
export interface LensDefinition {
  id: LensId;
  name: string;
  icon: string;
  primaryLayer: MapLayer;
  emphasizedIndicators: IndicatorId[];
  inspectorPriority: string[];
  defaultChartMetrics: string[];
  description: string;
}

/** Severity tier for event classification. */
export type EventSeverity = "critical" | "important" | "informational";

/** Classified game event with UI-specific metadata. */
export interface ClassifiedEvent {
  id: string;
  event: GameEvent;
  severity: EventSeverity;
  tick: number;
  read: boolean;
  linkedEntityId: string | null;
  linkedEntityType: "territory" | "organization" | "entity" | "institution" | null;
}

/** Grouped notification for display. */
export interface NotificationGroup {
  severity: EventSeverity;
  eventType: string;
  count: number;
  events: ClassifiedEvent[];
  summary: string;
  representativeEvent: ClassifiedEvent;
}

/** Single entry in the drill-down navigation stack. */
export interface BreadcrumbEntry {
  entityType: "overview" | "territory" | "organization" | "entity" | "institution";
  entityId: string | null;
  displayName: string;
  lensId: LensId;
}

/** Identifier for a trackable simulation metric. */
export type IndicatorId =
  | "imperial_rent"
  | "avg_consciousness"
  | "avg_heat"
  | "avg_organization"
  | "total_wealth"
  | "total_population"
  | "org_count"
  | "edge_count"
  | "eviction_rate"
  | "biocapacity_avg"
  | "p_revolution_max"
  | "p_acquiescence_min"
  | "repression_avg"
  | "agitation_avg"
  | "inequality_avg"
  | "solidarity_edges";

/** Threshold configuration for urgency coloring. */
export interface IndicatorThresholds {
  warning: number;
  critical: number;
  /** True when low values are critical (e.g., organization strength). */
  invert: boolean;
}

/** Indicator definition for the top bar. */
export interface IndicatorDefinition {
  id: IndicatorId;
  label: string;
  unit: string;
  format: "decimal" | "percent" | "integer" | "currency";
  thresholds: IndicatorThresholds;
  compute: (snapshot: GameSnapshot) => number;
}

/** Persisted UI preferences (localStorage). */
export interface UIPreferences {
  version: number;
  rightPanelWidth: number;
  rightPanelOpen: boolean;
  bottomPanelHeight: number;
  bottomPanelOpen: boolean;
  bottomTab: "timeseries" | "events" | "graph" | "notifications";
  activeLens: LensId;
  pinnedIndicators: IndicatorId[];
  graphEdgeFilter: string | null;
}

/** Server response for action preview. */
export interface ActionPreviewResult {
  estimated_consciousness_delta: number;
  estimated_heat_delta: number;
  action_point_cost: number;
  success_probability: number;
  affected_territory_ids: string[];
  warnings: string[];
}
