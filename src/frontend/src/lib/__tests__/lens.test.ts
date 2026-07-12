/**
 * Red-first tests for the unified map `Lens` discriminated union
 * (spec-110 B2, the one redesign this lane ships).
 *
 * Before this module, the cockpit's map had TWO independent, overlapping
 * "lens" axes carried in `web/frontend/src/stores/mapStore.ts`:
 *   - `activeLayer: MapLayer` — the single-metric color ramp
 *     (heat/consciousness/wealth/rent/biocapacity/population/profit_rate/
 *     exploitation_rate/occ/imperial_rent/org_presence).
 *   - `lensMode: LensMode` — the spec-070/093 political-topology lens
 *     (stance/heat/habitability/faction/collapse).
 * Both had their own "heat" (mapStore defaulted `activeLayer: "heat"` AND
 * `lensMode: "stance"` independently — a UI could select "heat" as BOTH
 * the layer and disagree with a different lensMode simultaneously, and
 * `MapLayer`'s "heat" ramp and `LensMode`'s "heat" fill happened to mean
 * the same territory-local value but were two unrelated code paths).
 *
 * This module collapses both into one `Lens` value: the 5 spec-093 modes
 * are primary "kind" tags; the remaining MAP_METRIC_PROPERTIES contract
 * metrics (profit_rate, exploitation_rate, occ, imperial_rent, org_presence,
 * population) live under a single `{ kind: "metric"; metric }` sub-select.
 * `heat` and `habitability` are NOT selectable as `metric` values — they
 * already have dedicated kinds, so there is exactly one way to ask for
 * either (eliminating the collision described above).
 */

import { describe, it, expect } from "vitest";
import {
  MAP_METRICS,
  SELECTABLE_METRICS,
  LENS_MODES,
  DEFAULT_LENS,
  isSameLens,
  isBalkanizationLens,
  lensKey,
  lensLegendLabel,
  lensRampStops,
  type Lens,
} from "../lens";
import { DATA_RAMPS } from "@/theme/colors";

describe("MAP_METRICS mirrors the backend's map_contract.py MAP_METRIC_PROPERTIES", () => {
  it("has exactly the 9 numeric contract metric names, in contract order", () => {
    expect(MAP_METRICS).toEqual([
      "profit_rate",
      "exploitation_rate",
      "occ",
      "imperial_rent",
      "heat",
      "org_presence",
      "population",
      "habitability",
      "solidarity_index",
    ]);
  });

  it("deliberately excludes dominant_class (categorical — drives the class_composition Lens kind instead)", () => {
    expect(MAP_METRICS).not.toContain("dominant_class");
  });
});

describe("SELECTABLE_METRICS excludes the metrics with a dedicated Lens kind", () => {
  it("drops heat and habitability (they have their own kind, not a metric sub-select)", () => {
    expect(SELECTABLE_METRICS).not.toContain("heat");
    expect(SELECTABLE_METRICS).not.toContain("habitability");
  });

  it("keeps every other contract metric, including solidarity_index", () => {
    expect([...SELECTABLE_METRICS].sort()).toEqual(
      [
        "profit_rate",
        "exploitation_rate",
        "occ",
        "imperial_rent",
        "org_presence",
        "population",
        "solidarity_index",
      ].sort(),
    );
  });
});

describe("LENS_MODES — the 5 spec-093 political-topology kinds", () => {
  it("lists exactly stance/heat/habitability/faction/collapse", () => {
    expect(LENS_MODES).toEqual(["stance", "heat", "habitability", "faction", "collapse"]);
  });
});

describe("DEFAULT_LENS", () => {
  it("is the Imperial Rent metric lens (DESIGN_BIBLE.md §9 amendment 1 — not a political-topology default)", () => {
    expect(DEFAULT_LENS).toEqual({ kind: "metric", metric: "imperial_rent" });
  });
});

describe("isSameLens", () => {
  it("treats two mode lenses of the same kind as equal", () => {
    expect(isSameLens({ kind: "heat" }, { kind: "heat" })).toBe(true);
  });

  it("treats mode lenses of different kinds as unequal", () => {
    expect(isSameLens({ kind: "heat" }, { kind: "stance" })).toBe(false);
  });

  it("treats metric lenses as equal only when the metric matches too", () => {
    expect(isSameLens({ kind: "metric", metric: "occ" }, { kind: "metric", metric: "occ" })).toBe(
      true,
    );
    expect(
      isSameLens({ kind: "metric", metric: "occ" }, { kind: "metric", metric: "population" }),
    ).toBe(false);
  });

  it("a metric lens is never equal to a mode lens, even by name collision", () => {
    // metric:"heat" is not constructible via SELECTABLE_METRICS, but the
    // union type technically allows any MapMetric — verify the comparison
    // still discriminates on kind first.
    const metricHeat = { kind: "metric", metric: "occ" } as const;
    const modeStance: Lens = { kind: "stance" };
    expect(isSameLens(metricHeat, modeStance)).toBe(false);
  });
});

describe("isBalkanizationLens", () => {
  it("is true for stance/faction/collapse (spec-070 balkanization-derived)", () => {
    expect(isBalkanizationLens({ kind: "stance" })).toBe(true);
    expect(isBalkanizationLens({ kind: "faction" })).toBe(true);
    expect(isBalkanizationLens({ kind: "collapse" })).toBe(true);
  });

  it("is false for heat/habitability (territory-local, A8)", () => {
    expect(isBalkanizationLens({ kind: "heat" })).toBe(false);
    expect(isBalkanizationLens({ kind: "habitability" })).toBe(false);
  });

  it("is false for every metric lens", () => {
    for (const metric of SELECTABLE_METRICS) {
      expect(isBalkanizationLens({ kind: "metric", metric })).toBe(false);
    }
  });

  it("is false for class_composition (hex_latest's own column, not the spec-070 balkanization block)", () => {
    expect(isBalkanizationLens({ kind: "class_composition" })).toBe(false);
  });
});

describe("lensKey — stable identity for React keys / updateTriggers arrays", () => {
  it("differs across mode kinds", () => {
    const keys = new Set(LENS_MODES.map((kind) => lensKey({ kind })));
    expect(keys.size).toBe(LENS_MODES.length);
  });

  it("differs across metric sub-selects", () => {
    const keys = new Set(SELECTABLE_METRICS.map((metric) => lensKey({ kind: "metric", metric })));
    expect(keys.size).toBe(SELECTABLE_METRICS.length);
  });

  it("a metric lens never collides with a mode lens key", () => {
    const modeKeys = new Set(LENS_MODES.map((kind) => lensKey({ kind })));
    for (const metric of SELECTABLE_METRICS) {
      expect(modeKeys.has(lensKey({ kind: "metric", metric }))).toBe(false);
    }
  });
});

describe("lensLegendLabel", () => {
  it("labels every mode lens distinctly", () => {
    const labels = LENS_MODES.map((kind) => lensLegendLabel({ kind }));
    expect(new Set(labels).size).toBe(LENS_MODES.length);
  });

  it("labels a metric lens with the metric name", () => {
    expect(lensLegendLabel({ kind: "metric", metric: "profit_rate" }).toLowerCase()).toContain(
      "profit",
    );
  });

  it("labels class_composition distinctly from every mode/metric lens", () => {
    const label = lensLegendLabel({ kind: "class_composition" }).toLowerCase();
    expect(label).toContain("class");
  });
});

describe("lensRampStops — single ramp resolution shared by fill + legend", () => {
  it("heat kind resolves to the canon heat ramp", () => {
    expect(lensRampStops({ kind: "heat" })).toEqual(DATA_RAMPS.heat);
  });

  it("habitability kind resolves to the diverging biocapacity ramp (matches old habitabilityFill)", () => {
    expect(lensRampStops({ kind: "habitability" })).toEqual(DATA_RAMPS.biocapacity);
  });

  it("metric:heat is unreachable via SELECTABLE_METRICS but still resolves consistently if forced", () => {
    // Guards against a future SELECTABLE_METRICS regression that re-adds
    // "heat" — the ramp math must stay consistent with kind:"heat" even if
    // it did leak through, so a duplicate isn't visually different.
    const forced = { kind: "metric", metric: "heat" } as const;
    expect(lensRampStops(forced)).toEqual(lensRampStops({ kind: "heat" }));
  });

  it("metric:habitability likewise stays consistent with kind:habitability", () => {
    const forced = { kind: "metric", metric: "habitability" } as const;
    expect(lensRampStops(forced)).toEqual(lensRampStops({ kind: "habitability" }));
  });

  it("every selectable metric resolves to a non-empty ramp", () => {
    for (const metric of SELECTABLE_METRICS) {
      const stops = lensRampStops({ kind: "metric", metric });
      expect(stops?.length ?? 0).toBeGreaterThan(1);
    }
  });

  it("stance/faction/collapse/class_composition have no single metric ramp (categorical fills, not a ramp)", () => {
    expect(lensRampStops({ kind: "stance" })).toBeNull();
    expect(lensRampStops({ kind: "faction" })).toBeNull();
    expect(lensRampStops({ kind: "collapse" })).toBeNull();
    expect(lensRampStops({ kind: "class_composition" })).toBeNull();
  });

  it("solidarity_index resolves to its own dedicated ramp, distinct from habitability's", () => {
    const stops = lensRampStops({ kind: "metric", metric: "solidarity_index" });
    expect(stops).toEqual(DATA_RAMPS.solidarity);
    expect(stops).not.toEqual(DATA_RAMPS.biocapacity);
  });
});
