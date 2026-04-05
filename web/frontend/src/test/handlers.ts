/**
 * MSW request handlers — stateful mock server simulating the Wayne County game loop.
 *
 * This mock server:
 * - Returns Wayne County snapshot data with vanguard resources and traps
 * - Processes action affordability checks (rejects unaffordable actions)
 * - Deducts resources on successful actions
 * - Resolves ticks and escalates trap scores based on action patterns
 * - Exports resetMockState() for test cleanup
 */

import { http, HttpResponse } from "msw";
import type { GameSnapshot } from "@/types/game";
import {
  makeWayneCountySnapshot,
  makeGameSummary,
  makeActionResult,
  makeActionPreview,
  makeAvailableAction,
} from "./fixtures";

// ---------------------------------------------------------------------------
// Stateful mock game state
// ---------------------------------------------------------------------------

let mockState: GameSnapshot = makeWayneCountySnapshot();
let actionHistory: Array<{ verb: string; org_id: string }> = [];

/** Reset mock state to initial Wayne County conditions. */
export function resetMockState(): void {
  mockState = makeWayneCountySnapshot();
  actionHistory = [];
}

// ---------------------------------------------------------------------------
// Affordability rules
// ---------------------------------------------------------------------------

interface CostRule {
  check: (state: GameSnapshot) => boolean;
  deduct: (state: GameSnapshot) => void;
  reason: string;
}

const VERB_COSTS: Record<string, CostRule> = {
  educate: {
    check: (s) => (s.organizations[0]?.vanguard?.budget ?? 0) >= 50,
    deduct: (s) => {
      if (s.organizations[0]?.vanguard) s.organizations[0].vanguard.budget -= 50;
    },
    reason: "Insufficient Budget (need $50)",
  },
  attack: {
    check: (s) => (s.organizations[0]?.vanguard?.cadre_labor ?? 0) >= 2,
    deduct: (s) => {
      if (s.organizations[0]?.vanguard) s.organizations[0].vanguard.cadre_labor -= 2;
    },
    reason: "Insufficient Cadre Labor (need 2)",
  },
  mobilize: {
    check: (s) => (s.organizations[0]?.vanguard?.sympathizer_labor ?? 0) >= 2,
    deduct: (s) => {
      if (s.organizations[0]?.vanguard) s.organizations[0].vanguard.sympathizer_labor -= 2;
    },
    reason: "Insufficient Sympathizer Labor (need 2)",
  },
};

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

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
          description: "Detroit tri-county area",
          territory_count: 1500,
        },
        {
          key: "two_node",
          name: "Two-Node Dialectic",
          description: "Minimal scenario",
          territory_count: 1,
        },
      ],
    }),
  ),

  // Game list
  http.get("/api/games/", () =>
    HttpResponse.json({
      status: "ok",
      data: [
        makeGameSummary(),
        makeGameSummary({
          id: "game-002",
          scenario: "detroit",
          current_tick: 12,
          status: "active",
        }),
      ],
    }),
  ),

  // Create game
  http.post("/api/games/", () =>
    HttpResponse.json({
      status: "ok",
      data: { session_id: "wayne-county-001" },
    }),
  ),

  // Game state — returns current stateful snapshot
  http.get("/api/games/:id/state/", () =>
    HttpResponse.json({
      status: "ok",
      data: mockState,
    }),
  ),

  // Available actions — 3 verbs for Wayne County
  http.get("/api/games/:id/actions/available/", () =>
    HttpResponse.json({
      status: "ok",
      data: [
        makeAvailableAction({ org_id: "ORG001", verb: "educate", cost: 50 }),
        makeAvailableAction({ org_id: "ORG001", verb: "attack", cost: 2 }),
        makeAvailableAction({ org_id: "ORG001", verb: "mobilize", cost: 2 }),
      ],
    }),
  ),

  // Action preview
  http.post("/api/games/:id/actions/preview/", () =>
    HttpResponse.json({
      status: "ok",
      data: makeActionPreview(),
    }),
  ),

  // Submit action — stateful affordability check
  http.post("/api/games/:id/actions/", async ({ request }) => {
    const body = (await request.json()) as { verb: string; org_id: string };
    const rule = VERB_COSTS[body.verb];

    if (rule && !rule.check(mockState)) {
      return HttpResponse.json(
        {
          status: "error",
          message: rule.reason,
        },
        { status: 400 },
      );
    }

    // Deduct resources
    if (rule) {
      rule.deduct(mockState);
    }

    // Track action for trap escalation
    actionHistory.push({ verb: body.verb, org_id: body.org_id });

    return HttpResponse.json({
      status: "ok",
      data: { id: actionHistory.length, status: "pending" },
    });
  }),

  // Resolve tick — advance tick & escalate traps
  http.post("/api/games/:id/resolve/", () => {
    mockState = { ...mockState, tick: mockState.tick + 1 };

    // Escalate traps based on action patterns
    if (mockState.traps) {
      const educateCount = actionHistory.filter((a) => a.verb === "educate").length;
      const attackCount = actionHistory.filter((a) => a.verb === "attack").length;

      const newTraps = { ...mockState.traps };

      // Liberal score increases with educate-heavy patterns
      if (educateCount > 0) {
        const newScore = (newTraps.liberal.score as number) + educateCount * 0.3;
        newTraps.liberal = {
          ...newTraps.liberal,
          score: Math.min(1.0, newScore),
          severity: newScore > 0.5 ? "moderate" : "mild",
        };
      }

      // Ultra-left score increases with attack-heavy patterns
      if (attackCount > 0) {
        const newScore = (newTraps.ultra_left.score as number) + attackCount * 0.3;
        newTraps.ultra_left = {
          ...newTraps.ultra_left,
          score: Math.min(1.0, newScore),
          severity: newScore > 0.5 ? "moderate" : "mild",
        };
      }

      // Determine active trap (highest non-none severity)
      const highest = [newTraps.liberal, newTraps.ultra_left, newTraps.rightist]
        .filter((t) => t.severity !== "none")
        .sort((a, b) => (b.score as number) - (a.score as number))[0];

      newTraps.active_trap = highest ? (highest.trap_type as string) : null;
      mockState = { ...mockState, traps: newTraps };
    }

    // Clear action history for next tick
    actionHistory = [];

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
