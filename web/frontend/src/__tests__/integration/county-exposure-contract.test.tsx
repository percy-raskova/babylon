/**
 * Contract test: county import-exposure endpoint (spec 103 US5).
 *
 * Pins the response shape `useCountyExposure` relies on: `{status: "ok",
 * data: ExposurePayload}` per `specs/103-trade-surfaces/contracts/
 * county-exposure.yaml`. The drill-down provenance chain must end at
 * reference-data citations. Written red-first — MSW has no handler for
 * `/api/games/:id/exposure/?county_fips=` until `test/handlers.ts` is updated.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse, ExposurePayload } from "@/types/trade";

const GAME_ID = "wayne-county-001";

describe("county-exposure contract (spec 103 US5)", () => {
  it("GET /api/games/:id/exposure/?county_fips= returns a real ExposurePayload with provenance chain", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/exposure/?county_fips=26161`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<ExposurePayload>;

    expect(body.status).toBe("ok");
    expect(body.data.county_fips).toBe("26161");
    expect(typeof body.data.has_data).toBe("boolean");
    expect(typeof body.data.total_exposure).toBe("number");
    expect(typeof body.data.breakdown).toBe("object");
    expect(Array.isArray(body.data.breakdown.contributors)).toBe(true);
    expect(Array.isArray(body.data.citations)).toBe(true);

    if (body.data.breakdown.contributors.length > 0) {
      const c = body.data.breakdown.contributors[0]!;
      expect(typeof c.label).toBe("string");
      expect(typeof c.value).toBe("number");
      expect(typeof c.share).toBe("number");
      expect(typeof c.source).toBe("object");
      expect(typeof c.source.kind).toBe("string");
      expect(typeof c.source.path).toBe("string");
      expect(Array.isArray(c.children)).toBe(true);

      // Drill-down children must trace to reference_table or dynamic_table
      if (c.children.length > 0) {
        const childKinds = c.children.map((ch) => ch.source.kind);
        const hasProvenance = childKinds.some((k) =>
          ["reference_table", "dynamic_table", "derived"].includes(k),
        );
        expect(hasProvenance).toBe(true);
      }
    }

    // Citations must carry reference-data provenance
    if (body.data.citations.length > 0) {
      const cite = body.data.citations[0]!;
      expect(typeof cite.id).toBe("string");
      expect(typeof cite.source).toBe("string");
      expect(typeof cite.table).toBe("string");
    }
  });

  it("GET /api/games/:id/exposure/?county_fips=unknown returns an honest no-data payload", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/exposure/?county_fips=99999`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<ExposurePayload>;

    expect(body.status).toBe("ok");
    expect(body.data.has_data).toBe(false);
    expect(body.data.total_exposure).toBe(0);
    expect(body.data.breakdown.contributors).toEqual([]);
  });
});
