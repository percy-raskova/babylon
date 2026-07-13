/**
 * Golden field-value snapshot at the typed read boundary (seam Sensor 3).
 *
 * `client.get()` is the seam through which the game reads runtime state. It is
 * meant to be transparent — every field the backend emits should arrive at the
 * caller byte-identical, never dropped, renamed, or coerced. This test pins the
 * *actual field values* the boundary returns for a canonical backend response,
 * so any relabel/remap/type-coercion inside the read boundary changes a byte
 * and trips the golden (rather than silently substituting a relabeled value for
 * a real one on screen).
 *
 * It is a value snapshot (what each field IS), not a type check.
 */

import { describe, it, expect } from "vitest";
import { get } from "./client";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import type { GameSummaryPayload } from "@/types/game";

/**
 * The exact JSON envelope the Django `EngineBridge.get_game_summary` contract
 * emits (mirrors `makeGameSummaryPayload`). Frozen as the canonical input.
 */
const CANONICAL_SUMMARY_RESPONSE = {
  status: "ok",
  data: {
    tick: 7,
    imperial_rent: 12.5,
    avg_consciousness: 0.4,
    population_total: 42000,
    exploitation_rate: 0.3,
    profit_rate: 0.18,
    org_count: 1,
    class_count: 4,
    event_counts: { critical: 0, warning: 0, informational: 0 },
  },
} as const;

describe("api/client golden field values (seam Sensor 3)", () => {
  it("returns the canonical summary field-for-field, unrelabeled", async () => {
    server.use(
      http.get("/api/games/:id/summary/", () =>
        HttpResponse.json(structuredClone(CANONICAL_SUMMARY_RESPONSE)),
      ),
    );

    const res = await get<GameSummaryPayload>("/api/games/game-001/summary/");

    // Golden: the pinned values the read boundary must hand back verbatim.
    expect(res).toEqual({
      status: "ok",
      data: {
        tick: 7,
        imperial_rent: 12.5,
        avg_consciousness: 0.4,
        population_total: 42000,
        exploitation_rate: 0.3,
        profit_rate: 0.18,
        org_count: 1,
        class_count: 4,
        event_counts: { critical: 0, warning: 0, informational: 0 },
      },
    });
  });
});
