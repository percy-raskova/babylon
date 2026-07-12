/**
 * lib/geo/topology.test.ts — fetch/cache/decode contract (spec-113 §7 task 2) plus a
 * smoke test against the real generated `public/geo/counties.topojson` asset.
 */

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  countyFeatures,
  loadCountyTopology,
  loadStateTopology,
  resetGeoTopologyCache,
  stateFeatures,
  type CountyProperties,
  type CountyTopology,
  type StateProperties,
  type StateTopology,
} from "./topology";
import miniCounties from "./__fixtures__/mini-counties.topojson.json";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

describe("loadCountyTopology / loadStateTopology", () => {
  beforeEach(() => {
    resetGeoTopologyCache();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    resetGeoTopologyCache();
    vi.restoreAllMocks();
  });

  it("fetches counties.topojson from /geo/counties.topojson", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(miniCounties), { status: 200 }));
    const topo = await loadCountyTopology();
    expect(fetchSpy).toHaveBeenCalledWith("/geo/counties.topojson");
    expect(topo.objects.counties.geometries).toHaveLength(4);
  });

  it("caches the parsed topology — a second call does not refetch", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(miniCounties), { status: 200 }));
    const first = await loadCountyTopology();
    const second = await loadCountyTopology();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(second).toBe(first);
  });

  it("dedupes concurrent in-flight requests to a single fetch", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(miniCounties), { status: 200 }));
    const [a, b] = await Promise.all([loadCountyTopology(), loadCountyTopology()]);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(a).toBe(b);
  });

  it("throws a descriptive error on a non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("not found", { status: 404, statusText: "Not Found" }),
    );
    await expect(loadCountyTopology()).rejects.toThrow(/404/);
  });

  it("fetches states.topojson from /geo/states.topojson independently of counties", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "Topology",
          arcs: [],
          objects: { states: { type: "GeometryCollection", geometries: [] } },
        }),
        { status: 200 },
      ),
    );
    await loadStateTopology();
    expect(fetchSpy).toHaveBeenCalledWith("/geo/states.topojson");
  });
});

describe("countyFeatures / stateFeatures", () => {
  it("extracts a GeoJSON FeatureCollection from the county topology", () => {
    const topo = miniCounties as unknown as CountyTopology;
    const fc = countyFeatures(topo);
    expect(fc.type).toBe("FeatureCollection");
    expect(fc.features).toHaveLength(4);
    expect(fc.features[0]?.properties?.GEOID).toBe("00001");
  });
});

describe("real counties.topojson asset (smoke test)", () => {
  it("parses, has 3,200+ county geometries, and every geometry has a 5-char GEOID", () => {
    const assetPath = path.resolve(__dirname, "../../../public/geo/counties.topojson");
    const raw = readFileSync(assetPath, "utf8");
    const topo = JSON.parse(raw) as CountyTopology;

    expect(topo.type).toBe("Topology");
    const geometries = topo.objects.counties.geometries;
    expect(geometries.length).toBeGreaterThanOrEqual(3200);

    for (const g of geometries) {
      // Every real county geometry is a Polygon/MultiPolygon (never topojson-specification's
      // untyped NullObject variant), so this narrows the union's properties type safely.
      const geoid = (g.properties as CountyProperties | undefined)?.GEOID;
      expect(typeof geoid).toBe("string");
      expect(geoid).toHaveLength(5);
    }
  });

  it("extracts a valid FeatureCollection via countyFeatures()", () => {
    const assetPath = path.resolve(__dirname, "../../../public/geo/counties.topojson");
    const raw = readFileSync(assetPath, "utf8");
    const topo = JSON.parse(raw) as CountyTopology;
    const fc = countyFeatures(topo);
    expect(fc.features).toHaveLength(topo.objects.counties.geometries.length);
    const nonPolygon = fc.features.filter(
      (f) => f.geometry.type !== "Polygon" && f.geometry.type !== "MultiPolygon",
    );
    expect(nonPolygon).toHaveLength(0);
  });
});

describe("real states.topojson asset (smoke test)", () => {
  it("parses and has 56 state-dissolve geometries with STATEFP", () => {
    const assetPath = path.resolve(__dirname, "../../../public/geo/states.topojson");
    const raw = readFileSync(assetPath, "utf8");
    const topo = JSON.parse(raw) as StateTopology;
    expect(topo.objects.states.geometries).toHaveLength(56);
    for (const g of topo.objects.states.geometries) {
      expect(typeof (g.properties as StateProperties | undefined)?.STATEFP).toBe("string");
    }
    const fc = stateFeatures(topo);
    expect(fc.features).toHaveLength(56);
  });
});
