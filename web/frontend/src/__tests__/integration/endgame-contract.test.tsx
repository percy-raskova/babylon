/**
 * Contract test: endgame state endpoint (spec 095).
 *
 * Pins the EndgameState response shape that `useEndgame` relies on:
 * `{status: "ok", data: EndgameState}` where EndgameState carries
 * tick/outcome/headline/summary/stats per the contract in
 * `specs/095-endgame-chronicle/contracts/endgame.yaml`.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse } from "@/types/game";
import type { EndgameState } from "@/types/dialectic";

const GAME_ID = "wayne-county-001";

describe("endgame contract (spec 095)", () => {
  it("GET /api/games/:id/endgame/ returns EndgameState", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/endgame/`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<EndgameState>;

    expect(body.status).toBe("ok");
    const state = body.data;

    expect(typeof state.tick).toBe("number");
    expect(state.outcome === null || typeof state.outcome === "string").toBe(true);
    expect(typeof state.headline).toBe("string");
    expect(typeof state.summary).toBe("string");

    const stats = state.stats;
    expect(typeof stats.final_tick).toBe("number");
    expect(typeof stats.consciousness).toBe("number");
    expect(typeof stats.solidarity_edges).toBe("number");
    expect(typeof stats.heat).toBe("number");
  });

  it("returns null outcome when game is in progress", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/endgame/`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<EndgameState>;
    // The MSW fixture returns outcome: null (game in progress).
    expect(body.data.outcome).toBeNull();
  });
});
