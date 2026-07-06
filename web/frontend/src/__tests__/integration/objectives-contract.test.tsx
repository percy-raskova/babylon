/**
 * Contract test: journal objectives endpoint (spec 095).
 *
 * Pins the ObjectivesTracker response shape that `useObjectives` relies on:
 * `{status: "ok", data: ObjectivesTracker}` where ObjectivesTracker carries
 * tick/objectives per the contract in
 * `specs/095-endgame-chronicle/contracts/objectives.yaml`.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse } from "@/types/game";
import type { ObjectivesTracker, Objective } from "@/types/dialectic";

const GAME_ID = "wayne-county-001";

describe("objectives contract (spec 095)", () => {
  it("GET /api/games/:id/objectives/ returns ObjectivesTracker", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/objectives/`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<ObjectivesTracker>;

    expect(body.status).toBe("ok");
    const tracker = body.data;

    expect(typeof tracker.tick).toBe("number");
    expect(Array.isArray(tracker.objectives)).toBe(true);
    expect(tracker.objectives.length).toBeGreaterThanOrEqual(1);
  });

  it("each objective has required fields with valid values", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/objectives/`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<ObjectivesTracker>;

    for (const obj of body.data.objectives as Objective[]) {
      expect(typeof obj.id).toBe("string");
      expect(typeof obj.title).toBe("string");
      expect(typeof obj.description).toBe("string");
      expect(typeof obj.progress).toBe("number");
      expect(obj.progress).toBeGreaterThanOrEqual(0);
      expect(obj.progress).toBeLessThanOrEqual(1);
      expect(["active", "complete", "failed"]).toContain(obj.status);
      expect(["revolution", "collapse", "fascist", "red_ogv", "fragmented"]).toContain(
        obj.category,
      );
    }
  });
});
