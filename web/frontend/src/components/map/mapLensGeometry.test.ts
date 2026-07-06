/**
 * Red-first tests for hull-polygon geometry resolution (sovereign CLAIMS
 * hulls). Pure function — no deck.gl/WebGL dependency.
 */

import { describe, it, expect } from "vitest";
import { hullPolygonForTerritories, type HullGeometryTerritory } from "./mapLensGeometry";

const TERRITORIES: HullGeometryTerritory[] = [
  { id: "T1", h3_index: "872a3072cffffff" },
  { id: "T2", h3_index: "872a3072dffffff" },
  { id: "T3", h3_index: "872a3072effffff" },
  { id: "T4", h3_index: null },
];

describe("hullPolygonForTerritories", () => {
  it("returns null when fewer than 3 territories resolve real geometry", () => {
    expect(hullPolygonForTerritories(["T1"], TERRITORIES)).toBeNull();
    expect(hullPolygonForTerritories(["T1", "T4"], TERRITORIES)).toBeNull();
  });

  it("resolves a closed [lng, lat] convex hull ring for 3+ real territories", () => {
    const hull = hullPolygonForTerritories(["T1", "T2", "T3"], TERRITORIES);
    expect(hull).not.toBeNull();
    expect(hull!.length).toBeGreaterThanOrEqual(3);
    // Closed ring: first and last point identical.
    expect(hull![0]).toEqual(hull![hull!.length - 1]);
    // [lng, lat] order — longitude around -71, not latitude (~42) in position 0.
    expect(Math.abs(hull![0]![0])).toBeGreaterThan(60);
  });

  it("ignores territories with no h3_index (null geometry)", () => {
    const withNull = hullPolygonForTerritories(["T1", "T2", "T3", "T4"], TERRITORIES);
    const withoutNull = hullPolygonForTerritories(["T1", "T2", "T3"], TERRITORIES);
    expect(withNull).toEqual(withoutNull);
  });

  it("ignores unknown territory ids", () => {
    const hull = hullPolygonForTerritories(["T1", "T2", "T3", "UNKNOWN"], TERRITORIES);
    expect(hull).not.toBeNull();
  });
});
