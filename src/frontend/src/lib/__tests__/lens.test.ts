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
  MAP_HISTORY_REPLAYABLE_METRICS,
  lensMetricName,
  isReplayableLens,
  type Lens,
} from "../lens";
import { DATA_RAMPS } from "@/theme/colors";

describe("MAP_METRICS mirrors the backend's map_contract.py MAP_METRIC_PROPERTIES", () => {
  it("has exactly the 12 numeric contract metric names, in contract order", () => {
    // Wave 2 Round 2 (reports/wave2-implementation-map.md): throughput_position
    // (ruling 1 — wired for real, no longer a frozen 1.0 constant) and
    // agitation (DECLARED_CONDITIONAL — legitimately 0.0 absent a crisis tick)
    // join the numeric contract, appended after solidarity_index. Audit Wave 4
    // straggler (task #76): centrality (a territory's own degree-centrality
    // within the org-network topology) is appended after agitation.
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
      "throughput_position",
      "agitation",
      "centrality",
    ]);
  });

  it("deliberately excludes dominant_class (categorical — drives the class_composition Lens kind instead)", () => {
    expect(MAP_METRICS).not.toContain("dominant_class");
  });

  it("deliberately excludes territory_type (categorical — drives the territory_type Lens kind instead)", () => {
    expect(MAP_METRICS).not.toContain("territory_type");
  });
});

describe("SELECTABLE_METRICS excludes the metrics with a dedicated Lens kind", () => {
  it("drops heat and habitability (they have their own kind, not a metric sub-select)", () => {
    expect(SELECTABLE_METRICS).not.toContain("heat");
    expect(SELECTABLE_METRICS).not.toContain("habitability");
  });

  it("keeps every other contract metric, including solidarity_index/throughput_position/agitation/centrality", () => {
    expect([...SELECTABLE_METRICS].sort()).toEqual(
      [
        "profit_rate",
        "exploitation_rate",
        "occ",
        "imperial_rent",
        "org_presence",
        "population",
        "solidarity_index",
        "throughput_position",
        "agitation",
        "centrality",
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

  it("treats field_flow lenses as equal only when the field matches too", () => {
    expect(
      isSameLens(
        { kind: "field_flow", field: "exploitation" },
        { kind: "field_flow", field: "exploitation" },
      ),
    ).toBe(true);
    expect(
      isSameLens(
        { kind: "field_flow", field: "exploitation" },
        { kind: "field_flow", field: "atomization" },
      ),
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

  it("is false for territory_type (territory-local TerritoryType enum, not the balkanization block)", () => {
    expect(isBalkanizationLens({ kind: "territory_type" })).toBe(false);
  });

  it("is false for field_flow (per-class-pair field_state edges, not the balkanization block)", () => {
    expect(isBalkanizationLens({ kind: "field_flow", field: "exploitation" })).toBe(false);
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

  it("field_flow keys differ per field, and never collide with a mode/metric key", () => {
    const exploitation = lensKey({ kind: "field_flow", field: "exploitation" });
    const atomization = lensKey({ kind: "field_flow", field: "atomization" });
    expect(exploitation).not.toBe(atomization);
    expect(LENS_MODES.map((kind) => lensKey({ kind }))).not.toContain(exploitation);
    expect(SELECTABLE_METRICS.map((metric) => lensKey({ kind: "metric", metric }))).not.toContain(
      exploitation,
    );
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

  it("labels territory_type distinctly from every mode/metric/class_composition lens", () => {
    const label = lensLegendLabel({ kind: "territory_type" }).toLowerCase();
    expect(label).toContain("territory");
  });

  it("labels the two new metric lenses (throughput_position/agitation) with their own names", () => {
    expect(
      lensLegendLabel({ kind: "metric", metric: "throughput_position" }).toLowerCase(),
    ).toContain("throughput");
    expect(lensLegendLabel({ kind: "metric", metric: "agitation" }).toLowerCase()).toContain(
      "agitation",
    );
  });

  it("labels the centrality metric lens with its own name (audit Wave 4 straggler, task #76)", () => {
    expect(lensLegendLabel({ kind: "metric", metric: "centrality" }).toLowerCase()).toContain(
      "central",
    );
  });

  it("labels field_flow with 'Gradient Wind' plus the title-cased field name", () => {
    expect(lensLegendLabel({ kind: "field_flow", field: "exploitation" })).toBe(
      "Gradient Wind · Exploitation Field",
    );
    expect(lensLegendLabel({ kind: "field_flow", field: "atomization" })).toBe(
      "Gradient Wind · Atomization Field",
    );
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

  it("stance/faction/collapse/class_composition/territory_type have no single metric ramp (categorical fills, not a ramp)", () => {
    expect(lensRampStops({ kind: "stance" })).toBeNull();
    expect(lensRampStops({ kind: "faction" })).toBeNull();
    expect(lensRampStops({ kind: "collapse" })).toBeNull();
    expect(lensRampStops({ kind: "class_composition" })).toBeNull();
    expect(lensRampStops({ kind: "territory_type" })).toBeNull();
  });

  it("field_flow has no fill ramp — direction/magnitude render as flow geometry, never a color ramp (DESIGN_BIBLE.md §11 law 1)", () => {
    expect(lensRampStops({ kind: "field_flow", field: "exploitation" })).toBeNull();
  });

  it("solidarity_index resolves to its own dedicated ramp, distinct from habitability's", () => {
    const stops = lensRampStops({ kind: "metric", metric: "solidarity_index" });
    expect(stops).toEqual(DATA_RAMPS.solidarity);
    expect(stops).not.toEqual(DATA_RAMPS.biocapacity);
  });

  it("throughput_position resolves to the wealth ramp, distinct from every other registered metric's ramp", () => {
    const stops = lensRampStops({ kind: "metric", metric: "throughput_position" });
    expect(stops).toEqual(DATA_RAMPS.wealth);
    expect(stops).not.toEqual(DATA_RAMPS.rent);
    expect(stops).not.toEqual(DATA_RAMPS.solidarity);
  });

  it("agitation resolves to the consciousness ramp, distinct from heat/solidarity (its nearest struggle-group cousins)", () => {
    const stops = lensRampStops({ kind: "metric", metric: "agitation" });
    expect(stops).toEqual(DATA_RAMPS.consciousness);
    expect(stops).not.toEqual(DATA_RAMPS.heat);
    expect(stops).not.toEqual(DATA_RAMPS.solidarity);
  });

  it("throughput_position and agitation resolve to two DISTINCT ramps from each other", () => {
    const throughput = lensRampStops({ kind: "metric", metric: "throughput_position" });
    const agitation = lensRampStops({ kind: "metric", metric: "agitation" });
    expect(throughput).not.toEqual(agitation);
  });

  it("centrality resolves to the population ramp — the one canonical ramp no other registered lens had yet claimed (audit Wave 4 straggler, task #76)", () => {
    const stops = lensRampStops({ kind: "metric", metric: "centrality" });
    expect(stops).toEqual(DATA_RAMPS.population);
    expect(stops).not.toEqual(DATA_RAMPS.consciousness);
    expect(stops).not.toEqual(DATA_RAMPS.wealth);
  });
});

describe("MAP_HISTORY_REPLAYABLE_METRICS mirrors web/game/map_contract.py's tuple of the same name", () => {
  it("lists exactly heat/population/profit_rate/exploitation_rate", () => {
    expect([...MAP_HISTORY_REPLAYABLE_METRICS].sort()).toEqual(
      ["heat", "population", "profit_rate", "exploitation_rate"].sort(),
    );
  });

  it("every entry is a real MAP_METRICS member (no invented metric names)", () => {
    for (const metric of MAP_HISTORY_REPLAYABLE_METRICS) {
      expect(MAP_METRICS).toContain(metric);
    }
  });
});

describe("lensMetricName — the single MapMetric a lens directly names, or null", () => {
  it("resolves {kind:'heat'} to 'heat'", () => {
    expect(lensMetricName({ kind: "heat" })).toBe("heat");
  });

  it("resolves {kind:'metric', metric} to that metric", () => {
    expect(lensMetricName({ kind: "metric", metric: "population" })).toBe("population");
    expect(lensMetricName({ kind: "metric", metric: "occ" })).toBe("occ");
  });

  it("returns null for every lens kind with no single-metric shape", () => {
    expect(lensMetricName({ kind: "stance" })).toBeNull();
    expect(lensMetricName({ kind: "faction" })).toBeNull();
    expect(lensMetricName({ kind: "collapse" })).toBeNull();
    expect(lensMetricName({ kind: "habitability" })).toBeNull();
    expect(lensMetricName({ kind: "class_composition" })).toBeNull();
    expect(lensMetricName({ kind: "territory_type" })).toBeNull();
    expect(lensMetricName({ kind: "field_flow", field: "exploitation" })).toBeNull();
  });
});

describe("isReplayableLens — gates the RadarLoopPanel scrubber's availability", () => {
  it("is true for the heat mode lens", () => {
    expect(isReplayableLens({ kind: "heat" })).toBe(true);
  });

  it("is true for the 3 replayable metric sub-selects", () => {
    expect(isReplayableLens({ kind: "metric", metric: "population" })).toBe(true);
    expect(isReplayableLens({ kind: "metric", metric: "profit_rate" })).toBe(true);
    expect(isReplayableLens({ kind: "metric", metric: "exploitation_rate" })).toBe(true);
  });

  it("is false for a non-replayable metric sub-select", () => {
    expect(isReplayableLens({ kind: "metric", metric: "occ" })).toBe(false);
    expect(isReplayableLens({ kind: "metric", metric: "imperial_rent" })).toBe(false);
  });

  it("is false for every categorical/vector lens kind", () => {
    expect(isReplayableLens({ kind: "stance" })).toBe(false);
    expect(isReplayableLens({ kind: "faction" })).toBe(false);
    expect(isReplayableLens({ kind: "collapse" })).toBe(false);
    expect(isReplayableLens({ kind: "habitability" })).toBe(false);
    expect(isReplayableLens({ kind: "class_composition" })).toBe(false);
    expect(isReplayableLens({ kind: "territory_type" })).toBe(false);
    expect(isReplayableLens({ kind: "field_flow", field: "exploitation" })).toBe(false);
  });
});
