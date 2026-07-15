/**
 * Unit tests for regionFillForLens — spec-112 C5's region-fill color logic
 * for aggregated (county/cz/msa/bea_ea/state) map features.
 */

import { describe, it, expect } from "vitest";
import { regionFillForLens, type RegionFillProperties } from "./regionFill";
import { lensRampStops, sampleRampStops, type Lens } from "@/lib/lens";
import { rampForLayer } from "@/theme/colors";
import { TERRITORY_TYPE_COLOR } from "@/components/map/mapLensLayers";

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

  describe("solidarity_index metric (spec-113 Lane B)", () => {
    it("samples the dedicated solidarity ramp, distinct from habitability's", () => {
      const properties: RegionFillProperties = { solidarity_index: 0.6 };
      const lens: Lens = { kind: "metric", metric: "solidarity_index" };
      const result = regionFillForLens(lens, properties, DOMAIN);
      expect(result).toEqual(sampleRampStops(lensRampStops(lens)!, 0.6));
    });
  });

  describe("class_composition lens (spec-113 Lane B/D)", () => {
    it("colors by dominant_class via the shared SOCIAL_ROLE_COLOR palette", () => {
      const properties: RegionFillProperties = { dominant_class: "core_bourgeoisie" };
      expect(regionFillForLens({ kind: "class_composition" }, properties, DOMAIN)).toEqual([
        212, 160, 44, 220,
      ]);
    });

    it("is null-honest when dominant_class is absent", () => {
      expect(regionFillForLens({ kind: "class_composition" }, {}, DOMAIN)).toBeNull();
    });

    it("is null-honest for an unrecognized role string", () => {
      const properties: RegionFillProperties = { dominant_class: "not_a_real_role" };
      expect(regionFillForLens({ kind: "class_composition" }, properties, DOMAIN)).toBeNull();
    });
  });

  describe("territory_type lens (Wave 2 Round 2 addition)", () => {
    it("colors by territory_type via the shared TERRITORY_TYPE_COLOR palette", () => {
      const properties: RegionFillProperties = { territory_type: "core" };
      expect(regionFillForLens({ kind: "territory_type" }, properties, DOMAIN)).toEqual(
        TERRITORY_TYPE_COLOR.core,
      );
    });

    it("is null-honest when territory_type is absent (never a fabricated fill)", () => {
      expect(regionFillForLens({ kind: "territory_type" }, {}, DOMAIN)).toBeNull();
    });

    it("is null-honest for an explicit null territory_type (partial-coverage group)", () => {
      const properties: RegionFillProperties = { territory_type: null };
      expect(regionFillForLens({ kind: "territory_type" }, properties, DOMAIN)).toBeNull();
    });

    it("is null-honest for an unrecognized territory-type string, never a fake zero color", () => {
      const properties: RegionFillProperties = { territory_type: "not_a_real_type" };
      expect(regionFillForLens({ kind: "territory_type" }, properties, DOMAIN)).toBeNull();
    });
  });

  describe("throughput_position / agitation metric lenses (Wave 2 Round 2 addition)", () => {
    it("throughput_position samples its own ramp like any other metric lens", () => {
      const properties: RegionFillProperties = { throughput_position: 0.4 };
      const lens: Lens = { kind: "metric", metric: "throughput_position" };
      const result = regionFillForLens(lens, properties, DOMAIN);
      expect(result).toEqual(sampleRampStops(lensRampStops(lens)!, 0.4));
    });

    it("agitation samples its own ramp like any other metric lens", () => {
      const properties: RegionFillProperties = { agitation: 0.0 };
      const lens: Lens = { kind: "metric", metric: "agitation" };
      const result = regionFillForLens(lens, properties, DOMAIN);
      expect(result).toEqual(sampleRampStops(lensRampStops(lens)!, 0.0));
    });

    it("is null-honest (never a fabricated zero fill) when throughput_position/agitation are missing", () => {
      const throughputLens: Lens = { kind: "metric", metric: "throughput_position" };
      const agitationLens: Lens = { kind: "metric", metric: "agitation" };
      expect(regionFillForLens(throughputLens, {}, DOMAIN)).toBeNull();
      expect(regionFillForLens(agitationLens, {}, DOMAIN)).toBeNull();
    });
  });

  it("a degenerate (zero-dynamic-range) domain is null-honest, not a fabricated floor color", () => {
    // A ramp encodes RELATIVE position within the visible domain. When every
    // region shares one value (span === 0 — e.g. the static-economy case where
    // every imperial_rent is 0.0, owner item #25), there is no relative signal
    // to encode. Sampling the ramp at t=0 would paint a floor color
    // indistinguishable from a genuine spread bottomed at the floor — the very
    // thing mapLensLayers.ts::metricFill's docstring forbids ("an empty domain
    // must render as visibly distinct from a real 0.0"). Honest-null here →
    // REGION_NO_DATA_FILL, so the always-drawn political borders show through
    // instead of a black blob (Constitution III.11). No divide-by-zero either.
    expect(regionFillForLens({ kind: "heat" }, { heat: 5 }, { min: 5, max: 5 })).toBeNull();

    const rentLens: Lens = { kind: "metric", metric: "imperial_rent" };
    expect(regionFillForLens(rentLens, { imperial_rent: 0 }, { min: 0, max: 0 })).toBeNull();
  });
});
