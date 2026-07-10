/**
 * Unit tests for regionFillForLens — spec-112 C5's region-fill color logic
 * for aggregated (county/cz/msa/bea_ea/state) map features.
 */

import { describe, it, expect } from "vitest";
import { regionFillForLens, type RegionFillProperties } from "./regionFill";
import { lensRampStops, sampleRampStops, type Lens } from "@/lib/lens";
import { rampForLayer } from "@/theme/colors";

const DOMAIN = { min: 0, max: 1 };

describe("regionFillForLens", () => {
  describe("heat lens", () => {
    it("samples the heat ramp at the normalized value", () => {
      const properties: RegionFillProperties = { heat: 0.5 };
      const result = regionFillForLens({ kind: "heat" }, properties, DOMAIN);
      expect(result).toEqual(sampleRampStops(lensRampStops({ kind: "heat" })!, 0.5));
    });

    it("normalizes against a non-[0,1] domain", () => {
      const properties: RegionFillProperties = { heat: 5 };
      const domain = { min: 0, max: 10 };
      const result = regionFillForLens({ kind: "heat" }, properties, domain);
      expect(result).toEqual(sampleRampStops(lensRampStops({ kind: "heat" })!, 0.5));
    });

    it("is null-honest when heat is missing", () => {
      expect(regionFillForLens({ kind: "heat" }, {}, DOMAIN)).toBeNull();
    });

    it("is null-honest for a non-finite value", () => {
      const properties: RegionFillProperties = { heat: NaN };
      expect(regionFillForLens({ kind: "heat" }, properties, DOMAIN)).toBeNull();
    });
  });

  describe("habitability lens", () => {
    it("samples the biocapacity ramp directly at the aggregate value (no domain division)", () => {
      const properties: RegionFillProperties = { habitability: 0.75 };
      const result = regionFillForLens({ kind: "habitability" }, properties, DOMAIN);
      expect(result).toEqual(sampleRampStops(lensRampStops({ kind: "habitability" })!, 0.75));
    });

    it("is null-honest when the backend never wrote a value for a partial-coverage group", () => {
      const explicitNull: RegionFillProperties = { habitability: null };
      expect(regionFillForLens({ kind: "habitability" }, explicitNull, DOMAIN)).toBeNull();

      expect(regionFillForLens({ kind: "habitability" }, {}, DOMAIN)).toBeNull();
    });
  });

  describe("metric lens", () => {
    it("samples the metric's own ramp, reusing lensRampStops/sampleRampStops (no duplicated ramp math)", () => {
      const properties: RegionFillProperties = { profit_rate: 0.3 };
      const lens: Lens = { kind: "metric", metric: "profit_rate" };
      const result = regionFillForLens(lens, properties, DOMAIN);
      expect(result).toEqual(sampleRampStops(lensRampStops(lens)!, 0.3));
    });

    it("normalizes against the provided domain like heat", () => {
      const properties: RegionFillProperties = { population: 50000 };
      const lens: Lens = { kind: "metric", metric: "population" };
      const domain = { min: 0, max: 100000 };
      const result = regionFillForLens(lens, properties, domain);
      expect(result).toEqual(sampleRampStops(lensRampStops(lens)!, 0.5));
    });

    it("is null-honest when the metric value is missing", () => {
      const lens: Lens = { kind: "metric", metric: "imperial_rent" };
      expect(regionFillForLens(lens, {}, DOMAIN)).toBeNull();
    });
  });

  describe("stance lens (FLAGGED for owner review)", () => {
    it("samples the consciousness ramp over the aggregate consciousness value", () => {
      const properties: RegionFillProperties = { consciousness: 0.6 };
      const result = regionFillForLens({ kind: "stance" }, properties, DOMAIN);
      expect(result).toEqual(sampleRampStops(rampForLayer("consciousness"), 0.6));
    });

    it("is null-honest when no consciousness aggregate is present (today's real /map/ payload shape)", () => {
      expect(regionFillForLens({ kind: "stance" }, {}, DOMAIN)).toBeNull();
    });
  });

  describe("faction and collapse lenses", () => {
    it("faction always returns null (neutral fill; hex-native influence rings remain the signal)", () => {
      const properties: RegionFillProperties = { heat: 1, habitability: 1, consciousness: 1 };
      expect(regionFillForLens({ kind: "faction" }, properties, DOMAIN)).toBeNull();
    });

    it("collapse always returns null (neutral fill; hex-native claims hulls remain the signal)", () => {
      const properties: RegionFillProperties = { heat: 1, habitability: 1, consciousness: 1 };
      expect(regionFillForLens({ kind: "collapse" }, properties, DOMAIN)).toBeNull();
    });
  });

  it("a zero-width domain does not divide by zero", () => {
    const properties: RegionFillProperties = { heat: 5 };
    const domain = { min: 5, max: 5 };
    expect(() => regionFillForLens({ kind: "heat" }, properties, domain)).not.toThrow();
  });
});
