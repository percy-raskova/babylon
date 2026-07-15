/**
 * Typed endpoint manifest — the single source of truth binding every game API
 * route to its response type and its path pattern.
 *
 * WHY THIS EXISTS (two audiences, one declaration):
 *
 *  1. **The UI calls through it.** A route string lives in exactly ONE place —
 *     `endpoints.economy.path({ id })` instead of a `` `/api/games/${id}/economy/` ``
 *     literal copied across slices. No divergent copies to drift.
 *
 *  2. **The Seam Observatory reads it.** The bridge sentinel
 *     (`babylon.sentinels.seam.bridge`) parses THIS file statically —
 *     `ep<Interface>("/api/games/:id/x/")` yields `(canonical path → response
 *     interface)` — and joins it against the backend `urls.py → view →
 *     bridge.get_*` chain to verify, autonomously, that every field the UI is
 *     promised is actually emitted by the serializer, and that every serializer
 *     reaching the wire is consumed by a typed contract declared here.
 *
 * A route whose response has no declared interface *yet* is declared
 * `ep<Untyped>(...)` — an explicit, machine-visible punch-list row for the
 * UI/UX wiring pass, never a fabricated type. Adding or removing a route here
 * is absorbed by the sentinel on its next run: coverage is a pure function of
 * this file plus the backend routes, with no hand-maintained mapping table
 * anywhere. That is the whole point — the seam grows and contracts with the code.
 */

import type {
  GameSnapshot,
  GameSummary,
  GameSummaryPayload,
  TimeseriesPayload,
  EconomyDashboardPayload,
  CommunitiesDashboardPayload,
  JournalPayload,
  AlertsPayload,
  OrgNetworkPayload,
  HypergraphPayload,
  InfrastructurePayload,
  ScenarioInfo,
  ActionPreviewResult,
  ClassHistoryPayload,
  EdgeHistoryPayload,
  FieldStatePayload,
  MapHistoryPayload,
} from "@/types/game";
import type { ContradictionSnapshot, EndgameState, ObjectivesTracker } from "@/types/dialectic";
import type { TradeFlowsPayload } from "@/types/trade";
import type { WireFeed } from "@/types/wire";
import type { ExplainResponse, InspectorNodeResponse } from "@/types/inspection";
import type { FeatureCollection } from "geojson";

/**
 * Marker for a route whose response body has no declared TS interface yet.
 * The sentinel treats it as an unresolved seam (a wiring punch-list item),
 * never as a checkable contract.
 */
export interface Untyped {
  readonly __untyped: unique symbol;
}

export type HttpMethod = "GET" | "POST" | "DELETE";

/** Phantom key retaining the response type for inference; never present at runtime. */
declare const RESPONSE_TYPE: unique symbol;

export interface Endpoint<T> {
  readonly pattern: string;
  readonly method: HttpMethod;
  readonly [RESPONSE_TYPE]?: T;
  /** Fill `:param` placeholders with concrete values to build the request URL. */
  path(params?: Record<string, string | number>): string;
}

/** Recover the declared response type of an endpoint (`EndpointResponse<typeof endpoints.economy>`). */
export type EndpointResponse<E> = E extends Endpoint<infer T> ? T : never;

/**
 * Declare one endpoint: its response type `T` (phantom), path `pattern`, and
 * HTTP method. `path()` substitutes `:param` segments — matching the backend
 * `<converter:name>` route positions — into a concrete URL, byte-identical to
 * the template literals it replaces (no encoding, so UUID/h3 ids pass through
 * unchanged and existing MSW path matchers keep working).
 */
function ep<T>(pattern: string, method: HttpMethod = "GET"): Endpoint<T> {
  return {
    pattern,
    method,
    path(params: Record<string, string | number> = {}): string {
      return pattern.replace(/:(\w+)/g, (_match, key: string) => {
        const value = params[key];
        if (value === undefined) {
          throw new Error(`endpoint ${pattern}: missing path param '${key}'`);
        }
        return String(value);
      });
    },
  };
}

/**
 * Every game API route (see `web/game/urls.py`), declared once. Section order
 * mirrors that file so a reviewer can diff the two by eye.
 */
export const endpoints = {
  // ---- Scenario catalog + game lifecycle -------------------------------- //
  scenarioList: ep<ScenarioInfo[]>("/api/scenarios/"),
  gameList: ep<GameSummary[]>("/api/games/"),
  gameCreate: ep<Untyped>("/api/games/", "POST"),
  gameDetail: ep<Untyped>("/api/games/:id/"),
  gamePause: ep<Untyped>("/api/games/:id/pause/", "POST"),
  gameResume: ep<Untyped>("/api/games/:id/resume/", "POST"),
  gameRecover: ep<Untyped>("/api/games/:id/recover/", "POST"),

  // ---- Core state + tick-driven panels ---------------------------------- //
  gameState: ep<GameSnapshot>("/api/games/:id/state/"),
  summary: ep<GameSummaryPayload>("/api/games/:id/summary/"),
  timeseries: ep<TimeseriesPayload>("/api/games/:id/timeseries/"),
  map: ep<FeatureCollection>("/api/games/:id/map/"),
  // Program 17 Wave 3 (Backend-W3R3): the RADAR LOOP replay scrubber's data
  // source — see MapHistoryPayload's docstring for the 4-of-11 replayable
  // metric split (`lib/lens.ts`'s MAP_HISTORY_REPLAYABLE_METRICS).
  mapHistory: ep<MapHistoryPayload>("/api/games/:id/map/history/"),

  // ---- Domain dashboards ------------------------------------------------ //
  economy: ep<EconomyDashboardPayload>("/api/games/:id/economy/"),
  communities: ep<CommunitiesDashboardPayload>("/api/games/:id/communities/"),
  organizations: ep<Untyped>("/api/games/:id/organizations/"),
  edges: ep<Untyped>("/api/games/:id/edges/"),
  stateApparatus: ep<Untyped>("/api/games/:id/state-apparatus/"),
  journal: ep<JournalPayload>("/api/games/:id/journal/"),
  alerts: ep<AlertsPayload>("/api/games/:id/alerts/"),
  wire: ep<WireFeed>("/api/games/:id/wire/"),

  // ---- Endgame / dialectic screen (spec-095) ---------------------------- //
  contradiction: ep<ContradictionSnapshot>("/api/games/:id/contradiction/"),
  endgame: ep<EndgameState>("/api/games/:id/endgame/"),
  objectives: ep<ObjectivesTracker>("/api/games/:id/objectives/"),
  // Program 19/20 Wave 3 Round 1/2a — the Field screen's System-19/20
  // contradiction-field stack (see FieldStatePayload's docstring for the
  // known R1b altitude gap: nodes/edges/principal_field/dialectical_regime
  // are honestly empty/null on most real games today).
  fieldState: ep<FieldStatePayload>("/api/games/:id/field_state/"),

  // ---- Trade surfaces (spec-103) ---------------------------------------- //
  tradeFlows: ep<TradeFlowsPayload>("/api/games/:id/trade-flows/"),
  countyExposure: ep<Untyped>("/api/games/:id/exposure/"),
  tradePanel: ep<Untyped>("/api/games/:id/trade-panel/"),

  // ---- Spatial multi-scale ---------------------------------------------- //
  orgNetwork: ep<OrgNetworkPayload>("/api/games/:id/orgs/network/"),
  hypergraphCommunities: ep<HypergraphPayload>("/api/games/:id/hypergraph/communities/"),
  infrastructure: ep<InfrastructurePayload>("/api/games/:id/infrastructure/"),

  // ---- Inspector drill-downs (adapter-decoded; RawEntity, not a wire
  //      contract — declared Untyped so the sentinel reports the adapter seam) //
  inspectorNode: ep<InspectorNodeResponse>("/api/games/:id/node/:entityId/"),
  inspectorOrg: ep<Untyped>("/api/games/:id/org/:entityId/"),
  inspectorCommunity: ep<Untyped>("/api/games/:id/community/:entityId/"),
  inspectorEdge: ep<Untyped>("/api/games/:id/edge/:entityId/"),
  inspectorHex: ep<Untyped>("/api/games/:id/hex/:entityId/"),
  inspectorOrgHistory: ep<Untyped>("/api/games/:id/org/:entityId/history/"),
  inspectorTerritoryHistory: ep<Untyped>("/api/games/:id/territory/:entityId/history/"),
  // Wave 2 W2.5a/W2.5b (reports/wave2-implementation-map.md owner ruling 3):
  // class survival-calculus history — mirrors the org/territory history
  // routes above but, unlike them, has a real frontend consumer
  // (SurvivalDuelPanel) as of this row, hence typed rather than Untyped.
  inspectorNodeHistory: ep<ClassHistoryPayload>("/api/games/:id/node/:entityId/history/"),
  // Audit Wave 4 straggler (task #76): edge-weight history sparkline — same
  // "has a real frontend consumer" reasoning as inspectorNodeHistory above
  // (the edge adapter's own `.history` row, not a dead punch-list row).
  inspectorEdgeHistory: ep<EdgeHistoryPayload>("/api/games/:id/edge/:entityId/history/"),

  // ---- Formula/metric provenance (spec-113 Lane D) ---------------------- //
  explain: ep<ExplainResponse>("/api/games/:id/explain/"),

  // ---- Action utilities ------------------------------------------------- //
  actionsAvailable: ep<Untyped>("/api/games/:id/actions/available/"),
  actionsPreview: ep<ActionPreviewResult>("/api/games/:id/actions/preview/", "POST"),
  actionDelete: ep<Untyped>("/api/games/:id/actions/:actionId/", "DELETE"),
  actionsList: ep<Untyped>("/api/games/:id/actions/"),
  resolveTick: ep<Untyped>("/api/games/:id/resolve/", "POST"),
  tickResults: ep<Untyped>("/api/games/:id/results/:tick/"),

  // ---- Per-verb action endpoints (spec-040 §6.1). `*Targets` are GET
  //      (get_<verb>_targets serializers); `*Submit` are POST resolvers. ---- //
  educateTargets: ep<Untyped>("/api/games/:id/actions/educate/targets/"),
  educateSubmit: ep<Untyped>("/api/games/:id/actions/educate/", "POST"),
  aidTargets: ep<Untyped>("/api/games/:id/actions/aid/targets/"),
  aidSubmit: ep<Untyped>("/api/games/:id/actions/aid/", "POST"),
  attackTargets: ep<Untyped>("/api/games/:id/actions/attack/targets/"),
  attackSubmit: ep<Untyped>("/api/games/:id/actions/attack/", "POST"),
  mobilizeTargets: ep<Untyped>("/api/games/:id/actions/mobilize/targets/"),
  mobilizeSubmit: ep<Untyped>("/api/games/:id/actions/mobilize/", "POST"),
  campaignTargets: ep<Untyped>("/api/games/:id/actions/campaign/targets/"),
  campaignSubmit: ep<Untyped>("/api/games/:id/actions/campaign/", "POST"),
  moveTargets: ep<Untyped>("/api/games/:id/actions/move/targets/"),
  moveSubmit: ep<Untyped>("/api/games/:id/actions/move/", "POST"),
  investigateTargets: ep<Untyped>("/api/games/:id/actions/investigate/targets/"),
  investigateSubmit: ep<Untyped>("/api/games/:id/actions/investigate/", "POST"),
  reproduceTargets: ep<Untyped>("/api/games/:id/actions/reproduce/targets/"),
  reproduceSubmit: ep<Untyped>("/api/games/:id/actions/reproduce/", "POST"),
  negotiateTargets: ep<Untyped>("/api/games/:id/actions/negotiate/targets/"),
  negotiateSubmit: ep<Untyped>("/api/games/:id/actions/negotiate/", "POST"),
} as const;
