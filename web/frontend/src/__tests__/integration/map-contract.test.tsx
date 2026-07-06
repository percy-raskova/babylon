/**
 * Contract test: map snapshot endpoint (spec 093 US3).
 *
 * Pins the response shape `DeckGLMap` relies on: `{status: "ok", data:
 * FeatureCollection}` with `metadata.balkanization` carrying the real
 * `_build_balkanization_block` shape. MSW handler in `test/handlers.ts`.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse } from "@/types/game";
import type { BalkanizationBlock } from "@/components/map/mapLensLayers";

const GAME_ID = "wayne-county-001";

interface MapData {
  type: string;
  features: unknown[];
  metadata: { balkanization: BalkanizationBlock };
}

describe("map contract (spec 093 US3)", () => {
  it("GET /api/games/:id/map/ returns balkanization with the correct shape", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/map/`, { credentials: "include" });
    const body = (await res.json()) as ApiResponse<MapData>;

    expect(body.status).toBe("ok");
    expect(body.data.type).toBe("FeatureCollection");

    const balk = body.data.metadata.balkanization;
    expect(balk).toBeDefined();
    expect(Array.isArray(balk.factions)).toBe(true);
    expect(Array.isArray(balk.sovereigns)).toBe(true);
    expect(Array.isArray(balk.territory_influence)).toBe(true);

    if (balk.factions.length > 0) {
      const f = balk.factions[0]!;
      expect(typeof f.id).toBe("string");
      expect(typeof f.colonial_stance).toBe("string");
    }

    if (balk.sovereigns.length > 0) {
      const s = balk.sovereigns[0]!;
      expect(typeof s.id).toBe("string");
      expect(typeof s.ruling_faction_id).toBe("string");
      expect(typeof s.legitimacy).toBe("number");
      expect(Array.isArray(s.claimed_territory_ids)).toBe(true);
    }

    if (balk.territory_influence.length > 0) {
      const ti = balk.territory_influence[0]!;
      expect(typeof ti.territory_id).toBe("string");
      expect(Array.isArray(ti.influences)).toBe(true);
      expect(typeof ti.contested).toBe("boolean");
      expect(typeof ti.habitability).toBe("number");
    }
  });
});
