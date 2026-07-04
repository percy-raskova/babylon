/**
 * Contract test: per-territory economy endpoint (spec 093 US5).
 *
 * Pins the response shape `useEconomy` relies on: `{status: "ok", data:
 * EconomyPayload}` per `specs/093-territory-org-detail/contracts/
 * economy.yaml`. Written red-first — MSW has no handler for
 * `/api/games/:id/economy/?territory_id=` until `test/handlers.ts` is
 * updated.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse, EconomyPayload } from "@/types/game";

const GAME_ID = "wayne-county-001";

describe("economy contract (spec 093 US5)", () => {
  it("GET /api/games/:id/economy/?territory_id=T1 returns a real EconomyPayload", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/economy/?territory_id=T1`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<EconomyPayload>;

    expect(body.status).toBe("ok");
    expect(body.data.territory_id).toBe("T1");
    expect(typeof body.data.has_data).toBe("boolean");
    expect(typeof body.data.value_produced).toBe("number");
    expect(typeof body.data.rent_extracted).toBe("number");
    expect(typeof body.data.extraction_intensity).toBe("number");
    expect(body.data.wage_share === null || typeof body.data.wage_share === "number").toBe(true);
    expect(
      body.data.exploitation_rate === null || typeof body.data.exploitation_rate === "number",
    ).toBe(true);
  });

  it("GET /api/games/:id/economy/?territory_id=unknown returns an honest no-data payload", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/economy/?territory_id=unknown-territory`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<EconomyPayload>;

    expect(body.status).toBe("ok");
    expect(body.data.has_data).toBe(false);
    expect(body.data.value_produced).toBe(0);
    expect(body.data.exploitation_rate).toBeNull();
  });
});
