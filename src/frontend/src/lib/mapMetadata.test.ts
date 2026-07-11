/**
 * Unit tests for `lib/mapMetadata.ts` — the `panels.map` data-reading
 * helpers spec-113 Lane B extended with `availableMetricsFromMapData` and
 * `hexFeaturePropertiesByH3`.
 */

import { describe, it, expect } from "vitest";
import {
  factionsFromMapData,
  availableMetricsFromMapData,
  hexFeaturePropertiesByH3,
  type MapFeatureCollectionWithMetadata,
} from "./mapMetadata";

describe("factionsFromMapData", () => {
  it("returns [] when data is null", () => {
    expect(factionsFromMapData(null)).toEqual([]);
  });

  it("reads factions off metadata.balkanization", () => {
    const data: MapFeatureCollectionWithMetadata = {
      type: "FeatureCollection",
      features: [],
      metadata: {
        balkanization: {
          factions: [{ id: "F1", colonial_stance: "uphold" }],
          sovereigns: [],
          territory_influence: [],
        },
      },
    };
    expect(factionsFromMapData(data)).toEqual([{ id: "F1", colonial_stance: "uphold" }]);
  });
});

describe("availableMetricsFromMapData", () => {
  it("returns undefined when data is null", () => {
    expect(availableMetricsFromMapData(null)).toBeUndefined();
  });

  it("returns undefined when metadata carries no available_metrics", () => {
    const data: MapFeatureCollectionWithMetadata = { type: "FeatureCollection", features: [] };
    expect(availableMetricsFromMapData(data)).toBeUndefined();
  });

  it("reads metadata.available_metrics verbatim", () => {
    const data: MapFeatureCollectionWithMetadata = {
      type: "FeatureCollection",
      features: [],
      metadata: { available_metrics: ["heat", "imperial_rent", "dominant_class"] },
    };
    expect(availableMetricsFromMapData(data)).toEqual(["heat", "imperial_rent", "dominant_class"]);
  });
});

describe("hexFeaturePropertiesByH3", () => {
  it("returns an empty map for null data", () => {
    expect(hexFeaturePropertiesByH3(null).size).toBe(0);
  });

  it("indexes hex features by properties.h3_index", () => {
    const data: MapFeatureCollectionWithMetadata = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          id: "882a100d2bfffff",
          geometry: { type: "Polygon", coordinates: [] },
          properties: {
            h3_index: "882a100d2bfffff",
            profit_rate: 0.3,
            dominant_class: "core_bourgeoisie",
            solidarity_index: 0.6,
          },
        },
      ],
    };
    const index = hexFeaturePropertiesByH3(data);
    expect(index.size).toBe(1);
    expect(index.get("882a100d2bfffff")?.profit_rate).toBe(0.3);
    expect(index.get("882a100d2bfffff")?.dominant_class).toBe("core_bourgeoisie");
    expect(index.get("882a100d2bfffff")?.solidarity_index).toBe(0.6);
  });

  it("skips features with no h3_index property (defensive — region features shouldn't reach this path)", () => {
    const data: MapFeatureCollectionWithMetadata = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          id: "26163",
          geometry: null,
          properties: { group_key: "26163", member_h3: ["a", "b"] },
        } as unknown as GeoJSON.Feature,
      ],
    };
    expect(hexFeaturePropertiesByH3(data).size).toBe(0);
  });
});
