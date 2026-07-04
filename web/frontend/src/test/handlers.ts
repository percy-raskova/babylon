/**
 * MSW request handlers — stateful mock of the Django API endpoints and Babylon engine.
 */

import { http, HttpResponse } from "msw";
import {
  makeWayneCountySnapshot,
  makeAvailableAction,
  makeGameSummary,
  makeActionResult,
} from "./fixtures";
import { GameSnapshot, GameEvent } from "../types/game";
import orgsFixture from "../mocks/organizations.json";
import educateTargetsFixture from "../mocks/educate_targets.json";

// In-memory state machine for the mock game loop
let mockState: GameSnapshot = makeWayneCountySnapshot();
let queuedActions: { verb: string; targets?: string[] }[] = [];

// Spec 092: journal/alerts fixture — a mix of severities across ticks so
// the Event Log filter buttons and the Tick Resolution alert feed both
// have something real to render against.
//
// Spec-092 review fix (Defect D): types use the REAL engine's lowercase
// snake_case `EventType` casing (verified against
// `src/babylon/models/enums/events.py`), and severities match the
// backend's `_EVENT_SEVERITY` classification table
// (`web/game/engine_bridge.py`) rather than `lib/eventClassifier.ts`'s
// UPPERCASE-keyed map — EventLogPage/TickResolutionPage no longer consult
// that classifier (they read `event.severity` directly), so a green test
// suite against these fixtures now means something on real production data.
const mockJournalEvents: GameEvent[] = [
  {
    id: "journal-1",
    type: "uprising",
    tick: 5,
    severity: "critical",
    title: "Uprising",
    body: "Workers rose up in Hamtramck",
    data: { org_id: "ORG001" },
  },
  {
    id: "journal-2",
    type: "eviction_pipeline",
    tick: 4,
    severity: "warning",
    title: "Eviction Pipeline",
    body: "Eviction pipeline triggered against striking tenants in Dearborn",
    data: {},
  },
  {
    id: "journal-3",
    type: "wage_payment",
    tick: 3,
    severity: "informational",
    title: "Wage Payment",
    body: "Wages paid to proletariat",
    data: {},
  },
];

// Reset state function for testing
export const resetMockState = () => {
  mockState = makeWayneCountySnapshot();
  queuedActions = [];
};

export const handlers = [
  // Auth endpoints
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

  http.get("/accounts/login/", () =>
    HttpResponse.text("<html><body>login</body></html>", {
      headers: {
        "Content-Type": "text/html",
      },
    }),
  ),

  http.post("/accounts/logout/", () => HttpResponse.json({ status: "ok", data: null })),

  // Scenario catalog
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
        {
          key: "us_nationwide",
          name: "United States — Nationwide",
          description: "Full CONUS simulation",
          territory_count: 1100,
        },
      ],
    }),
  ),

  // Game list
  http.get("/api/games/", () =>
    HttpResponse.json({
      status: "ok",
      data: [
        makeGameSummary({
          id: "wayne-county-001",
          scenario: "wayne_county",
          current_tick: mockState.tick,
          status: "active",
        }),
      ],
    }),
  ),

  // Create game
  http.post("/api/games/", () => {
    resetMockState(); // Reset for a new game
    return HttpResponse.json({
      status: "ok",
      data: { session_id: "wayne-county-001" },
    });
  }),

  // Game state
  http.get("/api/games/:id/state/", () =>
    HttpResponse.json({
      status: "ok",
      data: mockState,
    }),
  ),

  // Organizations
  http.get("/api/games/:id/organizations/", ({ request }) => {
    const url = new URL(request.url);
    const playerOnly = url.searchParams.get("player_only") === "true";
    let orgs = orgsFixture.organizations;
    if (playerOnly) {
      orgs = orgs.filter((o) => o.vanguard !== null && o.vanguard !== undefined);
    }
    return HttpResponse.json({
      status: "ok",
      data: { organizations: orgs },
    });
  }),

  // Available actions
  http.get("/api/games/:id/actions/available/", () =>
    HttpResponse.json({
      status: "ok",
      data: [
        makeAvailableAction({ verb: "educate", targets: ["C001", "C004"], cost: 0 }),
        makeAvailableAction({ verb: "attack", targets: ["C003"], cost: 0 }),
        makeAvailableAction({ verb: "mobilize", targets: ["C001"], cost: 0 }),
      ],
    }),
  ),

  // Educate Targets
  http.get("/api/games/:id/actions/educate/targets/", () =>
    HttpResponse.json(educateTargetsFixture),
  ),

  // Submit action — per-verb endpoints (Spec 040)
  http.post("/api/games/:id/actions/:verb/", async ({ params, request }) => {
    const data = (await request.json()) as Record<string, unknown>;
    const verb = params.verb as string;

    // Affordability Check Contract
    let canAfford = true;
    let reason = "";

    const playerOrg = mockState.organizations[0]; // Assuming Wayne County Player Org is first
    if (playerOrg && playerOrg.vanguard) {
      if (verb === "attack") {
        if (playerOrg.vanguard.cadre_labor < 2) {
          canAfford = false;
          reason = "Insufficient Cadre Labor (need 2)";
        }
      } else if (verb === "educate") {
        if (playerOrg.vanguard.budget < 50) {
          canAfford = false;
          reason = "Insufficient Budget (need $50)";
        }
      }
    }

    if (!canAfford) {
      return HttpResponse.json(
        {
          status: "error",
          message: reason,
        },
        { status: 400 },
      );
    }

    // Deduct cost and queue action
    if (playerOrg && playerOrg.vanguard) {
      if (verb === "attack") playerOrg.vanguard.cadre_labor -= 2;
      if (verb === "educate") playerOrg.vanguard.budget -= 50;
    }

    queuedActions.push({ verb, ...data });

    return HttpResponse.json({
      status: "ok",
      data: { id: queuedActions.length, status: "pending", verb },
    });
  }),

  // Resolve tick
  http.post("/api/games/:id/resolve/", () => {
    mockState.tick += 1;

    // Simulate Trap Escalation Contract
    if (mockState.traps) {
      const attackCount = queuedActions.filter((a) => a.verb === "attack").length;
      const educateCount = queuedActions.filter((a) => a.verb === "educate").length;

      if (attackCount > 0) {
        mockState.traps.ultra_left.score += 0.3 * attackCount;
        if (mockState.traps.ultra_left.score >= 0.5) {
          mockState.traps.ultra_left.severity = "moderate";
          mockState.traps.active_trap = "ultra_left";
        }
      }

      if (educateCount > 0) {
        mockState.traps.liberal.score += 0.3 * educateCount;
        if (mockState.traps.liberal.score >= 0.5) {
          mockState.traps.liberal.severity = "moderate";
          mockState.traps.active_trap = "liberal";
        }
      }
    }

    queuedActions = []; // Flush actions

    return HttpResponse.json({
      status: "ok",
      data: { resolved: true },
      tick: mockState.tick,
    });
  }),

  // Action results
  http.get("/api/games/:id/results/:tick/", () =>
    HttpResponse.json({
      status: "ok",
      data: [makeActionResult()],
    }),
  ),

  // Journal — full cross-tick event history (spec 092)
  http.get("/api/games/:id/journal/", () =>
    HttpResponse.json({
      status: "ok",
      data: { events: mockJournalEvents },
    }),
  ),

  // Alerts — critical/warning events from the latest tick (spec 092)
  http.get("/api/games/:id/alerts/", () =>
    HttpResponse.json({
      status: "ok",
      data: { alerts: mockJournalEvents.filter((e) => e.severity !== "informational") },
    }),
  ),
];
