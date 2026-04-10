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
import { GameSnapshot } from "../types/game";

// In-memory state machine for the mock game loop
let mockState: GameSnapshot = makeWayneCountySnapshot();
let queuedActions: { verb: string; targets?: string[] }[] = [];

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
];
