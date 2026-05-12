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

/**
 * Full game state snapshot (Spec 052 §5).
 *
 * Note what is absent: no ``entities`` array, no top-level ``economy``.
 * Classes are derived aggregations, not agents.
 */
export interface GameSnapshot {
  tick: number;
  session_id: string;
  organizations: OrgState[];
  institutions: InstitutionState[];
  territories: TerritoryState[];
  hyperedges: HyperedgeState[];
  edges: EdgeState[];
  events: GameEvent[];
  traps?: TrapDetectionResult;
  derived: DerivedBlock;
  endgame?: EndgameData;
}

/** Trap detection output from the engine. */
export interface TrapDetectionResult {
  liberal: TrapStatus;
  ultra_left: TrapStatus;
  rightist: TrapStatus;
  active_trap: "liberal" | "ultra_left" | "rightist" | null;
  game_over_trap: "liberal" | "ultra_left" | "rightist" | null;
}

/** Status of a single trap detector (Spec 052 §13). */
export interface TrapStatus {
  severity: "none" | "mild" | "moderate" | "severe";
  score: number;
  indicators: string[];
  ticks_at_moderate: number;
}

/** Territory with full visualization fields (Spec 052 §8). */
export interface TerritoryState {
  id: string;
  name: string;
  h3_index: string | null;
  h3_resolution: number;
  county_fips: string;
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

/** Ternary consciousness vector — always sums to 1.0 (Spec 052 §6). */
export interface ConsciousnessVector {
  liberal: number;
  fascist: number;
  revolutionary: number;
}

/** OODA loop profile (Spec 052 §6). */
/** OODA decision-loop profile.
 *  Spec 061 US4 FR-011 (T066, T067): adds ``phase`` — the deterministic
 *  argmax over the four floats — so the frontend can render OODA
 *  badges without re-implementing argmax.
 */
export interface OodaProfile {
  observe: number;
  orient: number;
  decide: number;
  act: number;
  cycle_ticks: number;
  /** Deterministic argmax over observe/orient/decide/act. */
  phase?: "observe" | "orient" | "decide" | "act";
}

/** Organization — the only agent type (Spec 052 §6).
 *  Spec 061 US4 (T071): adds short_name / player_controlled / legitimacy /
 *  opacity. These are optional on the type so US3 (Briefing) can ship
 *  ahead of the full US4 serializer expansion; once US4 backend lands,
 *  the bridge populates them on every snapshot.
 */
export interface OrgState {
  id: string;
  name: string;
  /** Display-only short name (≤16 chars). Derived from `name` when absent. */
  short_name?: string;
  /** True when this org belongs to the requesting session's player. */
  player_controlled?: boolean;
  /** [0, 1] legitimacy under spec 061 FR-011. */
  legitimacy?: number;
  /** [0, 1] opacity (counter-intelligence) under spec 061 FR-011. */
  opacity?: number;
  org_type: OrgType;
  class_character: string;
  cohesion: number;
  cadre_level: number;
  budget: number;
  heat: number;
  territory_ids: string[];
  hyperedge_memberships: string[];
  consciousness: ConsciousnessVector;
  ooda: OodaProfile;
  /** Computed vanguard economy resources (player orgs only). */
  vanguard?: VanguardResources | null;
}

/** Permitted org_type values (Spec 052 §6). */
export type OrgType = "state_apparatus" | "business" | "political_faction" | "civil_society_org";

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

/** Factional composition of an institution (Spec 052 §7). */
export interface FactionalComposition {
  liberal_technocratic: number;
  revanchist_fascist: number;
  institutionalist_bonapartist: number;
}

/** Institution (Spec 052 §7) — not an agent, no OODA. */
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
  factional_composition: FactionalComposition;
}

/** Permitted edge mode values (Spec 052 §10). */
export type EdgeMode =
  | "EXTRACTIVE"
  | "TRANSACTIONAL"
  | "SOLIDARISTIC"
  | "ANTAGONISTIC"
  | "CO_OPTIVE";

/** Dyadic edge between two nodes (Spec 052 §10). */
export interface EdgeState {
  id: string;
  source_id: string;
  target_id: string;
  mode: EdgeMode;
  value_flow: number;
  tension: number;
  repression_flow: number;
}

/** Hyperedge category (Spec 052 §9). */
export type HyperedgeCategory =
  | "contradiction_pair"
  | "institutional_exclusion"
  | "lifecycle_phase";

/** XGI hyperedge — community membership (Spec 052 §9). */
export interface HyperedgeState {
  id: string;
  category: HyperedgeCategory;
  label: string;
  contradiction_partner_id: string | null;
  member_ids: string[];
  material_basis: {
    description: string;
    indicators: string[];
  };
  ideological_dimension: {
    collective_identity_strength: number;
    organizational_vehicles: string[];
  };
}

/** Value tensor (Spec 052 §11). */
export interface ValueTensor {
  departments: string[];
  components: string[];
  values: number[][];
  conservation_residual: number;
}

/** Three-component imperial rent (Spec 052 §11). */
export interface ImperialRent {
  unequal_exchange: number;
  externalized_reproductive: number;
  domestic_shadow: number;
  total: number;
}

/** Class aggregate — derived, not an agent (Spec 052 §11). */
export interface ClassAggregate {
  population: number;
  wage_share: number;
  agitation_proxy: number;
}

/** Derived economy summary (Spec 052 §11). */
export interface EconomyDerived {
  gdp: number;
  gini: number;
  profit_rate: number;
  exploitation_rate: number;
}

/** Per-hyperedge prediction (Spec 052 §11). */
export interface HyperedgePrediction {
  p_acquiescence: number;
  p_revolution: number;
  warsaw_ghetto_corollary_triggered: boolean;
}

/** Engine-computed derived block — read-only cache (Spec 052 §11). */
export interface DerivedBlock {
  value_tensor: ValueTensor;
  imperial_rent: ImperialRent;
  dept_iii_visibility: { g33: number };
  class_aggregates: Record<string, ClassAggregate>;
  economy: EconomyDerived;
  predictions: {
    per_hyperedge: Record<string, HyperedgePrediction>;
  };
}

/** Simulation event. Spec 061 FR-012: severity/title/body/id are
 *  populated by the bridge serializer so v2 pages can render
 *  Priority Dispatch and badges directly from snapshot data.
 */
export interface GameEvent {
  /** Deterministic UUID5 over (session_id, tick, type, data). Stable across replays. */
  id: string;
  type: string;
  tick: number;
  /** Three canonical buckets per FR-012; backend default for unknown types is "informational". */
  severity: "critical" | "warning" | "informational";
  /** Human-readable title derived from `type` ("economic_crisis" → "Economic Crisis"). */
  title: string;
  /** Short prose body. May be the empty string when no narrative is available. */
  body: string;
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

/** Parameters for submitting an action.
 *
 * Spec 040: The ``verb`` field determines the URL path
 * (``/api/games/{id}/actions/{verb}/``) rather than being sent
 * in the request body. The remaining fields become the POST body.
 */
export interface SubmitActionParams {
  org_id: string;
  verb: PlayerVerb;
  target_id: string;
  /** Verb-specific parameters (consciousness_strategy, mode, etc.). */
  [key: string]: unknown;
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
  | "population"
  | "profit_rate"
  | "exploitation_rate"
  | "occ"
  | "imperial_rent"
  | "org_presence";

/** Valid administrative framing levels for multi-scale spatial rendering. */
export type AdminLevel = "state" | "county" | "cz" | "bea_ea" | "msa" | "hex";

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
  linkedEntityType: "territory" | "organization" | "institution" | "hyperedge" | null;
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
  entityType: "overview" | "territory" | "organization" | "institution" | "hyperedge";
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

// ---------------------------------------------------------------------------
// Multi-Scale Spatial Rendering Types
// ---------------------------------------------------------------------------

/** Org-network graph payload from /api/games/{id}/orgs/network/. */
export interface OrgNetworkPayload {
  tick: number;
  nodes: OrgNetworkNode[];
  edges: OrgNetworkEdge[];
}

/** Node in the org-network graph. */
export interface OrgNetworkNode {
  id: string;
  type: "organization" | "institution" | "territory";
  attributes: Record<string, unknown>;
}

/** Edge in the org-network graph. */
export interface OrgNetworkEdge {
  source: string;
  target: string;
  mode: string;
  attributes: Record<string, unknown>;
}

/** Hypergraph community payload from /api/games/{id}/hypergraph/communities/. */
export interface HypergraphPayload {
  tick: number;
  hyperedges: HypergraphCommunity[];
}

/** Single hyperedge community. */
export interface HypergraphCommunity {
  id: string;
  community_type: string;
  category: string;
  members: string[];
}

/** Infrastructure network payload from /api/games/{id}/infrastructure/. */
export interface InfrastructurePayload {
  tick: number;
  nodes: InfrastructureNode[];
  edges: InfrastructureEdge[];
}

/** Infrastructure hub node. */
export interface InfrastructureNode {
  id: string;
  type: string;
  coordinates: [number, number];
  attributes: Record<string, unknown>;
}

/** Infrastructure corridor edge. */
export interface InfrastructureEdge {
  id: string;
  geometry: unknown;
  conductance: number;
  type: string;
}

/** Aggregated admin-level feature from map snapshot. */
export interface AdminFeatureProperties {
  group_key: string;
  group_name: string;
  group_level: AdminLevel;
  hex_count: number;
  county_fips: string;
  state_fips: string;
  state_name: string;
  cz_id: string;
  cz_name: string;
  bea_ea_code: string;
  bea_ea_name: string;
  msa_code: string;
  msa_name: string;
  heat: number;
  consciousness: number;
  wealth: number;
  rent: number;
  biocapacity: number;
  population: number;
  profit_rate: number;
  exploitation_rate: number;
  occ: number;
  imperial_rent: number;
  org_presence: number;
}
