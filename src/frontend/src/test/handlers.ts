/**
 * MSW request handlers — auth/lobby (B1/B2) plus the stateful game-loop
 * mock the B3 cockpit store exercises (spec-110 B3).
 *
 * The game-loop portion mirrors `web/frontend/src/test/handlers.ts`'s
 * mutable-module-state pattern: `mockSnapshot`/`resetMockGameState()` for
 * the current tick, `resolveBehaviorQueue` for scripting one-shot
 * 409/500 responses out of `/resolve/`, and `requestLog` for asserting
 * fan-out counts and request ordering (heartbeat gating, "exactly one
 * fetch per panel per tick change", serialized Play).
 */

import { http, HttpResponse } from "msw";
import {
  makeSnapshot,
  makeGameSummary,
  makeWireFeed,
  makeContradictionSnapshot,
  makeEndgameState,
  makeObjectivesTracker,
  makeTradeFlowsPayload,
  makeJournalPayload,
  makeClassHistoryPayload,
  makeEdgeHistoryPayload,
  makeFieldStatePayload,
  makeMapHistoryPayload,
  makeOrgNetworkPayload,
  makeStateApparatusDashboard,
  makeEdgesDashboard,
} from "./fixtures";
import type { GameSnapshot } from "@/types/game";

export const DEFAULT_GAME_ID = "game-001";

let mockSnapshot: GameSnapshot = makeSnapshot({ session_id: DEFAULT_GAME_ID });

/** Ordered log of every request the game-loop handlers served this test. */
export const requestLog: string[] = [];

type ResolveBehavior = "ok" | "409" | "500";
/** One-shot behaviors for POST /resolve/, shift()'d in order; "ok" once empty. */
export const resolveBehaviorQueue: ResolveBehavior[] = [];

/** Reset all mutable mock state — call from `beforeEach` in tests that use it. */
export function resetMockGameState(overrides?: Partial<GameSnapshot>): void {
  mockSnapshot = makeSnapshot({ session_id: DEFAULT_GAME_ID, events: [], ...overrides });
  requestLog.length = 0;
  resolveBehaviorQueue.length = 0;
}

export function getMockSnapshot(): GameSnapshot {
  return mockSnapshot;
}

/** Replace the snapshot the next GET /state/ will serve (e.g. to seed events for a tick). */
export function setMockSnapshot(next: GameSnapshot): void {
  mockSnapshot = next;
}

function logRequest(label: string): void {
  requestLog.push(label);
}

export const handlers = [
  // Auth — exercised by api/client.test.ts's `get()` happy-path tests.
  http.get("/accounts/whoami/", () =>
    HttpResponse.json({
      status: "ok",
      data: { is_authenticated: true, id: 1, username: "testuser" },
    }),
  ),

  http.post("/accounts/login/", () =>
    HttpResponse.json({
      status: "ok",
      data: { username: "testuser" },
    }),
  ),

  // GET /accounts/login/ — api/client's ensureCsrfCookie() hits this to
  // obtain a fresh CSRF cookie before postForm() when none is set yet.
  http.get("/accounts/login/", () =>
    HttpResponse.text("<html><body>login</body></html>", {
      headers: { "Content-Type": "text/html" },
    }),
  ),

  http.post("/accounts/logout/", () => HttpResponse.json({ status: "ok", data: null })),

  http.get("/api/scenarios/", () =>
    HttpResponse.json({
      status: "ok",
      data: [
        {
          key: "wayne_county",
          name: "Wayne County Organizer",
          description: "Organize in Wayne County, Michigan.",
          territory_count: 81,
        },
      ],
    }),
  ),

  http.get("/api/games/", () =>
    HttpResponse.json({
      status: "ok",
      data: [makeGameSummary({ id: DEFAULT_GAME_ID, current_tick: mockSnapshot.tick })],
    }),
  ),

  http.post("/api/games/", () =>
    HttpResponse.json({ status: "ok", data: { session_id: DEFAULT_GAME_ID } }, { status: 201 }),
  ),

  // ---- Game loop -----------------------------------------------------

  http.get("/api/games/:id/state/", () => {
    logRequest("GET state");
    return HttpResponse.json({ status: "ok", data: mockSnapshot, tick: mockSnapshot.tick });
  }),

  http.post("/api/games/:id/resolve/", () => {
    logRequest("POST resolve");
    const behavior = resolveBehaviorQueue.shift() ?? "ok";
    if (behavior === "409") {
      return HttpResponse.json(
        { status: "error", message: "Game is already being resolved or is no longer active" },
        { status: 409 },
      );
    }
    if (behavior === "500") {
      return HttpResponse.json(
        { status: "error", message: "Tick resolution failed" },
        { status: 500 },
      );
    }
    mockSnapshot = { ...mockSnapshot, tick: mockSnapshot.tick + 1, events: [] };
    return HttpResponse.json({ status: "ok", data: { resolved: true }, tick: mockSnapshot.tick });
  }),

  // ---- Docked-panel dashboards (spec 109 A4) --------------------------

  http.get("/api/games/:id/summary/", () => {
    logRequest("GET summary");
    return HttpResponse.json({
      status: "ok",
      data: {
        tick: mockSnapshot.tick,
        imperial_rent: 12.5,
        avg_consciousness: 0.4,
        population_total: 42000,
        exploitation_rate: 0.3,
        profit_rate: null,
        org_count: mockSnapshot.organizations.length,
        class_count: 4,
        event_counts: { critical: 0, warning: 0, informational: 0 },
      },
    });
  }),

  http.get("/api/games/:id/timeseries/", () => {
    logRequest("GET timeseries");
    return HttpResponse.json({
      status: "ok",
      data: {
        ticks: [0, 1],
        imperial_rent: [10, 12.5],
        consciousness: [0.3, 0.4],
        solidarity: [1, 1],
        heat: [0.2, 0.25],
        wealth: [100, 105],
        biocapacity: [0.5, 0.5],
      },
    });
  }),

  http.get("/api/games/:id/economy/", () => {
    logRequest("GET economy");
    return HttpResponse.json({
      status: "ok",
      data: {
        tick: mockSnapshot.tick,
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
        wealth_by_class_role: { proletariat: 40, bourgeoisie: 60 },
        county_flow: { year: null, phi_accrued_this_year: null, wage_accrued_this_year: null },
      },
    });
  }),

  // Cross-tick event history (spec-092) — not a docked panel (no
  // `panels.journal` slice), but EconomyDashboard's crisis timeline
  // (Wave 2 W2.2a) fetches it directly and filters for
  // `crisis_phase_transition`. Empty by default; tests that need crisis
  // rows override with server.use().
  http.get("/api/games/:id/journal/", () => {
    logRequest("GET journal");
    return HttpResponse.json({ status: "ok", data: makeJournalPayload() });
  }),

  http.get("/api/games/:id/communities/", () => {
    logRequest("GET communities");
    return HttpResponse.json({ status: "ok", data: { communities: [] } });
  }),

  // spec-111 C2 — the State Apparatus intelligence screen. Defaults mirror
  // the real wayne_county contract (Detroit PD seeded, no actions/finances
  // yet); tests needing a specific payload override with server.use().
  http.get("/api/games/:id/state-apparatus/", () => {
    logRequest("GET stateApparatus");
    return HttpResponse.json({
      status: "ok",
      data: makeStateApparatusDashboard({ tick: mockSnapshot.tick }),
    });
  }),

  // spec-111 C2 — the Edges/Tension dashboard ("where is the class war
  // hottest"). Defaults mirror the real wayne_county contract (dense
  // relationship graph, one seeded SOLIDARITY edge, no edge_mode yet);
  // tests needing a specific payload override with server.use().
  http.get("/api/games/:id/edges/", () => {
    logRequest("GET edges");
    return HttpResponse.json({
      status: "ok",
      data: makeEdgesDashboard({ tick: mockSnapshot.tick }),
    });
  }),

  http.get("/api/games/:id/map/", () => {
    logRequest("GET map");
    return HttpResponse.json({
      status: "ok",
      data: { type: "FeatureCollection", features: [] },
    });
  }),

  // Program 17 Wave 3 (Backend-W3R3) — RADAR LOOP's map-history replay
  // frames. Honest empty-but-well-formed by default (mirrors
  // `stub_bridge.py::get_map_history`'s `frames: []` — this handler does
  // NOT emulate the real bridge's 400/422 validation, since the frontend
  // gates `metric` client-side via `isReplayableLens` before ever fetching;
  // tests exercising a specific frame set or an error response override
  // with `server.use()`.
  http.get("/api/games/:id/map/history/", ({ request }) => {
    logRequest("GET map:history");
    const metric = new URL(request.url).searchParams.get("metric") ?? "heat";
    return HttpResponse.json({ status: "ok", data: makeMapHistoryPayload({ metric }) });
  }),

  // Spec-113 Lane Carto's cartographic substrate (`lib/geo/topology.ts`) —
  // DeckGLMap fetches these directly (not through the app's api client), so
  // they need their own MSW handlers or `onUnhandledRequest: "error"`
  // (setup.ts) fails every test that mounts a real DeckGLMap. Minimal but
  // structurally valid (empty-geometry) topologies — geometry-content
  // assertions belong to `lib/geo/topology.test.ts`'s real-asset smoke
  // tests, not here.
  http.get("/geo/counties.topojson", () =>
    HttpResponse.json({
      type: "Topology",
      arcs: [],
      objects: { counties: { type: "GeometryCollection", geometries: [] } },
    }),
  ),
  http.get("/geo/states.topojson", () =>
    HttpResponse.json({
      type: "Topology",
      arcs: [],
      objects: { states: { type: "GeometryCollection", geometries: [] } },
    }),
  ),

  // ---- Takeover surfaces + Objectives dock tab (spec-110 B5) -----------

  http.get("/api/games/:id/wire/", () => {
    logRequest("GET wire");
    return HttpResponse.json({ status: "ok", data: makeWireFeed() });
  }),

  http.get("/api/games/:id/contradiction/", () => {
    logRequest("GET contradiction");
    return HttpResponse.json({ status: "ok", data: makeContradictionSnapshot() });
  }),

  http.get("/api/games/:id/endgame/", () => {
    logRequest("GET endgame");
    return HttpResponse.json({ status: "ok", data: makeEndgameState() });
  }),

  http.get("/api/games/:id/objectives/", () => {
    logRequest("GET objectives");
    return HttpResponse.json({ status: "ok", data: makeObjectivesTracker() });
  }),

  // Program 19/20 Wave 3 R2a — honest empty-but-well-formed by default
  // (mirrors the stub bridge, `web/game/stub_bridge.py::get_field_state`);
  // tests needing real nodes/edges override with server.use().
  http.get("/api/games/:id/field_state/", () => {
    logRequest("GET field_state");
    return HttpResponse.json({ status: "ok", data: makeFieldStatePayload() });
  }),

  http.get("/api/games/:id/trade-flows/", () => {
    logRequest("GET trade-flows");
    return HttpResponse.json({ status: "ok", data: makeTradeFlowsPayload() });
  }),

  // AW4-R2 — the Network takeover's org-network graph. Honest
  // empty-but-well-formed by default (Constitution III.11: no fabricated
  // nodes) — tests exercising real rendering override with server.use().
  http.get("/api/games/:id/orgs/network/", () => {
    logRequest("GET orgs:network");
    return HttpResponse.json({ status: "ok", data: makeOrgNetworkPayload() });
  }),

  // ---- Action Composer: verb targets + submit --------------------------

  http.get("/api/games/:id/actions/:verb/targets/", ({ params }) => {
    logRequest(`GET targets:${String(params.verb)}`);
    // Flat body, no envelope — matches the real per-verb target endpoints'
    // quirk (see fetchVerbTargets's docstring). Empty by default; tests
    // that need real targets override with server.use().
    return HttpResponse.json({ targets: [] });
  }),

  http.post("/api/games/:id/actions/:verb/", ({ params }) => {
    logRequest(`POST actions:${String(params.verb)}`);
    return HttpResponse.json({ status: "ok", data: null });
  }),

  // Live preview strip (Program 17 Wave 1 item W1.2) — default is an honest
  // all-zero/no-warning baseline; tests that care about a specific delta
  // override with server.use().
  http.post("/api/games/:id/actions/preview/", () => {
    logRequest("POST actions:preview");
    return HttpResponse.json({
      status: "ok",
      data: {
        estimated_consciousness_delta: 0,
        estimated_heat_delta: 0,
        action_point_cost: 0,
        success_probability: 1,
        affected_territory_ids: [],
        warnings: [],
      },
    });
  }),

  // ---- Inspector drill-downs — GET /api/games/{id}/{kind}/{entityId}/ --

  // Wave 2 W2.5a/W2.5b — GET /api/games/{id}/node/{entityId}/history/: a
  // class's survival-calculus history (SurvivalDuelPanel's fetch). Registered
  // ahead of the generic 2-segment catch-all below since this route has an
  // extra trailing /history/ segment. Empty by default; tests needing real
  // points/markers override with server.use().
  http.get("/api/games/:id/node/:entityId/history/", ({ params }) => {
    logRequest("GET node:history");
    return HttpResponse.json({
      status: "ok",
      data: makeClassHistoryPayload({ class_id: String(params.entityId) }),
    });
  }),

  // Audit Wave 4 straggler (task #76) — GET /api/games/{id}/edge/{entityId}/history/:
  // the edge-weight history sparkline. Registered ahead of the generic
  // catch-all below for the same reason as node:history above. Empty by
  // default; tests needing real weight points override with server.use().
  http.get("/api/games/:id/edge/:entityId/history/", ({ params }) => {
    logRequest("GET edge:history");
    return HttpResponse.json({
      status: "ok",
      data: makeEdgeHistoryPayload({ edge_id: String(params.entityId) }),
    });
  }),

  http.get("/api/games/:id/:kind/:entityId/", ({ params }) => {
    logRequest(`GET inspector:${String(params.kind)}`);
    return HttpResponse.json({
      status: "ok",
      data: { kind: params.kind, id: params.entityId },
    });
  }),
];
