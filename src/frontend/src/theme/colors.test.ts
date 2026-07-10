/**
 * Unit tests for color scale functions.
 */

import { describe, it, expect } from "vitest";
import { getColorScale, rgbaToCss, DATA_RAMPS, rampForLayer } from "./colors";
import type { MapLayer } from "@/types/game";

/** Parse ``#rrggbb`` → RGB triple (test helper). */
function hex(s: string): [number, number, number] {
  const n = parseInt(s.replace(/^#/, ""), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

describe("color scales", () => {
  const ALL_LAYERS: MapLayer[] = [
    "heat",
    "consciousness",
    "wealth",
    "rent",
    "biocapacity",
    "population",
  ];

  it("getColorScale returns a function for each layer", () => {
    for (const layer of ALL_LAYERS) {
      const scale = getColorScale(layer);
      expect(typeof scale).toBe("function");
    }
  });

  it("scales return RGBA tuples with 4 elements", () => {
    for (const layer of ALL_LAYERS) {
      const scale = getColorScale(layer);
      const color = scale(0.5);
      expect(color).toHaveLength(4);
      expect(color.every((c) => typeof c === "number")).toBe(true);
    }
  });

  it("scales handle boundary value 0", () => {
    for (const layer of ALL_LAYERS) {
      const scale = getColorScale(layer);
      const color = scale(0);
      expect(color).toHaveLength(4);
      // All RGBA values should be valid (0-255)
      for (const c of color) {
        expect(c).toBeGreaterThanOrEqual(0);
        expect(c).toBeLessThanOrEqual(255);
      }
    }
  });

  it("scales handle boundary value 1", () => {
    for (const layer of ALL_LAYERS) {
      const scale = getColorScale(layer);
      const color = scale(1);
      expect(color).toHaveLength(4);
      for (const c of color) {
        expect(c).toBeGreaterThanOrEqual(0);
        expect(c).toBeLessThanOrEqual(255);
      }
    }
  });

  it("scales produce different colors for 0 and 1", () => {
    for (const layer of ALL_LAYERS) {
      const scale = getColorScale(layer);
      const low = scale(0);
      const high = scale(1);
      // At least one channel should differ
      const differs = low.some((c, i) => c !== high[i]);
      expect(differs).toBe(true);
    }
  });
});

describe("Cold Collapse data ramps (spec-090)", () => {
  it("scales interpolate the canon ramp endpoints", () => {
    const seq: MapLayer[] = ["heat", "consciousness", "rent", "wealth", "population"];
    for (const layer of seq) {
      const stops = DATA_RAMPS[layer as keyof typeof DATA_RAMPS];
      const scale = getColorScale(layer);
      const low = scale(0);
      const high = scale(1);
      const first = stops[0] ?? "#000000";
      const last = stops[stops.length - 1] ?? "#000000";
      expect([low[0], low[1], low[2]]).toEqual(hex(first));
      expect([high[0], high[1], high[2]]).toEqual(hex(last));
    }
  });

  it("consciousness runs dark → spire cyan", () => {
    const scale = getColorScale("consciousness");
    expect([...scale(1).slice(0, 3)]).toEqual(hex("#4dd9e6"));
  });

  it("biocapacity is diverging: collapse-red → neutral → regenerate-green", () => {
    const scale = getColorScale("biocapacity");
    expect([...scale(0).slice(0, 3)]).toEqual(hex("#b8321f")); // collapse
    expect([...scale(1).slice(0, 3)]).toEqual(hex("#5fbf7a")); // regenerate
  });

  it("no ramp carries the retired gold rainbow interior (#c8a860)", () => {
    for (const stops of Object.values(DATA_RAMPS)) {
      expect(stops.map((s) => s.toLowerCase())).not.toContain("#c8a860");
    }
  });

  it("rampForLayer maps derived aliases onto their base ramp", () => {
    expect(rampForLayer("imperial_rent")).toEqual(DATA_RAMPS.rent);
    expect(rampForLayer("profit_rate")).toEqual(DATA_RAMPS.wealth);
    expect(rampForLayer("org_presence")).toEqual(DATA_RAMPS.consciousness);
  });
});

describe("rgbaToCss", () => {
  it("converts RGBA to CSS string", () => {
    const css = rgbaToCss([200, 40, 40, 220]);
    expect(css).toBe("rgba(200, 40, 40, 0.86)");
  });

  it("handles zero alpha", () => {
    const css = rgbaToCss([0, 0, 0, 0]);
    expect(css).toBe("rgba(0, 0, 0, 0.00)");
  });

  it("handles full alpha", () => {
    const css = rgbaToCss([255, 255, 255, 255]);
    expect(css).toBe("rgba(255, 255, 255, 1.00)");
  });
});
