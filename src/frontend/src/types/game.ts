/** TypeScript interfaces matching the Django API response schema. */

/** Standard API response envelope. */
export interface ApiResponse<T> {
  status: "ok" | "error";
  data: T;
  tick?: number;
  session_id?: string;
  message?: string;
  /**
   * Raw HTTP status code of the underlying response (spec-110 B3). The
   * Django error envelope (`{status:"error", message}`) carries no status
   * code of its own, so callers that must distinguish e.g. 409 (external
   * resolve in flight) from 5xx (loud failure) need this. `undefined` when
   * the request never reached the server (network error).
   */
  http_status?: number;
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

/**
 * Crisis lifecycle phase (mirrors `CrisisPhase` StrEnum,
 * `domain/economics/tick/types.py`). The business-cycle progression a county
 * moves through: NORMAL → ONSET → EARLY → DEEP, then RECOVERY once the profit
 * rate holds above threshold. "In crisis" = onset/early/deep.
 */
export type CrisisPhase = "normal" | "onset" | "early" | "deep" | "recovery";

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
}

/**
 * Spec-070 political-topology extension to the map-snapshot response
 * (spec-093 US3): factions, sovereigns, and per-territory influence,
 * sourced from `GraphProtocol.query_faction_influence_by_territory` /
 * `query_sovereign_claims` / `query_territory_claims`.
 *
 * IMPORTANT: this lives under `GET /api/games/{id}/map/`'s
 * `metadata.balkanization` (`EngineBridge.get_map_snapshot`,
 * `_build_balkanization_block`) — it is NOT part of `GameSnapshot`
 * (`GET .../state/`). `useGameState()`'s `mapData` field is the source;
 * `DeckGLMap` reads `mapData?.metadata?.balkanization`, never
 * `snapshot.balkanization` (that field doesn't exist on the real API).
 *
 * Absent (or `null`) when the session has no balkanization graph data yet
 * (see `specs/093-territory-org-detail/research.md` Q7) — the map lens set
 * degrades to an explicit "no data" legend in that case, never a
 * fabricated fill. Distinct from `hyperedges` (Constitution VIII.9): this
 * block is never derived from, and never renders as, hyperedge/community
 * membership.
 */
export interface MapSnapshotMetadata {
  balkanization?: import("@/components/map/mapLensLayers").BalkanizationBlock | null;
  /**
   * `web/game/map_contract.py`'s `MAP_METRIC_PROPERTIES` — the full list of
   * metric names this `/map/` response's features carry (spec-113 Lane B's
   * `lib/lenses/registry.ts` `availableWhen` reads this to degrade starred
   * lenses honestly before/without a given backend property).
   */
  available_metrics?: string[];
  [key: string]: unknown;
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
  /**
   * Metabolic ceiling (Territory model field). Spec-109 A2: was hardcoded
   * to 100 at the map layer before the serializer carried the real value.
   */
  max_biocapacity?: number;
  /**
   * Spec-070 FR-043 Sovereign-driven metabolic impact — graph-only (not a
   * Territory model field), so it is `null`/absent whenever no live graph
   * was threaded through the bridge or MetabolismSystem never wrote it for
   * this territory (spec-109 A2). Never a fabricated default.
   */
  habitability?: number | null;
  /**
   * Wave 3 R2a discovery: `_serialize_territory` (`web/game/engine_bridge.py`)
   * has been emitting this on every `/state/` snapshot territory row since
   * Program 17 Item 1a's crisis-detector family, read off the graph-only
   * `tick_bifurcation_score` attr (`_territory_graph_attr`,
   * `crisis/bifurcation.py`'s per-county sign convention: −1 revolutionary /
   * +1 fascist, solidarity-*density*-based — NOT the dormant Π₀ topological
   * invariant, see `bifurcation/analysis.py`). This interface never declared
   * it, so no frontend consumer could type-check against it until now
   * (Constitution III.11: `null` before the first year boundary this
   * session produces usable data, never a fabricated 0).
   */
  bifurcation_score?: number | null;
  /**
   * Crisis / business-cycle family (Feature 018 crisis-devaluation, surfaced
   * via Program 17 Item 1a). `_serialize_territory` emits all four on every
   * `/state/` snapshot territory row, read off the graph-only
   * `tick_crisis_phase`/`tick_crisis_duration`/`tick_wage_compression`/
   * `tick_capital_stock` attrs the crisis system writes
   * (`domain/economics/tick/types.py::CrisisState`; registered
   * `SeamScope.TERRITORY`, `sentinels/seam/registry.py:433-484`). This
   * interface never declared them, so no frontend consumer could type-check
   * against them until the CrisisTimeline widget. Honest `null`/absent before
   * the first year-boundary this session produces usable data — the crisis
   * detector runs on the year boundary, never a fabricated default
   * (Constitution III.11).
   *
   * `crisis_phase` is the 5-value lifecycle `CrisisPhase`; `crisis_duration`
   * counts periods in crisis (ONSET–DEEP); `wage_compression` is cumulative
   * in [0,1]; `capital_stock` is the county's absolute K (extensive — sum,
   * don't average, to watch aggregate devaluation).
   */
  crisis_phase?: CrisisPhase | null;
  crisis_duration?: number | null;
  wage_compression?: number | null;
  capital_stock?: number | null;
  /**
   * Wave 5 receptivity pair (Epistemic Horizon Phase 1 honest display):
   * `_serialize_territory` emits all three on every `/state/` snapshot
   * territory row, read off the graph-only `mass_receptivity`/
   * `intel_confidence`/`vision_state` attrs `EpistemicHorizonSystem`
   * writes and `_carry_epistemic_horizon` re-injects post-round-trip.
   * `intel_confidence` deliberately has NO map lens (uniformly 0.1 today,
   * C_p=0 everywhere — see the program report's Phase-1 findings); it is
   * a drill-down/tooltip field only. All three are honest `null` for a
   * tenant-less territory or before the graph has ever been stepped
   * (Constitution III.11 — never a fabricated 0/state).
   */
  mass_receptivity?: number | null;
  intel_confidence?: number | null;
  vision_state?: string | null;
  /**
   * Feature 021 lens pair (System #5 `ReserveArmySystem` / System #10
   * `DispossessionEventSystem`): `_serialize_territory` emits both on every
   * `/state/` snapshot territory row, read off the graph-only
   * `wage_pressure`/`dispossession_intensity` attrs those systems write.
   * Honest `null`/absent whenever the writing system found no reserve-army
   * pressure / no dispossession activity for that territory this tick
   * (Constitution III.11 — never a fabricated 0).
   */
  wage_pressure?: number | null;
  dispossession_intensity?: number | null;
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
  /** Null until the engine computes an org-level ideology distribution —
   *  the backend never fabricates thirds (spec-109 A5, Constitution III.11).
   *  Render a loud "no data" state, not a default. */
  consciousness: ConsciousnessVector | null;
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
  "EXTRACTIVE" | "TRANSACTIONAL" | "SOLIDARISTIC" | "ANTAGONISTIC" | "CO_OPTIVE";

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
  "contradiction_pair" | "institutional_exclusion" | "lifecycle_phase";

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

/** Spec 092: GET /api/games/{id}/journal/ — full cross-tick event history. */
export interface JournalPayload {
  events: GameEvent[];
}

/** Spec 092: GET /api/games/{id}/alerts/ — critical/warning events from the
 *  latest resolved tick (the Tick Resolution screen's alert feed). */
export interface AlertsPayload {
  alerts: GameEvent[];
}

/**
 * One per-tick point of a `social_class` node's survival-calculus history
 * (Wave 2 W2.5a/W2.5b, `reports/wave2-implementation-map.md` owner ruling
 * 3). Sourced from the real `class_snapshot` table (mirrors the
 * `org_snapshot`/`territory_snapshot` per-tick pattern, spec 111 C2), never
 * client-side accumulation. Honest-null (Constitution III.11): a tick the
 * engine has not populated stays `null` rather than a fabricated value.
 */
export interface ClassHistoryPoint {
  tick: number;
  p_acquiescence: number | null;
  p_revolution: number | null;
}

/**
 * `GET /api/games/:id/node/:entityId/history/` response body for a
 * `social_class` node (Wave 2 W2.5a/W2.5b) — mirrors `get_org_history`'s
 * `{org_id, history}` shape (`web/game/engine_bridge.py`). The URL path
 * param is `node_id` (reusing the generic `/node/:node_id/` inspector
 * route), but the envelope key follows `get_org_history`'s convention of
 * naming it after the snapshot table's own PK column — `class_snapshot`'s
 * is `class_id` (`postgres_schema.py`'s `CLASS_SNAPSHOT_DDL`,
 * `query_class_snapshot_history`'s `class_id` parameter). Oldest-tick-first;
 * an empty `history` is an honest "no ticks recorded yet", never a
 * fabricated flat line.
 *
 * `ruptures` is the server-filtered UPRISING/`revolutionary_pressure`
 * event list for THIS node (`query_node_uprising_events`) — preferred over
 * client-filtering `/journal/`, whose shared 200-event cap can silently
 * age an old rupture out of the window in a long game.
 */
export interface ClassHistoryPayload {
  class_id: string;
  history: ClassHistoryPoint[];
  ruptures: GameEvent[];
}

/**
 * A rupture marker on the Survival Duel chart (Wave 2 W2.5a, owner ruling
 * 3): one `UPRISING` event whose `data.trigger === "revolutionary_pressure"`
 * for this class's node id — the only honest P(S|R) > P(S|A) crossing
 * signal (struggling classes only, agitation gated; `struggle.py`'s
 * `uprising_condition`). Sourced from `ClassHistoryPayload.ruptures` (the
 * uncapped, server-filtered list) with the same predicate re-applied
 * client-side as defense-in-depth — never computed from the raw
 * probability crossing, which is not evented for non-struggling classes.
 */
export interface RuptureMarker {
  tick: number;
  eventId: string;
}

/**
 * One per-tick `edge_snapshot` reading (audit Wave 4 straggler, task #76 —
 * the edge-weight history sparkline). `weight` is `value_flow` — the one
 * promoted numeric column every edge type carries (SOLIDARITY/TRIBUTE/
 * WAGES/PRESENCE/TENANCY/ADJACENCY/EXPLOITATION alike); `solidarity` is a
 * real column-level `null` (never fabricated) for every non-SOLIDARITY
 * edge type. Honest-null throughout (Constitution III.11): a tick the
 * engine has not populated stays `null` rather than a fabricated value.
 */
export interface EdgeHistoryPoint {
  tick: number;
  weight: number | null;
  solidarity: number | null;
  tension: number | null;
}

/**
 * `GET /api/games/:id/edge/:entityId/history/` response body (audit Wave 4
 * straggler, task #76) — mirrors `get_org_history`'s `{org_id, history}`
 * shape (`web/game/engine_bridge.py`). `edge_id` is the same
 * `"{source}->{target}"` scheme `get_inspector_edge` established. Oldest-
 * tick-first; an empty `history` is an honest "no ticks recorded yet",
 * never a fabricated flat line.
 */
export interface EdgeHistoryPayload {
  edge_id: string;
  history: EdgeHistoryPoint[];
}

/** Spec 093 US5: GET /api/games/{id}/economy/?territory_id= — real
 *  per-territory economic summary for Territory Detail's economic panel.
 *  See `specs/093-territory-org-detail/contracts/economy.yaml`. */
export interface EconomyPayload {
  territory_id: string | null;
  /** False when no node/edge in the graph references this territory yet. */
  has_data: boolean;
  value_produced: number;
  wage_share: number | null;
  rent_extracted: number;
  exploitation_rate: number | null;
  extraction_intensity: number;
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
  /** Optional: educate submits ``target_community_id`` instead, and
   *  reproduce omits the target entirely when self-targeting. */
  target_id?: string;
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

/**
 * Org-network graph payload from /api/games/{id}/orgs/network/ — see
 * `EngineBridge.get_org_network` (`web/game/engine_bridge.py`) for the
 * authoritative shape. `centrality`/`percolation_ratio` (AW4-R2, verified
 * against the bridge field-for-field) are bridge-derived analytics over
 * THIS response's own node/edge set, additive to the original two-field
 * contract.
 */
export interface OrgNetworkPayload {
  tick: number;
  nodes: OrgNetworkNode[];
  edges: OrgNetworkEdge[];
  /** Per-node degree/betweenness/closeness, keyed by node id. `betweenness`/
   *  `closeness` are honestly omitted (never 0.0-fabricated) when their
   *  guard condition (>1 node, and connected for closeness) isn't met. */
  centrality: Record<string, OrgNetworkCentrality>;
  /** Real SOLIDARITY-network giant-component ratio (L_max / N), or `null`
   *  when undefined (zero social_class nodes) — never a fabricated 0.0. */
  percolation_ratio: number | null;
}

/** One node's entry in `OrgNetworkPayload.centrality`. */
export interface OrgNetworkCentrality {
  degree: number;
  betweenness?: number;
  closeness?: number;
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

/** Empty-state default (Constitution III.11) — an honestly empty network,
 *  never fabricated nodes/edges. Mirrors `EMPTY_CONTRADICTION`/
 *  `EMPTY_WIRE_FEED`'s convention. */
export const EMPTY_ORG_NETWORK: OrgNetworkPayload = {
  tick: 0,
  nodes: [],
  edges: [],
  centrality: {},
  percolation_ratio: null,
};

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

// ---------------------------------------------------------------------------
// Spec 110 B3 — cockpit dashboard payload shapes (spec-109 A4 endpoints)
// ---------------------------------------------------------------------------

/** Scenario metadata from GET /api/scenarios/. */
export interface ScenarioInfo {
  key: string;
  name: string;
  description: string;
  territory_count: number;
}

/** Per-severity event counts (spec 092). */
export interface EventCounts {
  critical: number;
  warning: number;
  informational: number;
}

/**
 * GET /api/games/{id}/summary/ — top-bar aggregate.
 * See `EngineBridge.get_game_summary`. Fields the engine cannot honestly
 * compute yet (`profit_rate`, or any average over an empty collection)
 * are `null` — never a fabricated zero (Constitution III.11).
 */
export interface GameSummaryPayload {
  tick: number;
  imperial_rent: number | null;
  avg_consciousness: number | null;
  population_total: number | null;
  exploitation_rate: number | null;
  profit_rate: number | null;
  org_count: number;
  class_count: number;
  event_counts: EventCounts;
}

/**
 * GET /api/games/{id}/timeseries/ — per-tick history for charts.
 * See `EngineBridge.get_game_timeseries`. Every array is parallel-indexed
 * with `ticks`; individual entries are `null` when that tick has no value.
 */
export interface TimeseriesPayload {
  ticks: number[];
  imperial_rent: (number | null)[];
  consciousness: (number | null)[];
  solidarity: (number | null)[];
  heat: (number | null)[];
  wealth: (number | null)[];
  biocapacity: (number | null)[];
}

/**
 * County-level flow-accrual snapshot (owner item 30, point 5). See
 * `EngineBridge._county_flow_snapshot`: every field is `null` when no
 * territory has ever carried boundary state this session (Constitution
 * III.11 — an empty domain, not a fabricated zero).
 */
export interface CountyFlowSnapshot {
  year: number | null;
  phi_accrued_this_year: number | null;
  wage_accrued_this_year: number | null;
}

/**
 * GET /api/games/{id}/economy/ (no `territory_id`) — graph-wide economy
 * dashboard. See `EngineBridge.get_economy_dashboard`. Distinct from
 * `EconomyPayload`, which is the per-territory shape returned when
 * `?territory_id=` is supplied.
 */
export interface EconomyDashboardPayload {
  tick: number;
  has_data: boolean;
  value_produced: number;
  rent_extracted: number;
  exploitation_rate: number | null;
  profit_rate: number | null;
  occ: number | null;
  imperial_rent_pool: number | null;
  current_super_wage_rate: number | null;
  wage_flow_total: number;
  tribute_flow_total: number;
  /** Wealth summed by `SocialRole`, keyed by role name. */
  wealth_by_class_role: Record<string, number>;
  /** Hex-level static-economy broadcast (spec-109 A7), surfaced when reachable. */
  county_flow: CountyFlowSnapshot;
}

/**
 * One connected SOLIDARITY-edge community (see
 * `_build_solidarity_communities`). Not the XGI hyperedge layer —
 * see the backend docstring for why.
 */
export interface CommunityEntry {
  id: string;
  member_ids: string[];
  member_count: number;
  dominant_role: string | null;
  avg_consciousness: number | null;
  total_solidarity_strength: number;
}

/** GET /api/games/{id}/communities/ — communities left-panel dashboard. */
export interface CommunitiesDashboardPayload {
  communities: CommunityEntry[];
}

/**
 * GET /api/games/{id}/state-apparatus/ — the State Apparatus intelligence
 * screen (spec-111 C2). See `EngineBridge.get_state_apparatus_dashboard` /
 * `_build_state_apparatus_dashboard`.
 *
 * `organizations` reuses `OrgState` (the same shape the Outliner/OrgNetwork
 * already render) filtered server-side to `org_type === "state_apparatus"` —
 * wayne_county seeds the Detroit Police Department (`"ORG002"`), so this is
 * non-empty (`org_count >= 1`) for that scenario. `recent_actions` reuses
 * `GameEvent` (the same shape the journal/alerts feeds render), pre-filtered
 * to STATE_REPRESSION/STATE_SURVEILLANCE/STATE_ACTION_EXECUTED rows.
 *
 * `state_finances` is honestly `{}` today — no scenario seeds
 * `WorldState.state_finances` yet (Constitution III.11: an empty map is the
 * true state, never a fabricated placeholder). Typed as a loose record
 * (per-state `StateFinance.model_dump()` JSON) rather than a fully-modeled
 * interface since there is no real data yet to shape one against.
 */
export interface StateApparatusDashboard {
  tick: number;
  organizations: OrgState[];
  org_count: number;
  total_repression_budget: number;
  total_heat: number;
  state_finances: Record<string, unknown>;
  recent_actions: GameEvent[];
}

/**
 * One live graph edge projected onto the edges-dashboard row shape — see
 * `_edge_row` in `web/game/engine_bridge.py`. `edge_type` is the mechanical
 * `EdgeType` (exploitation/wages/solidarity/tenancy/tribute/…), lowercased;
 * `edge_mode` is the dialectical EdgeMode classification, also lowercased,
 * and `null` until `EdgeTransitionSystem` has run at least one tick — a
 * fresh tick-0 graph legitimately has no edge_mode yet (Constitution
 * III.11). Both are typed as loose `string`s rather than the uppercase
 * `EdgeMode` union above: the backend lowercases whatever `EdgeType`/
 * `EdgeMode` StrEnum value is present, so reusing that union verbatim
 * would be dishonest casing.
 */
export interface EdgeRow {
  source_id: string;
  target_id: string;
  edge_type: string;
  edge_mode: string | null;
  value_flow: number;
  tension: number;
}

/**
 * GET /api/games/{id}/edges/ — the edges/relations left-panel dashboard
 * (spec-111 C2). See `EngineBridge.get_edges_dashboard` /
 * `_build_edges_dashboard`. Aggregates every live graph edge: counts by
 * mechanical `edge_type` and by dialectical `edge_mode` (the latter
 * honestly `{}` until `EdgeTransitionSystem` runs a tick), the top-10
 * edges by absolute `value_flow` and by `tension` (both deterministically
 * tie-broken by `(source_id, target_id)`), and SOLIDARITY-edge strength
 * summary stats. The "where is the class war hottest" ranked/textual
 * companion to the `field_flow` spatial lens.
 *
 * `solidarity_strength_stats`'s `avg`/`min`/`max` are `null` when `count`
 * is 0 (no SOLIDARITY edges seeded this session) — never a fabricated 0.
 */
export interface EdgesDashboardPayload {
  tick: number;
  total_edges: number;
  counts_by_type: Record<string, number>;
  counts_by_mode: Record<string, number>;
  top_by_value_flow: EdgeRow[];
  top_by_tension: EdgeRow[];
  solidarity_strength_stats: {
    count: number;
    avg: number | null;
    min: number | null;
    max: number | null;
  };
}

/** Aggregated admin-level feature from map snapshot. */
export interface AdminFeatureProperties {
  group_key: string;
  group_name: string;
  group_level: AdminLevel;
  hex_count: number;
  /**
   * Sorted H3 index strings rolled into this group (spec-112 C5) — the
   * frontend derives the region's real polygon from these at render time
   * (`H3ClusterLayer`/`h3-js`), since the backend ships `geometry: null`
   * for aggregated features.
   */
  member_h3: string[];
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
  /**
   * Spec-113 Lane D additions (`_aggregate_hex_features`'s `dominant_class_pop`
   * vote / `solidarity_index_sum`/`solidarity_index_pop` mean) — optional
   * because they postdate this interface's other fields and older/stubbed
   * `/map/` fixtures may not carry them yet. `null` is the real backend's
   * honest "no TENANCY-linked coverage this tick" value (Constitution
   * III.11), never fabricated.
   */
  dominant_class?: string | null;
  solidarity_index?: number | null;
  /**
   * Wave 2 Round 2 (`reports/wave2-implementation-map.md`) additions —
   * `_mean_territory_attr`-style pop-weighted mean aggregates:
   * `throughput_position` (ruling 1, real circulation-intensity Pi, no
   * longer the frozen `1.0` constant) and `agitation`
   * (`_agitation_index_by_territory`, DECLARED_CONDITIONAL — legitimately
   * `0.0` absent a crisis tick). Optional/nullable for the same reason as
   * `dominant_class`/`solidarity_index` above.
   */
  throughput_position?: number | null;
  agitation?: number | null;
  /**
   * Wave 2 Round 2's aggregated `territory_type` — the group's
   * population-weighted-mode real `TerritoryType` enum value (ruling 4).
   * Categorical, like `dominant_class`.
   */
  territory_type?: string | null;
  /**
   * Audit Wave 4 straggler (task #76) — `_aggregate_hex_features`'s
   * population-weighted mean of `centrality` (a territory's own
   * degree-centrality within the org-network topology,
   * `_centrality_by_territory`). Optional/nullable for the same
   * partial-coverage reason as `throughput_position`/`agitation`.
   */
  centrality?: number | null;
  /**
   * Wave 5 receptivity pair — `_aggregate_hex_features`'s
   * population-weighted mean of `mass_receptivity` (M_r) and
   * population-weighted-mode `vision_state` (desert/mud/water, same
   * deterministic tie-break as `territory_type`). Optional/nullable for
   * the same partial-coverage reason as the entries above.
   */
  mass_receptivity?: number | null;
  vision_state?: string | null;
  /**
   * Feature 021 lens pair — `_aggregate_hex_features`'s population-weighted
   * mean of `wage_pressure` (the Reserve Army's bounded-sigmoid
   * wage-discipline coefficient) and `dispossession_intensity`
   * (`DispossessionIntensityCalculator`'s composite intensity).
   * Optional/nullable for the same partial-coverage reason as
   * `mass_receptivity` above — both are presence-conditional, not merely
   * value-conditional (the writing system skips a territory entirely
   * absent reserve-army pressure / dispossession activity this tick).
   */
  wage_pressure?: number | null;
  dispossession_intensity?: number | null;
}

// ---------------------------------------------------------------------------
// Program 19/20 Wave 3 Round 1/2a — the field_state endpoint (System-19/20
// contradiction-field stack). See `EngineBridge.get_field_state`,
// `_build_field_state_nodes`/`_build_field_state_edges`
// (`web/game/engine_bridge.py`).
// ---------------------------------------------------------------------------

/**
 * One `social_class` node's field-stack entry (`_build_field_state_nodes`).
 * Every key beyond `id`/`name` is optional and independently present —
 * Constitution III.11: a node carrying only SOME of the field stack
 * contributes only the keys it actually has, never a fabricated zero/empty
 * dict for the rest.
 *
 * `fields`/`laplacian`/`df_dt` are keyed by contradiction-field name (e.g.
 * `"exploitation"`, `"atomization"` — see the Wave-3 implementation map's
 * "verified-reality census": production computes exactly these two fields
 * today, not the fuller five the original brief claimed).
 */
export interface FieldStateNode {
  id: string;
  name: string;
  /** ContradictionFieldSystem (@19) per-field values. */
  fields?: Record<string, number>;
  /** FieldDerivativeSystem (@20) per-field Laplacian. */
  laplacian?: Record<string, number>;
  /** FieldDerivativeSystem (@20) per-field temporal derivative. */
  df_dt?: Record<string, number>;
  /** FascistFactionSystem's per-class routing signal (`reactionary.py`). */
  fascist_alignment?: number;
}

/**
 * One per-field gradient on a class<->class edge (`_build_field_state_edges`),
 * territory-anchored via the bridge's existing TENANCY resolution.
 * `source_territory`/`target_territory` are `null` (key present, never
 * omitted) when that endpoint class has no resolvable TENANCY territory —
 * the same keep-key-use-null convention `_serialize_territory`'s
 * `dominant_class`/`solidarity_index` already use for an unresolvable
 * per-territory aggregate.
 */
export interface FieldStateEdge {
  source: string;
  target: string;
  source_territory: string | null;
  target_territory: string | null;
  field: string;
  gradient: number;
}

/**
 * The System-18 fixed-point regime classification stashed on the graph's
 * `dialectical_regime` attr (`contradiction.py`'s `DIALECTICAL_REGIME_ATTR`,
 * `classify_regime`). `opposition` names which `OppositionState.key` the
 * regime/rate describe (`target.key` at the write site — verified against
 * `contradiction.py:361`, not the stale `"principal"` name a nearby comment
 * claims).
 */
export interface DialecticalRegime {
  regime: "reproduction" | "crisis" | "sublation";
  opposition: string;
  rate: number;
}

/**
 * `GET /api/games/{id}/field_state/` — the System-19/20 contradiction-field
 * stack for the Field screen (Program 19/20, Wave 3 Round 1/2a). See
 * `EngineBridge.get_field_state`'s docstring for the full trace.
 *
 * **Known altitude gap (R1b, not yet fixed):** the web bridge steps via the
 * `WorldState` round-trip facade, so `contradiction_fields`/`field_derivatives`
 * are excluded from `SocialClass` reconstruction and `principal_field`/
 * `dialectical_regime` are outside `to_graph()`'s graph-attr whitelist. On a
 * real running game today, `nodes`/`edges` are almost always `[]` and
 * `principal_field`/`dialectical_regime` almost always `null` — only
 * `fascist_alignment` (a real, defaulted `SocialClass` field) reliably
 * survives the round-trip. Consume this payload accordingly: an honest
 * empty is the COMMON case, not a bug, until R1b lands a carry-forward
 * channel for the rest of the field stack.
 */
export interface FieldStatePayload {
  tick: number;
  nodes: FieldStateNode[];
  edges: FieldStateEdge[];
  principal_field: string | null;
  dialectical_regime: DialecticalRegime | null;
}

/**
 * One tick's per-county values for a replayable map metric — one entry of
 * `MapHistoryPayload.frames` (Program 17 Wave 3, Backend-W3R3's
 * `GET /api/games/{id}/map/history/`, `EngineBridge.get_map_history`).
 * Keyed by `county_fips`, NOT `h3_index` — both persisted sources
 * (`territory_snapshot`/`view_runtime_trace_emission`) are county-grained,
 * unlike the live hex-zoom `/map/` payload. `null` is an honest per-county
 * no-data entry for this tick (Constitution III.11) — the RADAR LOOP
 * scrubber must render it as an empty, never interpolate/fall back to a
 * neighboring tick or the live value.
 */
export interface MapHistoryFrame {
  tick: number;
  values: Record<string, number | null>;
}

/**
 * `GET /api/games/{id}/map/history/?metric=<name>[&from_tick=][&to_tick=]`
 * — the RADAR LOOP tick scrubber's real data source (Program 17 Wave 3,
 * Frontend-W3R3). Only `MAP_HISTORY_REPLAYABLE_METRICS` (`lib/lens.ts`,
 * mirroring the backend's `map_contract.py` tuple of the same name) —
 * heat/population/profit_rate/exploitation_rate — resolve without an
 * error; every other `MapMetric` 422s (`"not_replayable"`) because it
 * exists only in the current-tick `hex_latest` cache, not an append-only
 * history table (see `EngineBridge.get_map_history`'s docstring for the
 * full verified split). `frames` is tick-ascending. `capped` is `true`
 * when the served window is narrower than requested — the backend's
 * 128-tick window cap (`_MAP_HISTORY_WINDOW_CAP`).
 */
export interface MapHistoryPayload {
  metric: string;
  from_tick: number;
  to_tick: number;
  capped: boolean;
  frames: MapHistoryFrame[];
}
