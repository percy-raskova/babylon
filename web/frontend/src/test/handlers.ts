/**
 * MSW request handlers — mock all Django API endpoints.
 */

import { http, HttpResponse } from "msw";
import { makeSnapshot, makeAvailableAction, makeGameSummary, makeActionResult } from "./fixtures";

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
      data: { session_id: "new-game-001" },
    }),
  ),

  // Game state
  http.get("/api/games/:id/state/", () =>
    HttpResponse.json({
      status: "ok",
      data: makeSnapshot(),
    }),
  ),

  // Available actions
  http.get("/api/games/:id/actions/available/", () =>
    HttpResponse.json({
      status: "ok",
      data: [
        makeAvailableAction(),
        makeAvailableAction({ verb: "attack", targets: ["entity-bourgeoisie"], cost: 5 }),
      ],
    }),
  ),

  // Submit action
  http.post("/api/games/:id/actions/", () =>
    HttpResponse.json({
      status: "ok",
      data: { id: 1, status: "pending" },
    }),
  ),

  // Resolve tick
  http.post("/api/games/:id/resolve/", () =>
    HttpResponse.json({
      status: "ok",
      data: { resolved: true },
      tick: 2,
    }),
  ),

  // Action results
  http.get("/api/games/:id/results/:tick/", () =>
    HttpResponse.json({
      status: "ok",
      data: [makeActionResult()],
    }),
  ),
];
