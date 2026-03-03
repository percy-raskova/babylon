/**
 * Unit tests for color scale functions.
 */

import { describe, it, expect } from "vitest";
import { getColorScale, rgbaToCss } from "./colors";
import type { MapLayer } from "@/types/game";

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
